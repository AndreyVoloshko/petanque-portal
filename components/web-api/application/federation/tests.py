from datetime import date, timedelta
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.middleware.locale import LocaleMiddleware
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from django.utils.translation import get_language, gettext as _, override

from federation.forms.registration_player_form import RegistrationPlayerForm
from federation.middleware import InitialLanguageMiddleware
from federation.models.email_confirmation import EmailConfirmation
from federation.models.club import Club
from federation.models.player import Player
from federation.models.team import PlayerTeamMembership, Team
from federation.models.tournament import TeamTournamentMembership, Tournament
from federation.permissions import can_create_tournament
from federation.storage import StaticStorage
from federation.templatetags.app_filters import (
    licence_number,
    team_power_badge,
    tournament_audience_tag_class,
    tournament_field,
    tournament_power_badge,
    tournament_power_class,
    tournament_registration,
)
from federation.utils.tournament_names import (
    get_tournament_card_metadata,
    get_tournament_display_name,
    get_tournament_format_name,
    get_localized_tournament_format_name,
    tournament_display_name_matches,
)
from federation.views.login import _needs_email_prompt


class TournamentDisplayNameTests(SimpleTestCase):
    def create_tournament(self, name, year=2026, players_min=1, players_max=1, tournament_format='swiko'):
        return Tournament(
            name=name,
            category='open',
            place='Київ',
            start_date=date(year, 5, 1),
            number_of_players_in_team_min=players_min,
            number_of_players_in_team_max=players_max,
            format=tournament_format,
        )

    def test_adds_year_and_single_player_format(self):
        tournament = self.create_tournament('Тупіт копит')

        self.assertEqual(
            tournament.get_display_name(),
            'Тупіт копит. 2026. Тет-а-тет',
        )
        self.assertEqual(tournament.name, 'Тупіт копит')

    def test_uses_team_size_format_names(self):
        doublets = self.create_tournament('Тупіт копит', players_min=2, players_max=2)
        triplets = self.create_tournament('Тупіт копит', players_min=3, players_max=4)
        clubs = self.create_tournament('Чемпіонат України', players_min=6, players_max=10)

        self.assertEqual(get_tournament_display_name(doublets), 'Тупіт копит. 2026. Дуплети')
        self.assertEqual(get_tournament_display_name(triplets), 'Тупіт копит. 2026. Триплети')
        self.assertEqual(get_tournament_display_name(clubs), 'Чемпіонат України. 2026. Клуби')

    def test_uses_shooting_format_before_team_size(self):
        tournament = self.create_tournament('Чемпіонат України (жінки, ІІІ ранг)', tournament_format='tir')

        self.assertEqual(
            get_tournament_display_name(tournament),
            'Чемпіонат України (жінки, ІІІ ранг). 2026. Тир',
        )

    def test_does_not_duplicate_existing_year_or_format(self):
        tournament = self.create_tournament(
            'Чемпіонат України 2026. Триплети',
            players_min=3,
            players_max=4,
        )

        self.assertEqual(
            get_tournament_display_name(tournament),
            'Чемпіонат України 2026. Триплети',
        )

    def test_detects_format_inside_parentheses_case_insensitively(self):
        tournament = self.create_tournament(
            'Всеукраїнські змагання "Каштани" (триплети)',
            players_min=3,
            players_max=4,
        )

        self.assertEqual(
            get_tournament_display_name(tournament),
            'Всеукраїнські змагання "Каштани" (триплети). 2026',
        )

    def test_detects_tete_a_tete_shorthand(self):
        tournament = self.create_tournament(
            'Чемпіонат України (молодь, юніори, юнаки) тети',
            players_min=1,
            players_max=1,
        )

        self.assertEqual(
            get_tournament_display_name(tournament),
            'Чемпіонат України (молодь, юніори, юнаки) тети. 2026',
        )

    def test_trims_trailing_dot_before_appending_parts(self):
        tournament = self.create_tournament('Тупіт копит. ', players_min=2, players_max=2)

        self.assertEqual(
            get_tournament_display_name(tournament),
            'Тупіт копит. 2026. Дуплети',
        )

    def test_handles_missing_year_or_format(self):
        without_year = SimpleNamespace(
            name='Тупіт копит',
            start_date=None,
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            format='swiko',
        )
        without_format = SimpleNamespace(
            name='Тупіт копит',
            start_date=date(2026, 5, 1),
            number_of_players_in_team_min=4,
            number_of_players_in_team_max=4,
            format='swiko',
        )

        self.assertEqual(get_tournament_display_name(without_year), 'Тупіт копит. Дуплети')
        self.assertEqual(get_tournament_display_name(without_format), 'Тупіт копит. 2026')

    def test_display_name_search_matches_computed_year_and_format(self):
        tournament = self.create_tournament('Тупіт копит', players_min=1, players_max=1)

        self.assertTrue(tournament_display_name_matches(tournament, '2026 тет'))
        self.assertTrue(tournament_display_name_matches(tournament, 'Тупіт копит'))
        self.assertFalse(tournament_display_name_matches(tournament, '2025 дуплети'))

    def test_card_metadata_separates_format_and_audience_from_parentheses(self):
        tournament = self.create_tournament(
            'Чемпіонат України (тир, жінки)',
            tournament_format='tir',
        )

        self.assertEqual(get_tournament_card_metadata(tournament), {
            'name': 'Чемпіонат України',
            'format': 'Тир',
            'format_source': 'Тир',
            'format_tags': ['Тир'],
            'audience_tags': ['Жінки'],
        })

    def test_card_metadata_separates_multiple_formats_and_audience_from_parentheses(self):
        tournament = self.create_tournament(
            'Чемпіонат світу (триплети, тир, чоловіки)',
            players_min=3,
            players_max=4,
            tournament_format='tir',
        )

        self.assertEqual(get_tournament_card_metadata(tournament), {
            'name': 'Чемпіонат світу',
            'format': 'Триплети',
            'format_source': 'Триплети',
            'format_tags': ['Триплети', 'Тир'],
            'audience_tags': ['Чоловіки'],
        })

    def test_card_metadata_separates_format_only_parentheses(self):
        tournament = self.create_tournament(
            'Всеукраїнські змагання "Паланок" (дуплети)',
            players_min=2,
            players_max=2,
        )

        self.assertEqual(get_tournament_card_metadata(tournament), {
            'name': 'Всеукраїнські змагання "Паланок"',
            'format': 'Дуплети',
            'format_source': 'Дуплети',
            'format_tags': ['Дуплети'],
            'audience_tags': [],
        })

    def test_card_metadata_handles_multiple_audience_tags_and_trailing_format(self):
        tournament = self.create_tournament(
            'Чемпіонат України (молодь, юніори, юнаки) тети',
            players_min=1,
            players_max=1,
        )

        self.assertEqual(get_tournament_card_metadata(tournament), {
            'name': 'Чемпіонат України',
            'format': 'Тет-а-тет',
            'format_source': 'Тет-а-тет',
            'format_tags': ['Тет-а-тет'],
            'audience_tags': ['Молодь', 'Юніори', 'Юнаки'],
        })

    def test_card_metadata_normalizes_super_melee_variants(self):
        tournament = self.create_tournament(
            'July Rose Cup (супермеле)',
            tournament_format='mele',
        )

        self.assertEqual(get_tournament_card_metadata(tournament)['name'], 'July Rose Cup')
        self.assertEqual(get_tournament_card_metadata(tournament)['format'], 'Супер-меле')

    def test_card_metadata_strips_legacy_year_format_and_gender_segments(self):
        tournament = self.create_tournament(
            'Чемпіонат України 2019. Тир. Жінки',
            year=2019,
            tournament_format='tir',
        )

        self.assertEqual(get_tournament_card_metadata(tournament), {
            'name': 'Чемпіонат України',
            'format': 'Тир',
            'format_source': 'Тир',
            'format_tags': ['Тир'],
            'audience_tags': ['Жінки'],
        })

    def test_card_metadata_keeps_unknown_parenthetical_details(self):
        tournament = self.create_tournament(
            'Кубок області (етап 1)',
            players_min=2,
            players_max=2,
        )

        self.assertEqual(get_tournament_card_metadata(tournament), {
            'name': 'Кубок області (етап 1)',
            'format': 'Дуплети',
            'format_source': 'Дуплети',
            'format_tags': ['Дуплети'],
            'audience_tags': [],
        })

    def test_format_names_are_localized(self):
        tournament = self.create_tournament('Тупіт копит', players_min=2, players_max=2)

        self.assertEqual(get_tournament_format_name(tournament), 'Дуплети')
        with override('en'):
            self.assertEqual(
                get_localized_tournament_format_name(get_tournament_format_name(tournament)),
                'Doubles',
            )

    def test_tournament_power_class_uses_local_db_distribution_buckets(self):
        self.assertEqual(tournament_power_class(0), 'tournament-power-none')
        self.assertEqual(tournament_power_class('1.4883'), 'tournament-power-1')
        self.assertEqual(tournament_power_class('1.4884'), 'tournament-power-2')
        self.assertEqual(tournament_power_class('29.0942'), 'tournament-power-8')
        self.assertEqual(tournament_power_class('29.0943'), 'tournament-power-9')
        self.assertEqual(tournament_power_class('39.9999'), 'tournament-power-9')
        self.assertEqual(tournament_power_class('40.0000'), 'tournament-power-10')

    def test_tournament_audience_tags_have_semantic_color_classes(self):
        self.assertEqual(tournament_audience_tag_class('Чоловіки'), 'tournament-card-tag-men')
        self.assertEqual(tournament_audience_tag_class('Жінки'), 'tournament-card-tag-women')
        self.assertEqual(tournament_audience_tag_class('Молодь'), 'tournament-card-tag-youth')
        self.assertEqual(tournament_audience_tag_class('Юніори'), 'tournament-card-tag-youth')
        self.assertEqual(tournament_audience_tag_class('Юнаки'), 'tournament-card-tag-youth')
        self.assertEqual(tournament_audience_tag_class('Ветерани'), '')

    def test_tournament_power_badge_uses_consistent_label_icon_and_class(self):
        tournament = self.create_tournament('Тупіт копит')
        tournament.power = '40.0000'

        with override('en'):
            badge = str(tournament_power_badge(tournament))

        self.assertIn('tournament-power-badge tournament-power-10', badge)
        self.assertIn('Tournament power affects how many rating points results are worth.', badge)
        self.assertIn('Tournament power', badge)
        self.assertNotIn('tournament-power-label', badge)
        self.assertIn('bi bi-star', badge)
        self.assertTrue('40.00' in badge or '40,00' in badge)

    def test_team_power_badge_uses_team_label_and_purple_class(self):
        with override('en'):
            badge = str(team_power_badge('3.2100'))

        self.assertIn('team-power-badge', badge)
        self.assertIn('Team power', badge)
        self.assertIn('Team power in this tournament is calculated', badge)
        self.assertNotIn('tournament-power-label', badge)
        self.assertIn('bi bi-star', badge)

    def test_tournament_field_uses_power_badge_for_power(self):
        tournament = self.create_tournament('Тупіт копит')
        tournament.power = '1.4884'

        field = tournament_field(tournament, 'power')

        self.assertIn(_('Competition power'), field)
        self.assertIn('tournament-power-badge tournament-power-2', field)
        self.assertIn('bi bi-star', field)

    def test_tournament_registration_uses_large_plus_icon(self):
        tournament = self.create_tournament('Тупіт копит')
        tournament.pk = 123
        tournament.date_registration_stop = timezone.now() + timedelta(days=1)

        registration = str(tournament_registration(tournament))

        self.assertIn('bi bi-plus-lg', registration)
        self.assertIn(_('Register'), registration)


class TeamCaptainSelectionTests(TestCase):
    def create_player(self, username):
        user = User.objects.create_user(username=username)

        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def assert_team_capitan(self, team, player):
        self.assertEqual(team.get_capitan(), player)
        self.assertEqual(PlayerTeamMembership.objects.filter(team=team, is_capitan=True).count(), 1)

    def test_same_pair_can_register_again_with_different_capitan(self):
        first_player = self.create_player('first')
        second_player = self.create_player('second')

        first_team = Team.get_or_create_for_players([first_player.pk, second_player.pk])
        second_team = Team.get_or_create_for_players([second_player.pk, first_player.pk])

        self.assertNotEqual(first_team.pk, second_team.pk)
        self.assert_team_capitan(first_team, first_player)
        self.assert_team_capitan(second_team, second_player)

    def test_same_triple_can_register_again_with_different_capitan(self):
        first_player = self.create_player('first')
        second_player = self.create_player('second')
        third_player = self.create_player('third')

        first_team = Team.get_or_create_for_players([first_player.pk, second_player.pk, third_player.pk])
        second_team = Team.get_or_create_for_players([third_player.pk, second_player.pk, first_player.pk])
        same_second_team = Team.get_or_create_for_players([third_player.pk, first_player.pk, second_player.pk])

        self.assertNotEqual(first_team.pk, second_team.pk)
        self.assertEqual(second_team.pk, same_second_team.pk)
        self.assert_team_capitan(first_team, first_player)
        self.assert_team_capitan(second_team, third_player)

    def test_legacy_team_without_capitan_gets_current_registration_capitan(self):
        first_player = self.create_player('first')
        second_player = self.create_player('second')
        legacy_team = Team.objects.create()
        PlayerTeamMembership.objects.create(team=legacy_team, player=first_player)
        PlayerTeamMembership.objects.create(team=legacy_team, player=second_player)

        team = Team.get_or_create_for_players([second_player.pk, first_player.pk])

        self.assertEqual(team.pk, legacy_team.pk)
        self.assert_team_capitan(team, second_player)


class PlayerLicenseListTests(TestCase):
    def create_player(self, username, is_licence_active=True, licence_number_value=None):
        user = User.objects.create_user(username=username)

        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
            is_licence_active=is_licence_active,
            licence_number=licence_number_value,
        )

    def test_actual_players_list_requires_active_license_number(self):
        licensed = self.create_player('licensed', licence_number_value='00001')
        self.create_player('missing-number', licence_number_value=None)
        self.create_player('blank-number', licence_number_value='')
        self.create_player('inactive', is_licence_active=False, licence_number_value='00002')

        self.assertEqual(list(Player.get_actual_players_list()), [licensed])

    def test_licence_number_badge_treats_missing_number_as_no_license(self):
        player = self.create_player('missing-number', licence_number_value=None)

        with override('en'):
            badge = str(licence_number(player))

        self.assertIn('No license', badge)
        self.assertIn('bg-danger', badge)

    def test_licensed_players_page_uses_server_pagination(self):
        for index in range(55):
            self.create_player('licensed-{}'.format(index), licence_number_value='{:05d}'.format(index))
        self.create_player('missing-number', licence_number_value=None)

        response = self.client.get('/players/licence')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_size'], 50)
        self.assertEqual(response.context['page_obj'].paginator.count, 55)
        self.assertEqual(len(response.context['players']), 50)
        self.assertNotContains(response, 'players-license-badge-missing')


class PlayerTournamentListTests(TestCase):
    def test_player_tournament_table_shows_place_range_and_tournament_power(self):
        user = User.objects.create_user(username='range-player')
        player = Player.objects.create(
            user=user,
            name='Range',
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )
        team = Team.objects.create(name='Range Team')
        PlayerTeamMembership.objects.create(team=team, player=player, is_capitan=True)
        tournament = Tournament.objects.create(
            name='Playoff Cup',
            category='open',
            is_goes_to_rating=True,
            place='Київ',
            start_date=timezone.localdate() - timedelta(days=7),
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            format='swiko',
            power='12.3456',
            is_processing_finished=True,
        )
        TeamTournamentMembership.objects.create(
            tournament=tournament,
            team=team,
            place_min=5,
            place_max=8,
            power='3.2100',
            rating_points='14.5000',
        )

        response = self.client.get(f'/player/{player.pk}')
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('pt-col-strength', content)
        self.assertNotIn('pt-col-tournament-power', content)
        self.assertNotIn('pt-col-power', content)
        self.assertIn('tournament-power-badge', content)
        self.assertIn('tournament-power-4', content)
        self.assertIn('team-power-badge', content)
        self.assertNotIn('tournament-power-label', content)
        self.assertIn('data-sort-place="5"', content)
        self.assertIn('data-sort-place-max="8"', content)
        self.assertIn('>5-8</span>', content)
        self.assertIn('<span class="pt-tournament-location">Київ</span>', content)
        self.assertIn('<span class="ptm-location">Київ</span>', content)
        self.assertNotIn('>c. Київ<', content)
        self.assertNotIn('>с. Київ<', content)

        table_body = content.split('<tbody>', 1)[1]
        self.assertLess(
            table_body.index('class="pt-col-strength"'),
            table_body.index('class="pt-col-points"'),
        )


class OptionalRegistrationEmailTests(TestCase):
    def test_ukrainian_player_registration_allows_blank_email(self):
        form = RegistrationPlayerForm(data={
            'name': 'Blank',
            'surname': 'Email',
            'birth_date': '1990-01-01',
            'country': 'UA',
            'email': '',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'gender': 'M',
        })

        form.is_valid()

        self.assertNotIn('email', form.errors)

    def test_ukrainian_player_without_email_does_not_need_confirmation_prompt(self):
        user = User.objects.create_user(username='no-email-player')
        Player.objects.create(
            user=user,
            name='No',
            surname='Email',
            birth_date=date(1990, 1, 1),
            country='UA',
            gender='M',
        )

        self.assertFalse(_needs_email_prompt(user))

    def test_pending_email_confirmation_still_needs_prompt(self):
        user = User.objects.create_user(username='pending-email-player', email='pending@example.com')
        Player.objects.create(
            user=user,
            name='Pending',
            surname='Email',
            birth_date=date(1990, 1, 1),
            country='UA',
            gender='M',
        )
        EmailConfirmation.objects.create(user=user, email=user.email)

        self.assertTrue(_needs_email_prompt(user))


class InitialLanguageMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_response(self, request):
        middleware = InitialLanguageMiddleware(LocaleMiddleware(lambda req: HttpResponse(get_language())))
        return middleware(request)

    def test_sets_ukrainian_for_ukraine_country_header(self):
        request = self.factory.get('/', HTTP_CF_IPCOUNTRY='UA')

        response = self.get_response(request)

        self.assertEqual(response.content.decode(), 'uk')
        self.assertEqual(response.cookies['django_language'].value, 'uk')

    def test_sets_english_for_non_ukraine_country_header(self):
        request = self.factory.get('/', HTTP_CF_IPCOUNTRY='PL')

        response = self.get_response(request)

        self.assertEqual(response.content.decode(), 'en')
        self.assertEqual(response.cookies['django_language'].value, 'en')

    def test_existing_language_cookie_takes_priority(self):
        request = self.factory.get('/', HTTP_CF_IPCOUNTRY='PL')
        request.COOKIES['django_language'] = 'uk'

        response = self.get_response(request)

        self.assertEqual(response.content.decode(), 'uk')
        self.assertNotIn('django_language', response.cookies)

    def test_missing_country_header_uses_default_language(self):
        request = self.factory.get('/', HTTP_ACCEPT_LANGUAGE='en')

        response = self.get_response(request)

        self.assertEqual(response.content.decode(), 'uk')
        self.assertEqual(response.cookies['django_language'].value, 'uk')


class StaticStorageTests(TestCase):
    def test_manifest_storage_does_not_crash_on_missing_entries(self):
        self.assertFalse(StaticStorage.manifest_strict)


@override_settings(CURRENT_COUNTRY='UA')
class TournamentListingPageTests(TestCase):
    def create_tournament(
        self,
        name,
        start_offset=20,
        end_offset=None,
        is_rating=False,
        country='UA',
        category='open',
        registration_days=None,
        players_min=2,
        tournament_format='swiko',
        club=None,
        power='0',
        processed=False,
        meta=None,
        place='Київ',
    ):
        start_date = timezone.localdate() + timedelta(days=start_offset)
        end_date = None
        if end_offset is not None:
            end_date = timezone.localdate() + timedelta(days=end_offset)

        date_registration_stop = None
        if registration_days is not None:
            date_registration_stop = timezone.now() + timedelta(days=registration_days)

        return Tournament.objects.create(
            name=name,
            category=category,
            is_goes_to_rating=is_rating,
            place=place,
            country=country,
            start_date=start_date,
            end_date=end_date,
            date_registration_stop=date_registration_stop,
            number_of_players_in_team_min=players_min,
            number_of_players_in_team_max=players_min,
            format=tournament_format,
            organizer_club=club,
            power=power,
            is_processing_finished=processed,
            meta=meta,
        )

    def create_player(self, username='history-player'):
        user = User.objects.create_user(username=username)
        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def register_player_for_tournament(self, tournament, player, place_min=0):
        team = Team.objects.create()
        PlayerTeamMembership.objects.create(team=team, player=player, is_capitan=True)
        return TeamTournamentMembership.objects.create(
            tournament=tournament,
            team=team,
            place_min=place_min,
        )

    def test_rating_route_preset_shows_future_rating_rows_and_strength(self):
        self.create_tournament('Rating Cup', is_rating=True, power='22.2800')
        self.create_tournament('Community Cup', is_rating=False, power='18.5000')

        response = self.client.get('/tournaments/future/rating')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rating Cup')
        self.assertNotContains(response, 'Community Cup')
        self.assertContains(response, 'tournament-strength-column')
        self.assertContains(response, 'tournament-power-badge')
        self.assertEqual(response.context['filters']['period'], 'future')
        self.assertEqual(response.context['filters']['rating_type'], 'rating')

    def test_non_rating_route_preset_shows_strength_column(self):
        self.create_tournament('Rating Cup', is_rating=True, power='22.2800')
        self.create_tournament('Community Cup', is_rating=False, power='18.5000')

        response = self.client.get('/tournaments/future/non_rating')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Community Cup')
        self.assertNotContains(response, 'Rating Cup')
        self.assertContains(response, 'tournament-strength-column')
        self.assertContains(response, 'tournament-power-badge')
        self.assertEqual(response.context['filters']['rating_type'], 'non_rating')

    def test_secondary_filters_and_registration_action_render(self):
        club = Club.objects.create(name='Kyiv Petanque Club', short_name='KPC', address='Kyiv')
        tournament = self.create_tournament(
            'Kyiv Open (жінки)',
            is_rating=False,
            registration_days=5,
            club=club,
            players_min=3,
        )
        tournament.total_number_of_teams = 12
        tournament.save(update_fields=['total_number_of_teams'])
        self.create_tournament('Another Cup', is_rating=False)

        response = self.client.get('/tournaments/', {
            'period': 'future',
            'q': 'Kyiv',
            'category': 'women',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kyiv Open')
        self.assertNotContains(response, 'Another Cup')
        self.assertContains(response, 'Жінки')
        self.assertContains(response, 'KPC')
        self.assertContains(response, 'flag-icon-ua')
        self.assertContains(response, '12 команд')
        self.assertContains(response, 'Взяти участь')

    def test_away_route_preset_enables_foreign_filter(self):
        self.create_tournament('Domestic Cup', country='UA', category='open')
        self.create_tournament('French Open', country='FR', category='away')

        response = self.client.get('/tournaments/future/away')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'French Open')
        self.assertNotContains(response, 'Domestic Cup')
        self.assertTrue(response.context['filters']['foreign'])

    def test_away_country_display_uses_place_country_and_avoids_duplicates(self):
        self.create_tournament('Spain Cup', country='UA', category='away', place='Іспанія')
        self.create_tournament('Slovakia Cup', country='SK', category='away', place='Словаччнина')
        self.create_tournament('Slovakia Address Cup', country='SK', category='away', place='Slovakia, Galanta')
        self.create_tournament('Poland Address Cup', country='PL', category='away', place='Poland, Zywiec, Kopernika 2')
        self.create_tournament('Czech Address Cup', country='CZ', category='away', place='Czech Republic, Liblice')

        response = self.client.get('/tournaments/future/away')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Іспанія')
        self.assertContains(response, 'flag-icon-es')
        self.assertNotContains(response, 'Іспанія, Україна')
        self.assertNotContains(response, 'flag-icon-ua')
        self.assertContains(response, 'Словаччина')
        self.assertContains(response, 'flag-icon-sk')
        self.assertNotContains(response, 'Словаччнина, Словаччина')
        self.assertNotContains(response, 'Словаччина, Словаччина')
        self.assertContains(response, 'Slovakia, Galanta')
        self.assertNotContains(response, 'Slovakia, Galanta, Словаччина')
        self.assertContains(response, 'Poland, Zywiec, Kopernika 2')
        self.assertNotContains(response, 'Poland, Zywiec, Kopernika 2, Польща')
        self.assertContains(response, 'Czech Republic, Liblice')
        self.assertNotContains(response, 'Czech Republic, Liblice, Чехія')

    def test_date_sort_can_be_reversed(self):
        self.create_tournament('Soon Cup', start_offset=5)
        self.create_tournament('Later Cup', start_offset=40)

        response = self.client.get('/tournaments/', {
            'period': 'future',
            'sort': 'date_desc',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['rows'][0]['title'], 'Later Cup')
        self.assertEqual(response.context['sort_state']['date_direction'], 'desc')
        self.assertNotIn('sort=date_desc', response.context['sort_state']['date_url'])

    def test_ongoing_period_uses_dates_only(self):
        self.create_tournament('Today Cup', start_offset=0)
        self.create_tournament('Multi Day Cup', start_offset=-1, end_offset=1)
        self.create_tournament('Past Single Day Cup', start_offset=-1)
        self.create_tournament('Future Cup', start_offset=1)

        response = self.client.get('/tournaments/', {'period': 'ongoing'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Today Cup')
        self.assertContains(response, 'Multi Day Cup')
        self.assertNotContains(response, 'Past Single Day Cup')
        self.assertNotContains(response, 'Future Cup')

    def test_past_period_tab_uses_desc_sort_by_default(self):
        self.create_tournament('Old Past Cup', start_offset=-40)
        self.create_tournament('Recent Past Cup', start_offset=-5)

        response = self.client.get('/tournaments/', {'period': 'future'})

        self.assertEqual(response.status_code, 200)
        past_tab = next(tab for tab in response.context['period_tabs'] if tab['key'] == 'past')
        self.assertNotIn('sort=date_asc', past_tab['url'])
        self.assertNotIn('sort=date_desc', past_tab['url'])

        past_response = self.client.get(past_tab['url'])
        self.assertEqual(past_response.status_code, 200)
        self.assertEqual(past_response.context['sort_state']['date_direction'], 'desc')
        self.assertEqual(past_response.context['rows'][0]['title'], 'Recent Past Cup')

    def test_past_listing_hides_unprocessed_tournament_after_auto_cancel_cutoff(self):
        stale = self.create_tournament('Stale Unprocessed Cup', start_offset=-31, end_offset=-30)
        recent = self.create_tournament('Recent Unprocessed Cup', start_offset=-30, end_offset=-29)
        processed = self.create_tournament(
            'Processed Old Cup',
            start_offset=-31,
            end_offset=-30,
            processed=True,
        )

        response = self.client.get('/tournaments/', {'period': 'past'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(stale.is_auto_cancelled())
        self.assertFalse(recent.is_auto_cancelled())
        self.assertFalse(processed.is_auto_cancelled())
        self.assertNotContains(response, 'Stale Unprocessed Cup')
        self.assertContains(response, 'Recent Unprocessed Cup')
        self.assertContains(response, 'Processed Old Cup')
        past_tab = next(tab for tab in response.context['period_tabs'] if tab['key'] == 'past')
        self.assertEqual(past_tab['count'], 2)

    def test_player_history_hides_auto_cancelled_unprocessed_tournaments(self):
        player = self.create_player()
        stale = self.create_tournament('Stale Player Cup', start_offset=-31, end_offset=-30)
        recent = self.create_tournament('Recent Player Cup', start_offset=-30, end_offset=-29)
        processed = self.create_tournament(
            'Processed Player Cup',
            start_offset=-31,
            end_offset=-30,
            processed=True,
        )
        self.register_player_for_tournament(stale, player)
        self.register_player_for_tournament(recent, player, place_min=4)
        self.register_player_for_tournament(processed, player, place_min=2)

        response = self.client.get('/player/{}'.format(player.pk))

        self.assertEqual(response.status_code, 200)
        tournament_ids = {tournament.pk for tournament in response.context['player_tournaments']}
        self.assertNotIn(stale.pk, tournament_ids)
        self.assertIn(recent.pk, tournament_ids)
        self.assertIn(processed.pk, tournament_ids)
        self.assertNotContains(response, 'Stale Player Cup')
        self.assertContains(response, 'Recent Player Cup')
        self.assertContains(response, 'Processed Player Cup')

    def test_period_counts_respect_secondary_filters(self):
        self.create_tournament('Shooting Cup', tournament_format='tir')
        self.create_tournament('Doublets Cup', players_min=2)

        response = self.client.get('/tournaments/', {
            'period': 'future',
            'format': 'shooting',
        })

        self.assertEqual(response.status_code, 200)
        future_tab = response.context['period_tabs'][0]
        self.assertEqual(future_tab['key'], 'future')
        self.assertEqual(future_tab['count'], 1)
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_filter_form_auto_submits_without_apply_button(self):
        self.create_tournament('Future Cup')
        self.client.cookies['django_language'] = 'en'

        response = self.client.get('/tournaments/', {'period': 'future'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'tournament-filter-submit')
        self.assertNotContains(response, 'Apply')

    def test_tournament_name_has_full_name_tooltip(self):
        self.create_tournament('Full Cup (триплети, тур, чоловіки)', players_min=3)

        response = self.client.get('/tournaments/', {'period': 'future'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Full Cup')
        self.assertContains(response, 'title="Full Cup (триплети, тур, чоловіки)"')
        self.assertContains(response, 'data-bs-toggle="tooltip"')

    def test_tete_a_tete_listing_uses_player_count_label(self):
        tete = self.create_tournament('Tete Cup', players_min=1)
        tete.total_number_of_teams = 8
        tete.save(update_fields=['total_number_of_teams'])
        doublets = self.create_tournament('Doublets Cup', players_min=2)
        doublets.total_number_of_teams = 4
        doublets.save(update_fields=['total_number_of_teams'])

        response = self.client.get('/tournaments/', {'period': 'future'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '8 гравців')
        self.assertContains(response, '4 команди')
        self.assertNotContains(response, '8 команд')

    def test_tete_a_tete_listing_uses_localized_player_count_label(self):
        tete = self.create_tournament('Tete Cup', players_min=1)
        tete.total_number_of_teams = 1
        tete.save(update_fields=['total_number_of_teams'])
        self.client.cookies['django_language'] = 'en'

        response = self.client.get('/tournaments/', {'period': 'future'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 player')
        self.assertNotContains(response, '1 team')

    def test_per_page_param_limits_tournament_listing_to_five_rows(self):
        for index in range(6):
            self.create_tournament('Future Cup {}'.format(index), start_offset=index + 1)

        response = self.client.get('/tournaments/', {
            'period': 'future',
            'per_page': '5',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_size'], 5)
        self.assertEqual(response.context['page_obj'].paginator.per_page, 5)
        self.assertEqual(len(response.context['rows']), 5)
        self.assertContains(response, 'class="tournaments-mobile-list"')
        self.assertContains(response, 'per_page=5')
        self.assertContains(response, 'tournaments-page-size-value">5</span>')

    def test_english_listing_localizes_labels_and_keeps_key_based_filters(self):
        self.create_tournament('Junior Triples Cup (юніори)', players_min=3)
        self.create_tournament('Senior Doublets Cup', players_min=2)
        self.client.cookies['django_language'] = 'en'

        response = self.client.get('/tournaments/', {
            'period': 'future',
            'category': 'juniors',
            'format': 'triplets',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tournaments')
        self.assertContains(response, 'Future')
        self.assertContains(response, 'Juniors')
        self.assertContains(response, 'Triples')
        self.assertContains(response, 'No club')
        self.assertContains(response, '0 teams')
        self.assertContains(response, 'Junior Triples Cup')
        self.assertNotContains(response, 'Senior Doublets Cup')
        self.assertNotContains(response, 'Змагання не знайдено')
        self.assertEqual(response.context['page_obj'].paginator.count, 1)

    def test_create_button_is_visible_only_for_allowlisted_superuser(self):
        self.create_tournament('Future Cup')
        allowed = User.objects.create_superuser(
            id=1,
            username='andreyvoloshko',
            email='andreyvoloshko@gmail.com',
            password='secret',
        )

        self.client.login(username='andreyvoloshko', password='secret')
        response = self.client.get('/tournaments/')
        self.assertContains(response, 'Додати турнір')

        self.client.logout()
        User.objects.create_superuser(
            id=999,
            username='not-allowlisted',
            email='other@example.com',
            password='secret',
        )

        self.client.login(username='not-allowlisted', password='secret')
        response = self.client.get('/tournaments/')
        self.assertNotContains(response, 'Додати турнір')

    def test_permission_helper_requires_active_allowlisted_superuser(self):
        self.assertTrue(can_create_tournament(User(
            id=1,
            username='andreyvoloshko',
            is_active=True,
            is_superuser=True,
        )))
        self.assertFalse(can_create_tournament(User(
            id=1,
            username='andreyvoloshko',
            is_active=True,
            is_superuser=False,
        )))
        self.assertFalse(can_create_tournament(User(
            id=65,
            username='wrong-user',
            is_active=True,
            is_superuser=True,
        )))
        self.assertFalse(can_create_tournament(User(
            id=1839,
            username='admin',
            is_active=False,
            is_superuser=True,
        )))
