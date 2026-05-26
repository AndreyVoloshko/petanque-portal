from datetime import date
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.middleware.locale import LocaleMiddleware
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils.translation import get_language, gettext as _, override

from federation.forms.registration_player_form import RegistrationPlayerForm
from federation.middleware import InitialLanguageMiddleware
from federation.models.email_confirmation import EmailConfirmation
from federation.models.player import Player
from federation.models.team import PlayerTeamMembership, Team
from federation.models.tournament import Tournament
from federation.storage import StaticStorage
from federation.templatetags.app_filters import (
    tournament_audience_tag_class,
    tournament_field,
    tournament_power_badge,
    tournament_power_class,
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
            'audience_tags': ['Жінки'],
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

        badge = str(tournament_power_badge(tournament))

        self.assertIn('tournament-power-badge tournament-power-10', badge)
        self.assertIn(_('Competition power'), badge)
        self.assertIn('bi bi-star', badge)
        self.assertTrue('40.00' in badge or '40,00' in badge)

    def test_tournament_field_uses_power_badge_for_power(self):
        tournament = self.create_tournament('Тупіт копит')
        tournament.power = '1.4884'

        field = tournament_field(tournament, 'power')

        self.assertIn(_('Competition power'), field)
        self.assertIn('tournament-power-badge tournament-power-2', field)
        self.assertIn('bi bi-star', field)


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
