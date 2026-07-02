import datetime
import json
import re
from contextlib import nullcontext
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

from django.contrib.auth.models import User
from django.contrib.admin.sites import AdminSite
from django.db.models import Prefetch
from django.http import HttpResponse
from django.middleware.locale import LocaleMiddleware
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from django.utils.translation import get_language, gettext as _, override

from federation.forms.player_form import PlayerForm
from federation.forms.registration_team_form import RegistrationTeamForm
from federation.forms.registration_player_form import RegistrationPlayerForm
from federation.admin_actions.tournament import recalculate_power
from federation.middleware import InitialLanguageMiddleware
from federation.models.email_confirmation import EmailConfirmation
from federation.models.club import Club
from federation.models.national_teams import National_team, PlayerNational_teamMembership
from federation.models.player import Player
from federation.models.season import Season
from federation.models.team import PlayerTeamMembership, Team
from federation.models.tournament import (
    ArbiterTeamTournamentAdminInline,
    TeamTournamentMembership,
    Tournament,
)
from federation.permissions import can_create_tournament
from federation.services.season_snapshots import generate_season_rating_snapshot
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
from federation.views.tournaments import _tournament_status_key


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

    def test_team_without_explicit_capitan_has_display_fallback_to_first_registered_player(self):
        first_player = self.create_player('first')
        second_player = self.create_player('second')
        team = Team.objects.create()
        PlayerTeamMembership.objects.create(team=team, player=first_player)
        PlayerTeamMembership.objects.create(team=team, player=second_player)

        self.assertIsNone(team.get_capitan())
        self.assertEqual(team.get_display_capitan(), first_player)
        self.assertEqual(PlayerTeamMembership.objects.filter(team=team, is_capitan=True).count(), 0)

    def test_prefetched_team_without_explicit_capitan_has_display_fallback_to_first_registered_player(self):
        first_player = self.create_player('first')
        second_player = self.create_player('second')
        team = Team.objects.create()
        PlayerTeamMembership.objects.create(team=team, player=first_player)
        PlayerTeamMembership.objects.create(team=team, player=second_player)

        prefetched_team = Team.objects.prefetch_related(
            Prefetch(
                'playerteammembership_set',
                queryset=PlayerTeamMembership.objects.filter(is_capitan=True).select_related('player'),
                to_attr='captain_memberships',
            )
        ).get(pk=team.pk)

        self.assertIsNone(prefetched_team.get_capitan())
        self.assertEqual(prefetched_team.get_display_capitan(), first_player)
        self.assertEqual(PlayerTeamMembership.objects.filter(team=team, is_capitan=True).count(), 0)


class SeasonSnapshotGenerationTests(TestCase):
    def create_player(self, username, gender='M', with_club=True):
        club = None
        if with_club:
            club = Club.objects.create(
                name=f'{username.title()} Club',
                short_name=username.upper(),
                address='Kyiv',
            )
        user = User.objects.create_user(username=username)

        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender=gender,
            current_club=club,
            is_licence_active=True,
            licence_number=username,
        )

    def create_tournament_membership(
        self,
        player,
        year,
        points,
        is_goes_to_rating=True,
        is_b_tournament=False,
        is_ukrainian_league=False,
    ):
        team = Team.objects.create()
        PlayerTeamMembership.objects.create(team=team, player=player)
        tournament = Tournament.objects.create(
            name=f'Season Cup {year}',
            category='open',
            place='Kyiv',
            start_date=date(year, 5, 1),
            format='swiko',
            is_processing_finished=True,
            is_goes_to_rating=is_goes_to_rating,
            is_b_tournament=is_b_tournament,
            is_ukrainian_league=is_ukrainian_league,
        )

        return TeamTournamentMembership.objects.create(
            tournament=tournament,
            team=team,
            rating_points=points,
        )

    def test_generates_snapshot_rows_from_processed_tournament_memberships(self):
        player = self.create_player('snapshot-player')
        inactive_player = self.create_player('inactive-snapshot-player')
        zero_points_player = self.create_player('zero-points-snapshot-player')
        self.create_tournament_membership(
            player,
            2024,
            Decimal('12.5000'),
            is_b_tournament=True,
            is_ukrainian_league=True,
        )
        self.create_tournament_membership(player, 2025, Decimal('99.0000'))
        self.create_tournament_membership(zero_points_player, 2024, Decimal('0.0000'))

        result = generate_season_rating_snapshot(2024)

        season = Season.objects.get(year=2024, player=player)
        self.assertEqual(result.created, 1)
        self.assertEqual(result.updated, 0)
        self.assertEqual(season.club, player.current_club)
        self.assertEqual(season.rating, Decimal('12.5000'))
        self.assertEqual(season.rating_b, Decimal('12.5000'))
        self.assertEqual(season.rating_liga, Decimal('12.5000'))
        player.refresh_from_db()
        self.assertEqual(player.current_rating, Decimal('0.0000'))
        self.assertFalse(Season.objects.filter(year=2024, player=inactive_player).exists())
        self.assertFalse(Season.objects.filter(year=2024, player=zero_points_player).exists())

    def test_snapshot_skips_players_without_current_club(self):
        player = self.create_player('foreign-player', with_club=False)
        self.create_tournament_membership(player, 2024, Decimal('12.5000'))

        result = generate_season_rating_snapshot(2024)

        self.assertEqual(result.created, 0)
        self.assertEqual(result.players_considered, 0)
        self.assertFalse(Season.objects.filter(year=2024, player=player).exists())

    def test_rerun_skips_existing_rows_unless_replace_is_requested(self):
        player = self.create_player('rerun-player')
        self.create_tournament_membership(player, 2024, Decimal('20.0000'))
        Season.objects.create(
            year=2024,
            player=player,
            club=player.current_club,
            rating=Decimal('1.0000'),
        )

        skipped_result = generate_season_rating_snapshot(2024)
        season = Season.objects.get(year=2024, player=player)
        self.assertEqual(skipped_result.created, 0)
        self.assertEqual(skipped_result.updated, 0)
        self.assertEqual(skipped_result.skipped, 1)
        self.assertEqual(season.rating, Decimal('1.0000'))

        replaced_result = generate_season_rating_snapshot(2024, replace=True)
        season.refresh_from_db()
        self.assertEqual(replaced_result.created, 0)
        self.assertEqual(replaced_result.updated, 1)
        self.assertEqual(season.rating, Decimal('20.0000'))

    def test_replace_removes_stale_rows_without_season_results(self):
        player_with_results = self.create_player('replace-result-player')
        stale_player = self.create_player('stale-player')
        self.create_tournament_membership(player_with_results, 2024, Decimal('15.0000'))
        Season.objects.create(
            year=2024,
            player=stale_player,
            club=stale_player.current_club,
            rating=Decimal('0.0000'),
        )

        result = generate_season_rating_snapshot(2024, replace=True)

        self.assertEqual(result.deleted, 1)
        self.assertTrue(Season.objects.filter(year=2024, player=player_with_results).exists())
        self.assertFalse(Season.objects.filter(year=2024, player=stale_player).exists())

    def test_replace_removes_rows_when_year_has_no_qualifying_results(self):
        stale_player = self.create_player('empty-year-stale-player')
        Season.objects.create(
            year=2024,
            player=stale_player,
            club=stale_player.current_club,
            rating=Decimal('10.0000'),
        )

        result = generate_season_rating_snapshot(2024, replace=True)

        self.assertEqual(result.deleted, 1)
        self.assertFalse(Season.objects.filter(year=2024).exists())

    def test_season_page_uses_unique_display_ranks(self):
        first_player = self.create_player('first-tied-player')
        second_player = self.create_player('second-tied-player')
        Season.objects.create(year=2024, player=first_player, club=first_player.current_club, rating=Decimal('10.0000'))
        Season.objects.create(year=2024, player=second_player, club=second_player.current_club, rating=Decimal('10.0000'))

        response = self.client.get('/seasons/2024')

        self.assertEqual(response.status_code, 200)
        ranks = re.findall(r'<span class="players-rank-value">(\d+)</span>', response.content.decode())
        self.assertEqual(ranks[:2], ['1', '2'])

    def test_season_page_preserves_full_ranking_places_when_filtered(self):
        for index in range(6):
            player = self.create_player('higher-ranked-{}'.format(index))
            Season.objects.create(
                year=2024,
                player=player,
                club=player.current_club,
                rating=Decimal(100 - index),
            )
        first_woman = self.create_player('first-woman', gender='F')
        second_woman = self.create_player('second-woman', gender='F')
        Season.objects.create(year=2024, player=first_woman, club=first_woman.current_club, rating=Decimal('50.0000'))
        Season.objects.create(year=2024, player=second_woman, club=second_woman.current_club, rating=Decimal('40.0000'))

        response = self.client.get('/seasons/2024', {'sex': 'F'})

        self.assertEqual(response.status_code, 200)
        ranks = re.findall(r'<span class="players-rank-value">(\d+)</span>', response.content.decode())
        self.assertEqual(ranks[:2], ['7', '8'])

    def test_season_page_excludes_players_without_club(self):
        club_player = self.create_player('club-player')
        no_club_player = self.create_player('no-club-player', with_club=False)
        Season.objects.create(year=2024, player=club_player, club=club_player.current_club, rating=Decimal('10.0000'))
        Season.objects.create(year=2024, player=no_club_player, club=None, rating=Decimal('100.0000'))

        response = self.client.get('/seasons/2024')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, club_player.get_name())
        self.assertNotContains(response, no_club_player.get_name())
        ranks = re.findall(r'<span class="players-rank-value">(\d+)</span>', response.content.decode())
        self.assertEqual(ranks[:1], ['1'])

    def test_season_page_shows_club_logo_in_table(self):
        player = self.create_player('season-logo-player')
        player.current_club.logo = 'clubs/season-kpc.png'
        player.current_club.short_name = 'KPC'
        player.current_club.save()
        Season.objects.create(year=2024, player=player, club=player.current_club, rating=Decimal('10.0000'))

        response = self.client.get('/seasons/2024')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="players-club-logo"')
        self.assertContains(response, 'media/clubs/season-kpc.png')
        self.assertContains(response, 'alt="KPC"')

    def test_year_tabs_preserve_active_filters(self):
        player = self.create_player('filtered-player')
        Season.objects.create(year=2024, player=player, club=player.current_club, rating=Decimal('10.0000'))
        Season.objects.create(year=2025, player=player, club=player.current_club, rating=Decimal('20.0000'))

        response = self.client.get('/seasons/2025', {
            'q': 'filtered',
            'club': player.current_club.short_name,
            'age': 'SEN',
            'sex': 'M',
            'per_page': '25',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '/seasons/2024?q=filtered&amp;club=FILTERED-PLAYER&amp;age=SEN&amp;sex=M&amp;per_page=25',
        )


class PlayerProfileFormTests(TestCase):
    def test_profile_form_layout_renders_every_bound_field(self):
        form = PlayerForm()
        layout_fields = {
            pointer.name
            for pointer in form.helper.layout.get_field_names()
        }

        self.assertEqual(set(form.fields), layout_fields)


class PlayerLicenseListTests(TestCase):
    def create_player(self, username, is_licence_active=True, licence_number_value=None, current_club=None):
        user = User.objects.create_user(username=username)

        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
            is_licence_active=is_licence_active,
            licence_number=licence_number_value,
            current_club=current_club,
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

    def test_players_page_shows_no_license_for_inactive_player_with_old_number(self):
        player = self.create_player(
            'inactive-license-player',
            is_licence_active=False,
            licence_number_value='LEGACY-0002',
        )

        with override('uk'):
            response = self.client.get('/players/', {'q': player.surname})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, player.get_name())
        self.assertContains(response, 'Без ліцензії')
        self.assertNotContains(response, 'LEGACY-0002')

    def test_profile_form_save_preserves_non_profile_fields(self):
        player = self.create_player('licensed-profile', licence_number_value='00001')
        player.prefred_position = 'point'
        player.save()
        form = PlayerForm(data={
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': '',
            'country': 'UA',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': 'licensed-profile@example.com',
        }, instance=player)

        self.assertNotIn('licence_number', form.fields)
        self.assertNotIn('prefred_position', form.fields)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        player.refresh_from_db()

        self.assertEqual(player.licence_number, '00001')
        self.assertTrue(player.is_licence_active)
        self.assertEqual(player.prefred_position, 'point')

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

    def test_licensed_players_page_shows_club_logo_in_table(self):
        club = Club.objects.create(
            name='Kyiv Petanque Club',
            short_name='KPC',
            address='Kyiv',
            logo='clubs/kpc.png',
        )
        self.create_player('club-player', licence_number_value='00001', current_club=club)

        response = self.client.get('/players/licence')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="players-club-logo"')
        self.assertContains(response, 'media/clubs/kpc.png')
        self.assertContains(response, 'alt="KPC"')


class ClubListingPageTests(TestCase):
    def test_filter_form_has_reset_button_that_clears_query_params(self):
        response = self.client.get('/clubs/', {
            'q': 'Kyiv',
            'city': 'Kyiv',
            'year': '2024',
            'sort': 'name',
            'per_page': '50',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="tournament-reset-button clubs-reset-button"')
        self.assertContains(response, 'href="/clubs/?per_page=50"')
        self.assertContains(response, 'Скинути фільтри')


class ClubDetailPageTests(TestCase):
    def create_club(self, name='Kyiv Petanque Club', short_name='KPC'):
        return Club.objects.create(
            name=name,
            short_name=short_name,
            address='Kyiv',
        )

    def create_player(
        self,
        username,
        club,
        rating='0.0000',
        is_licence_active=True,
        licence_number=None,
    ):
        user = User.objects.create_user(username=username)
        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
            current_club=club,
            current_rating=Decimal(rating),
            current_power=Decimal('1.0000'),
            is_licence_active=is_licence_active,
            licence_number=licence_number if licence_number is not None else username,
        )

    def test_club_page_shows_all_members_but_rates_only_ranked_players(self):
        club = self.create_club()
        other_club = self.create_club(name='Lviv Petanque Club', short_name='LPC')
        active_player = self.create_player('active-player', club=club, rating='10.0000', licence_number='00001')
        inactive_player = self.create_player(
            'inactive-former-player',
            club=club,
            rating='50.0000',
            is_licence_active=False,
            licence_number='00002',
        )
        active_without_license = self.create_player(
            'active-without-license',
            club=club,
            rating='40.0000',
            licence_number='',
        )
        other_club_player = self.create_player(
            'other-club-player',
            club=other_club,
            rating='25.0000',
            licence_number='00003',
        )

        response = self.client.get(f'/club/{club.pk}')
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['players'].count(), 3)
        self.assertEqual(
            set(response.context['players'].values_list('pk', flat=True)),
            {active_player.pk, inactive_player.pk, active_without_license.pk},
        )
        self.assertEqual(response.context['club_stats']['players_count'], 3)
        self.assertEqual(response.context['club_stats']['total_rating'], Decimal('10.0000'))
        self.assertEqual(response.context['club_stats']['average_rating'], Decimal('10.0000'))
        self.assertContains(response, active_player.get_name())
        self.assertContains(response, inactive_player.get_name())
        self.assertContains(response, active_without_license.get_name())
        self.assertNotContains(response, other_club_player.get_name())

        active_card = re.search(
            rf'<a class="card athlete-card[^"]*" href="/player/{active_player.pk}".*?</a>',
            content,
            re.S,
        )
        inactive_card = re.search(
            rf'<a class="card athlete-card[^"]*" href="/player/{inactive_player.pk}".*?</a>',
            content,
            re.S,
        )
        unlicensed_card = re.search(
            rf'<a class="card athlete-card[^"]*" href="/player/{active_without_license.pk}".*?</a>',
            content,
            re.S,
        )

        self.assertIsNotNone(active_card)
        self.assertIsNotNone(inactive_card)
        self.assertIsNotNone(unlicensed_card)
        self.assertIn('athlete-card-rank', active_card.group(0))
        self.assertNotIn('athlete-card-rank', inactive_card.group(0))
        self.assertNotIn('athlete-card-rank', unlicensed_card.group(0))
        self.assertIn('<span class="athlete-chip-value">00001</span>', active_card.group(0))
        self.assertIn('<span class="athlete-chip-value">---</span>', inactive_card.group(0))
        self.assertIn('<span class="athlete-chip-value">---</span>', unlicensed_card.group(0))

    def test_clubs_page_counts_all_members_but_rates_only_ranked_players(self):
        club = self.create_club()
        self.create_player('active-player', club=club, rating='10.0000', licence_number='00001')
        self.create_player('inactive-former-player', club=club, rating='50.0000', is_licence_active=False, licence_number='00002')
        self.create_player('active-without-license', club=club, rating='40.0000', licence_number='')

        response = self.client.get('/clubs/')

        self.assertEqual(response.status_code, 200)
        club_row = next(item for item in response.context['clubs'] if item.pk == club.pk)
        self.assertEqual(club_row.players_count, 3)
        self.assertEqual(club_row.total_rating, Decimal('10.0000'))


class PlayerTournamentListTests(TestCase):
    def create_player(self, username='player-page'):
        user = User.objects.create_user(username=username)
        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def test_player_tournament_table_shows_place_range_and_tournament_power(self):
        player = self.create_player('range-player')
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

    def test_player_tournament_table_shows_placeholder_team_power_badge(self):
        player = self.create_player('missing-team-power-player')
        team = Team.objects.create(name='Missing Power Team')
        PlayerTeamMembership.objects.create(team=team, player=player, is_capitan=True)
        tournament = Tournament.objects.create(
            name='Missing Team Power Cup',
            category='open',
            is_goes_to_rating=True,
            start_date=timezone.localdate() - timedelta(days=7),
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            format='swiko',
            power='11.3700',
            is_processing_finished=True,
        )
        TeamTournamentMembership.objects.create(
            tournament=tournament,
            team=team,
            place_min=9,
            place_max=16,
            power='0.0000',
        )

        response = self.client.get(f'/player/{player.pk}')
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'player-team-power-missing')
        self.assertContains(response, '<span>---</span>', html=True)
        self.assertIn('team-power-badge player-team-power-missing', content)
        table_strength_cell = re.search(
            r'<td class="pt-col-strength"[^>]*>(.*?)</td>',
            content,
            re.S,
        ).group(1)
        self.assertLess(
            table_strength_cell.index('player-team-power-missing'),
            table_strength_cell.index('tournament-power-badge tournament-power-'),
        )

    def test_player_page_shows_single_national_team_chip_for_multiple_memberships(self):
        player = self.create_player('national-team-player')
        men_veterans = National_team.objects.create(name='Veterans Men')
        women_veterans = National_team.objects.create(name='Veterans Women')
        PlayerNational_teamMembership.objects.create(
            player=player,
            team=men_veterans,
            position='player',
        )
        PlayerNational_teamMembership.objects.create(
            player=player,
            team=women_veterans,
            position='player',
        )

        response = self.client.get(f'/player/{player.pk}')
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content.count('player-chip-national-team'), 1)


class TournamentRegistrationLifecycleTests(TestCase):
    def setUp(self):
        self.now = timezone.make_aware(datetime.datetime(2026, 6, 15, 9, 0))

    def create_tournament(self, deadline):
        return Tournament.objects.create(
            name='Registration Lifecycle Cup',
            category='open',
            place='Київ',
            start_date=self.now.date(),
            start_time=datetime.time(12, 0),
            end_date=self.now.date(),
            date_registration_stop=deadline,
            number_of_players_in_team_min=1,
            number_of_players_in_team_max=1,
            format='ko',
        )

    def create_player(self):
        user = User.objects.create_user(username='registration-player')
        return Player.objects.create(
            user=user,
            name='Registration',
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
        )

    def test_extending_closed_deadline_reopens_same_day_registration(self):
        tournament = self.create_tournament(self.now - timedelta(minutes=1))

        with patch('django.utils.timezone.now', return_value=self.now):
            self.assertFalse(tournament.is_registration_opened())
            self.assertNotEqual(_tournament_status_key(tournament), 'registration_open')

            tournament.date_registration_stop = self.now + timedelta(hours=1)
            tournament.save(update_fields=['date_registration_stop'])

            self.assertTrue(tournament.is_registration_opened())
            self.assertEqual(_tournament_status_key(tournament), 'registration_open')

    def test_registration_post_is_blocked_when_closed_and_allowed_after_reopening(self):
        tournament = self.create_tournament(self.now - timedelta(minutes=1))
        player = self.create_player()
        registration_url = f'/register/team/{tournament.pk}/'
        registration_data = {'players[1]': str(player.pk)}

        with patch('django.utils.timezone.now', return_value=self.now):
            closed_response = self.client.post(registration_url, registration_data)

            self.assertEqual(closed_response.status_code, 200)
            self.assertFalse(closed_response.context['is_registration_opened'])
            self.assertFalse(
                TeamTournamentMembership.objects.filter(tournament=tournament).exists()
            )

            tournament.date_registration_stop = self.now + timedelta(hours=1)
            tournament.save(update_fields=['date_registration_stop'])

            reopened_response = self.client.post(registration_url, registration_data)

            self.assertEqual(reopened_response.status_code, 302)
            self.assertTrue(
                TeamTournamentMembership.objects.filter(tournament=tournament).exists()
            )


class TournamentPowerAdminActionTests(SimpleTestCase):
    def run_action(self, tournament):
        request = SimpleNamespace(POST={'post': 'yes'})
        with (
            patch('federation.admin_actions.tournament.messages.success') as success,
            patch('federation.admin_actions.tournament.messages.error') as error,
            patch('federation.admin_actions.tournament.transaction.atomic', return_value=nullcontext()),
        ):
            recalculate_power(None, request, [tournament])
        return success, error

    def test_recalculates_provisional_power_before_processing_is_ready(self):
        tournament = SimpleNamespace(
            name='Registration Cup',
            recalculate_power_for_current_state=Mock(return_value=True),
        )

        success, error = self.run_action(tournament)

        tournament.recalculate_power_for_current_state.assert_called_once_with()
        success.assert_called_once()
        error.assert_not_called()

    def test_provisional_power_recalculation_reports_success(self):
        memberships = [
            SimpleNamespace(power=Decimal('31.0000'), recalculate_power=Mock()),
            SimpleNamespace(power=Decimal('8.3125'), recalculate_power=Mock()),
        ]
        tournament = Tournament(
            name='Registration Cup',
            category='open',
            number_of_players_in_team_min=2,
        )
        tournament.get_teams_count = Mock(return_value=len(memberships))
        tournament.get_teams = Mock(side_effect=[memberships, memberships])
        tournament.save = Mock()

        result = tournament.recalculate_power_on_registration()

        self.assertTrue(result)
        self.assertEqual(tournament.power, Decimal('2.45703125'))
        tournament.save.assert_called_once_with()

    def test_power_recalculation_uses_provisional_calculation_before_processing_is_ready(self):
        tournament = Tournament(is_ready_for_processing=False)
        tournament.recalculate_power = Mock()
        tournament.recalculate_power_on_registration = Mock(return_value=True)

        result = tournament.recalculate_power_for_current_state()

        self.assertTrue(result)
        tournament.recalculate_power_on_registration.assert_called_once_with()
        tournament.recalculate_power.assert_not_called()

    def test_power_recalculation_uses_final_calculation_after_processing_is_ready(self):
        tournament = Tournament(is_ready_for_processing=True)
        tournament.recalculate_power = Mock()
        tournament.recalculate_power_on_registration = Mock()

        result = tournament.recalculate_power_for_current_state()

        self.assertTrue(result)
        tournament.recalculate_power.assert_called_once_with()
        tournament.recalculate_power_on_registration.assert_not_called()

    def test_admin_inline_team_change_refreshes_power_for_current_state(self):
        tournament = SimpleNamespace(
            is_processing_closed=Mock(return_value=False),
            recalculate_power_for_current_state=Mock(return_value=True),
        )
        form = SimpleNamespace(instance=tournament)
        formset = SimpleNamespace(
            model=TeamTournamentMembership,
            forms=[SimpleNamespace(has_changed=Mock(return_value=True))],
        )
        tournament_admin = ArbiterTeamTournamentAdminInline(Tournament, AdminSite())

        with patch('django.contrib.admin.options.ModelAdmin.save_formset'):
            tournament_admin.save_formset(None, form, formset, True)

        tournament.recalculate_power_for_current_state.assert_called_once_with()


@override_settings(MEDIA_URL='/media/')
class TournamentTeamExportJsonTests(TestCase):
    def create_club(self, name, short_name, logo):
        return Club.objects.create(
            name=name,
            short_name=short_name,
            address='Kyiv',
            logo=logo,
        )

    def create_player(
        self,
        username,
        club=None,
        rating='0.0000',
        avatar='',
        is_licence_active=True,
        licence_number=None,
    ):
        user = User.objects.create_user(username=username)
        return Player.objects.create(
            user=user,
            name=username.title(),
            surname='Player',
            birth_date=date(1990, 1, 1),
            gender='M',
            current_club=club,
            current_rating=Decimal(rating),
            is_licence_active=is_licence_active,
            licence_number=licence_number if licence_number is not None else username,
            avatar=avatar,
        )

    def create_tournament(self):
        return Tournament.objects.create(
            name='Export Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 6, 1),
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            format='swiko',
        )

    def create_team_membership(self, tournament, players, name, place_min, power='0.0000'):
        team = Team.objects.create(name=name)
        for index, player in enumerate(players):
            PlayerTeamMembership.objects.create(team=team, player=player, is_capitan=index == 0)

        return TeamTournamentMembership.objects.create(
            tournament=tournament,
            team=team,
            place_min=place_min,
            power=Decimal(power),
        )

    def test_json_export_includes_images_shared_club_power_and_player_rating_places(self):
        club = self.create_club('Kyiv Petanque Club', 'KPC', 'clubs/kpc.png')
        other_club = self.create_club('Lviv Petanque Club', 'LPC', 'clubs/lpc.png')
        self.create_player('ranking-leader', club=other_club, rating='200.0000')
        first = self.create_player('first', club=club, rating='100.0000', avatar='avatars/first.png')
        second = self.create_player('second', club=club, rating='50.0000', avatar='avatars/second.png')
        mixed = self.create_player('mixed', club=other_club, rating='25.0000')
        tournament = self.create_tournament()
        same_club_membership = self.create_team_membership(
            tournament,
            [first, second],
            'Kyiv Pair',
            place_min=1,
            power='12.3400',
        )
        self.create_team_membership(
            tournament,
            [first, mixed],
            'Mixed Pair',
            place_min=2,
            power='8.0000',
        )

        response = self.client.get('/tournament/team_export/{}'.format(tournament.pk), {'format': 'json'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['tournament']['player_rating_field'], 'current_rating')
        same_club_team = data['teams'][0]
        self.assertEqual(same_club_team['id'], same_club_membership.team.pk)
        self.assertEqual(same_club_team['team_power'], '12.3400')
        self.assertEqual(same_club_team['power'], '12.3400')
        self.assertEqual(same_club_team['club'], {
            'id': club.pk,
            'name': 'Kyiv Petanque Club',
            'short_name': 'KPC',
            'logo_url': 'http://testserver/media/clubs/kpc.png',
        })
        self.assertEqual(same_club_team['club_logo_url'], 'http://testserver/media/clubs/kpc.png')

        players_by_id = {player['id']: player for player in same_club_team['players']}
        self.assertEqual(players_by_id[first.pk]['avatar_url'], 'http://testserver/media/avatars/first.png')
        self.assertEqual(players_by_id[first.pk]['club_short_name'], 'KPC')
        self.assertEqual(players_by_id[first.pk]['club_logo_url'], 'http://testserver/media/clubs/kpc.png')
        self.assertEqual(players_by_id[first.pk]['rating'], '100.0000')
        self.assertEqual(players_by_id[first.pk]['rating_field'], 'current_rating')
        self.assertEqual(players_by_id[first.pk]['rating_place'], 2)
        self.assertEqual(players_by_id[second.pk]['avatar_url'], 'http://testserver/media/avatars/second.png')
        self.assertEqual(players_by_id[second.pk]['rating_place'], 3)

        mixed_team = data['teams'][1]
        self.assertIsNone(mixed_team['club'])
        self.assertIsNone(mixed_team['club_logo_url'])


class OptionalRegistrationEmailTests(TestCase):
    @override_settings(DEBUG=True, RECAPTCHA_PUBLIC_KEY=None, RECAPTCHA_PRIVATE_KEY=None)
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


@override_settings(DEBUG=True, RECAPTCHA_PUBLIC_KEY=None, RECAPTCHA_PRIVATE_KEY=None)
class PlayerRegistrationRedesignTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            'name': 'No',
            'surname': 'Password',
            'patronymic': 'Required',
            'birth_date': '01.01.1990',
            'country': 'UA',
            'gender': 'M',
            'licence_number': '',
            'autocaptcha_token': '',
        }
        data.update(overrides)
        return data

    def test_page_uses_redesigned_form_custom_date_picker_and_search_panel(self):
        response = self.client.get('/register/player/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'registration-redesign')
        self.assertContains(response, 'id="player-existence-search"')
        self.assertContains(response, 'data-search-url="/api/players_list/list/"')
        self.assertContains(response, 'data-date-picker')
        self.assertContains(response, 'data-date-picker-panel')
        self.assertContains(response, 'id="id_birth_date"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'id="account-access-field-group"')
        self.assertContains(response, 'id="id_email"')
        self.assertContains(response, 'id="id_password"')
        self.assertContains(response, 'id="id_password_confirm"')
        self.assertNotContains(response, 'type="date"')
        self.assertNotContains(response, '$(".dateinput").datepicker')

    def test_registration_form_accepts_redesigned_required_fields_without_password(self):
        form = RegistrationPlayerForm(data=self.registration_data())

        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_registration_form_rejects_future_birth_date(self):
        future_birth_date = timezone.localdate() + timedelta(days=1)
        form = RegistrationPlayerForm(data=self.registration_data(
            birth_date=future_birth_date.strftime('%d.%m.%Y'),
        ))

        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)

    def test_player_registration_creates_user_with_unusable_password(self):
        response = self.client.post('/register/player/', self.registration_data())

        self.assertEqual(response.status_code, 302)
        player = Player.objects.get(name='No', surname='Password')
        self.assertFalse(player.user.has_usable_password())

    def test_non_ukrainian_registration_ignores_optional_account_fields(self):
        form = RegistrationPlayerForm(data=self.registration_data(
            country='PL',
            patronymic='Should clear',
            email='ignored@example.com',
            password='StrongPass123!',
            password_confirm='StrongPass123!',
        ))

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.cleaned_data['patronymic'], '')
        self.assertEqual(form.cleaned_data['email'], '')
        self.assertEqual(form.cleaned_data['password'], '')

    @patch('federation.views.register.send_confirmation_email')
    def test_player_registration_with_account_credentials_sets_email_password_and_confirmation(self, send_email):
        response = self.client.post('/register/player/', self.registration_data(
            name='Cabinet',
            surname='Access',
            email='cabinet-access@example.com',
            password='StrongPass123!',
            password_confirm='StrongPass123!',
        ))

        self.assertEqual(response.status_code, 302)
        player = Player.objects.get(name='Cabinet', surname='Access')
        self.assertEqual(player.user.email, 'cabinet-access@example.com')
        self.assertTrue(player.user.has_usable_password())
        self.assertTrue(player.user.check_password('StrongPass123!'))
        confirmation = EmailConfirmation.objects.get(user=player.user)
        self.assertEqual(confirmation.email, 'cabinet-access@example.com')
        send_email.assert_called_once()


@override_settings(DEBUG=True, RECAPTCHA_PUBLIC_KEY=None, RECAPTCHA_PRIVATE_KEY=None)
class TeamRegistrationRedesignTests(TestCase):
    def test_page_uses_tournament_detail_summary_and_hides_export_actions(self):
        start_date = (timezone.now() + timedelta(days=30)).date()
        tournament = Tournament.objects.create(
            name='International Cup',
            category='away',
            place='Польща',
            start_date=start_date,
            start_time=datetime.time(10, 0),
            date_registration_stop=timezone.now() + timedelta(days=29),
            number_of_players_in_team_min=1,
            number_of_players_in_team_max=1,
            teams_limit=100,
            format='swiko',
        )

        response = self.client.get(f'/register/team/{tournament.pk}')
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tournament-detail-breadcrumbs')
        self.assertContains(response, 'tournament-detail-title')
        self.assertContains(response, 'registration-team-form')
        self.assertContains(response, 'dropdownParent: $field.closest(')
        self.assertContains(response, 'tournament-registration-add-player-link')
        self.assertContains(response, '1 гравець')
        self.assertContains(response, 'Польща')
        self.assertContains(response, 'name="players[1]"')
        self.assertNotContains(response, 'tournament-detail-export')
        self.assertRegex(content, r'style-v2\.css\?v=[0-9a-f]{12}')
        self.assertRegex(content, r'portal-ui\.js\?v=[0-9a-f]{12}')
        self.assertNotIn('20260609-review-hardcode-cleanup-v1', content)

    def test_team_registration_fields_render_capitan_first(self):
        start_date = (timezone.now() + timedelta(days=30)).date()
        tournament = Tournament.objects.create(
            name='International Cup',
            category='away',
            place='Польща',
            start_date=start_date,
            start_time=datetime.time(10, 0),
            date_registration_stop=timezone.now() + timedelta(days=29),
            number_of_players_in_team_min=3,
            number_of_players_in_team_max=4,
            teams_limit=100,
            format='swiko',
        )

        response = self.client.get(f'/register/team/{tournament.pk}')

        content = response.content.decode()
        player_field_positions = [
            content.index('name="players[1]"'),
            content.index('name="players[2]"'),
            content.index('name="players[3]"'),
            content.index('name="players[4]"'),
        ]
        self.assertEqual(player_field_positions, sorted(player_field_positions))

    def test_team_registration_form_keeps_capitan_first_team_creation_order(self):
        start_date = (timezone.now() + timedelta(days=30)).date()
        tournament = Tournament.objects.create(
            name='International Cup',
            category='away',
            place='Польща',
            start_date=start_date,
            start_time=datetime.time(10, 0),
            date_registration_stop=timezone.now() + timedelta(days=29),
            number_of_players_in_team_min=2,
            number_of_players_in_team_max=2,
            teams_limit=100,
            format='swiko',
        )
        capitan = Player.objects.create(
            user=User.objects.create_user(username='team-capitan'),
            name='Team',
            surname='Capitan',
            birth_date=date(1990, 1, 1),
            gender='M',
        )
        teammate = Player.objects.create(
            user=User.objects.create_user(username='team-player'),
            name='Team',
            surname='Player',
            birth_date=date(1991, 1, 1),
            gender='M',
        )

        form = RegistrationTeamForm(
            data={
                'players[1]': str(capitan.pk),
                'players[2]': str(teammate.pk),
            },
            tournament=tournament,
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.verified_player_ids, [teammate.pk, capitan.pk])

        team = Team.get_or_create_for_players(list(reversed(form.verified_player_ids)))

        self.assertEqual(team.get_capitan(), capitan)


@override_settings(
    DEBUG=False,
    RECAPTCHA_PUBLIC_KEY='public-key',
    RECAPTCHA_PRIVATE_KEY='private-key',
    AUTO_CAPTCHA_SCORE_THRESHOLD=0.5,
)
class AutoCaptchaRegistrationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def registration_data(self, **overrides):
        data = {
            'name': 'Auto',
            'surname': 'Human',
            'birth_date': '1990-01-01',
            'country': 'UA',
            'email': '',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'gender': 'M',
            'autocaptcha_token': 'valid-token',
        }
        data.update(overrides)
        return data

    def request(self):
        return self.factory.post('/register/player/', REMOTE_ADDR='203.0.113.10')

    def mock_response(self, urlopen_mock, **overrides):
        payload = {
            'success': True,
            'score': 0.9,
            'action': 'player_registration',
        }
        payload.update(overrides)
        response = urlopen_mock.return_value.__enter__.return_value
        response.read.return_value = json.dumps(payload).encode('utf-8')

    def assert_non_field_error_code(self, form, code):
        errors = form.non_field_errors().as_data()
        self.assertTrue(errors)
        self.assertEqual(errors[0].code, code)

    @patch('federation.utils.autocaptcha.urlopen')
    def test_accepts_valid_automatic_verification(self, urlopen_mock):
        self.mock_response(urlopen_mock)
        form = RegistrationPlayerForm(data=self.registration_data(), request=self.request())

        self.assertTrue(form.is_valid(), form.errors.as_json())

        verify_request = urlopen_mock.call_args.args[0]
        verify_payload = parse_qs(verify_request.data.decode('utf-8'))
        self.assertEqual(verify_payload['secret'], ['private-key'])
        self.assertEqual(verify_payload['response'], ['valid-token'])
        self.assertEqual(verify_payload['remoteip'], ['203.0.113.10'])

    @patch('federation.utils.autocaptcha.urlopen')
    def test_rejects_missing_automatic_verification_token(self, urlopen_mock):
        form = RegistrationPlayerForm(
            data=self.registration_data(autocaptcha_token=''),
            request=self.request(),
        )

        self.assertFalse(form.is_valid())
        self.assert_non_field_error_code(form, 'autocaptcha_missing')
        urlopen_mock.assert_not_called()

    @patch('federation.utils.autocaptcha.urlopen')
    def test_rejects_low_automatic_verification_score(self, urlopen_mock):
        self.mock_response(urlopen_mock, score=0.1)
        form = RegistrationPlayerForm(data=self.registration_data(), request=self.request())

        self.assertFalse(form.is_valid())
        self.assert_non_field_error_code(form, 'autocaptcha_low_score')

    @patch('federation.utils.autocaptcha.urlopen')
    def test_rejects_wrong_automatic_verification_action(self, urlopen_mock):
        self.mock_response(urlopen_mock, action='login')
        form = RegistrationPlayerForm(data=self.registration_data(), request=self.request())

        self.assertFalse(form.is_valid())
        self.assert_non_field_error_code(form, 'autocaptcha_action')

    @override_settings(DEBUG=True, RECAPTCHA_PUBLIC_KEY=None, RECAPTCHA_PRIVATE_KEY=None)
    def test_debug_without_keys_allows_local_form_validation(self):
        form = RegistrationPlayerForm(
            data=self.registration_data(autocaptcha_token=''),
            request=self.request(),
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())


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

    def test_tournament_detail_shows_rating_column_without_points_until_processing_is_finished(self):
        tournament = self.create_tournament('Unprocessed rating cup', is_rating=True)
        player = self.create_player('unprocessed-player')
        membership = self.register_player_for_tournament(tournament, player, place_min=1)
        membership.rating_points = '14.5000'
        membership.save(update_fields=['rating_points'])

        response = self.client.get(f'/tournament/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tournament-team-score-col')
        self.assertContains(response, 'tournament-team-score-cell')
        self.assertContains(response, 'has-rating-points')
        self.assertNotContains(response, '14,50')

    def test_tournament_detail_shows_rating_points_after_processing_is_finished(self):
        tournament = self.create_tournament(
            'Processed rating cup',
            is_rating=True,
            processed=True,
        )
        player = self.create_player('processed-player')
        membership = self.register_player_for_tournament(tournament, player, place_min=1)
        membership.rating_points = '14.5000'
        membership.save(update_fields=['rating_points'])

        response = self.client.get(f'/tournament/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tournament-team-score-col')
        self.assertContains(response, 'tournament-team-score-cell')
        self.assertContains(response, 'has-rating-points')
        self.assertContains(response, '14,50')
        self.assertContains(response, 'tournament-team-mobile-card')
        self.assertContains(response, 'tournament-team-mobile-content')

    def test_tournament_detail_only_displays_public_admin_notes(self):
        delegate = self.create_player('delegate-player')
        tournament = self.create_tournament('Public Notes Cup')
        tournament.notes = 'Public tournament note'
        tournament.fee = 'Hidden fee note'
        tournament.meta = 'Hidden draw information'
        tournament.final_notes = 'Hidden final protocol note'
        tournament.federation_delegat = delegate
        tournament.save()

        response = self.client.get(f'/tournament/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public tournament note')
        html = response.content.decode()
        note_start = html.index('<div class="tournament-detail-note">')
        note_content_start = html.index('Public tournament note', note_start)
        self.assertNotIn('bi-info-circle', html[note_start:note_content_start])
        self.assertNotContains(response, 'Hidden fee note')
        self.assertNotContains(response, 'Hidden draw information')
        self.assertNotContains(response, 'Hidden final protocol note')
        self.assertNotContains(response, delegate.get_name())
        self.assertNotContains(response, 'tournament-notes-tab')
        self.assertNotContains(response, 'tournament_notes_content')

    def test_tournament_detail_ignores_technical_meta_for_status(self):
        tournament = self.create_tournament('Technical Meta Cup')
        tournament.meta = '111111111111111111'
        tournament.save(update_fields=['meta'])

        response = self.client.get(f'/tournament/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '111111111111111111')

    def test_tournament_detail_manager_can_edit_public_notes_inline(self):
        admin = User.objects.create_superuser(
            username='tournament-admin',
            email='tournament-admin@example.com',
            password='password',
        )
        tournament = self.create_tournament('Editable Notes Cup')
        tournament.final_notes = 'Protocol-only note'
        tournament.save(update_fields=['final_notes'])

        self.client.force_login(admin)
        response = self.client.get(f'/tournament/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-tournament-notes-edit')
        self.assertContains(response, 'tournament_detail_notes_content')
        self.assertContains(response, 'tournament-detail-empty-inline')

        response = self.client.post(
            f'/tournament/{tournament.pk}',
            {'tournament_detail_notes_content': 'Saved public note'},
        )

        self.assertEqual(response.status_code, 302)
        tournament.refresh_from_db()
        self.assertEqual(tournament.notes, 'Saved public note')
        self.assertEqual(tournament.final_notes, 'Protocol-only note')

    def test_tournament_detail_team_table_uses_plain_captain_and_lists_all_athletes(self):
        tournament = self.create_tournament('Captain Table Cup')
        captain = self.create_player('captain-table')
        teammate = self.create_player('teammate-table')
        team = Team.objects.create()
        PlayerTeamMembership.objects.create(team=team, player=captain, is_capitan=True)
        PlayerTeamMembership.objects.create(team=team, player=teammate)
        TeamTournamentMembership.objects.create(tournament=tournament, team=team)

        response = self.client.get(f'/tournament/{tournament.pk}')
        html = response.content.decode()
        captain_cell = re.search(
            r'<td class="tournament-team-name-cell"[^>]*>(.*?)</td>',
            html,
            re.S,
        ).group(1)
        athletes_cell = re.search(
            r'<td class="tournament-team-athletes-cell"[^>]*>(.*?)</td>',
            html,
            re.S,
        ).group(1)
        mobile_captain_section = re.search(
            r'<section class="tournament-team-mobile-people">\s*<h3>.*?</h3>(.*?)</section>',
            html,
            re.S,
        ).group(1)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="tournament-team-captain-name"', captain_cell)
        self.assertIn(captain.get_name(), captain_cell)
        self.assertNotIn('tournament-team-player-avatar', captain_cell)
        self.assertNotIn('flag-icon', captain_cell)
        self.assertIn('class="tournament-team-captain-name"', mobile_captain_section)
        self.assertIn(captain.get_name(), mobile_captain_section)
        self.assertNotIn('tournament-team-player-avatar', mobile_captain_section)
        self.assertNotIn('flag-icon', mobile_captain_section)
        self.assertIn(captain.get_name(), athletes_cell)
        self.assertIn(teammate.get_name(), athletes_cell)
        self.assertContains(response, 'data-tournament-team-sort="place"')
        self.assertContains(response, 'data-tournament-team-sort="power"')
        self.assertContains(response, 'class="tournament-team-player-label"')
        self.assertContains(response, 'class="tournament-team-player-country"')

    def test_tournament_detail_unready_tournament_does_not_show_place_editor(self):
        admin = User.objects.create_superuser(
            username='place-editor-admin',
            email='place-editor-admin@example.com',
            password='password',
        )
        tournament = self.create_tournament('Unready Places Cup', is_rating=True)
        player = self.create_player('unready-place-player')
        self.register_player_for_tournament(tournament, player)

        self.client.force_login(admin)
        response = self.client.get(f'/tournament/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pt-place-chip')
        self.assertContains(response, '<span class="pt-place-value">-</span>', html=True)
        self.assertNotContains(response, 'class="tournament-ranking-place-input tournament-place-field-min"')
        self.assertNotContains(response, 'class="tournament-ranking-place-input tournament-place-field-max"')

    def test_tournament_detail_single_player_table_shows_club(self):
        club = Club.objects.create(
            name='Kyiv Petanque Club',
            short_name='KPC',
            address='Kyiv',
            logo='clubs/kpc.png',
        )
        tournament = self.create_tournament('Tete Club Cup', players_min=1)
        player = self.create_player('club-participant')
        player.current_club = club
        player.save(update_fields=['current_club'])
        self.register_player_for_tournament(tournament, player, place_min=1)

        response = self.client.get(f'/tournament/{tournament.pk}')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is-single-player-format')
        self.assertContains(response, 'tournament-team-club-col')
        self.assertContains(response, 'tournament-team-club-cell')
        self.assertContains(response, 'tournament-team-club-logo')
        self.assertContains(response, 'tournament-team-club-name')
        self.assertContains(response, 'tournament-team-player-club-mobile')
        self.assertNotContains(response, 'tournament-team-mobile-club-link')
        self.assertContains(response, 'KPC')

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
