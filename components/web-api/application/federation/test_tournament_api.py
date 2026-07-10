import json
from datetime import date

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from federation.audit import (
    SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME,
    SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME,
    extract_changed_field_values,
)
from federation.models.player import Player
from federation.models.team import PlayerTeamMembership, Team
from federation.models.tournament import TeamTournamentMembership, Tournament

API_PASSWORD = 'test-api-password'
AUTH = {'headers': {'authorization': API_PASSWORD}}

# The primary endpoint and its backward-compatibility alias share one handler —
# every behaviour that both must offer is asserted against both URLs.
PRIMARY_URL = '/api/tournament/'
LEGACY_URL = '/api/tournament/results/'
BOTH_URLS = (PRIMARY_URL, LEGACY_URL)


def draw_payload(**overrides):
    """A draw object shaped like what the external tool sends."""
    payload = {
        'name': 'Meta Cup. Triplets',
        'system': 'swiss',
        'tournamentIsFinished': False,
        'teams': [{'name': 'PLAYER One'}, {'name': 'PLAYER Two'}],
        'games': [[{
            'team_1': 'PLAYER One', 'team_1_score': 13,
            'team_2': 'PLAYER Two', 'team_2_score': 7,
        }]],
    }
    payload.update(overrides)
    return payload


@override_settings(API_PASSWORD=API_PASSWORD)
class TournamentApiTestCase(TestCase):
    def setUp(self):
        self.tournament = Tournament.objects.create(
            name='Api Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 7, 1),
            format='swiko',
        )

    def post(self, url, body, **kwargs):
        data = body if isinstance(body, str) else json.dumps(body)
        return self.client.post(url, data, content_type='application/json', **kwargs)

    def refreshed(self):
        self.tournament.refresh_from_db()
        return self.tournament

    def register_team(self, player_name, place_min=0):
        user = User.objects.create_user(
            username=f'api-player-{Player.objects.count()}-{player_name}'[:150],
            password='ApiPass123!',
        )
        player = Player.objects.create(
            user=user, name=player_name, surname='Player', birth_date=date(1990, 1, 1),
            country='UA', gender='M',
        )
        team = Team.objects.create()
        PlayerTeamMembership.objects.create(team=team, player=player)
        return TeamTournamentMembership.objects.create(
            tournament=self.tournament, team=team, place_min=place_min,
        )


class TournamentApiAuthTests(TournamentApiTestCase):
    def test_both_endpoints_reject_missing_api_password(self):
        for url in BOTH_URLS:
            with self.subTest(url=url):
                response = self.post(url, {
                    'tournament_id': self.tournament.pk,
                    'petanque_draw_id': 'draw-1',
                })

                self.assertEqual(response.status_code, 401)
                self.assertEqual(self.refreshed().petanque_draw_id, '')

    def test_both_endpoints_reject_wrong_api_password(self):
        for url in BOTH_URLS:
            with self.subTest(url=url):
                response = self.post(
                    url,
                    {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-1'},
                    headers={'authorization': 'wrong'},
                )

                self.assertEqual(response.status_code, 401)

    @override_settings(API_PASSWORD=None)
    def test_both_endpoints_fail_closed_when_password_unconfigured(self):
        for url in BOTH_URLS:
            with self.subTest(url=url):
                response = self.post(
                    url,
                    {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-1'},
                    **AUTH,
                )

                self.assertEqual(response.status_code, 401)

    def test_both_endpoints_reject_get(self):
        for url in BOTH_URLS:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, **AUTH).status_code, 405)

    def test_both_endpoints_accept_no_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        for url in BOTH_URLS:
            with self.subTest(url=url):
                response = csrf_client.post(
                    url,
                    json.dumps({'tournament_id': self.tournament.pk, 'petanque_draw_id': 'd'}),
                    content_type='application/json',
                    **AUTH,
                )

                self.assertEqual(response.status_code, 200)


class TournamentApiMetaTests(TournamentApiTestCase):
    def test_meta_object_is_stored_as_json_on_both_endpoints(self):
        for url in BOTH_URLS:
            with self.subTest(url=url):
                Tournament.objects.filter(pk=self.tournament.pk).update(meta=None)

                response = self.post(
                    url, {'tournament_id': self.tournament.pk, 'meta': draw_payload()}, **AUTH,
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(json.loads(self.refreshed().meta), draw_payload())

    def test_meta_accepts_preserialized_string(self):
        raw = json.dumps(draw_payload())

        response = self.post(
            PRIMARY_URL, {'tournament_id': self.tournament.pk, 'meta': raw}, **AUTH,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(self.refreshed().meta), draw_payload())

    def test_meta_without_draw_shape_rejected(self):
        for meta in ({'foo': 'bar'}, {'games': []}, [], 'not json', 5):
            with self.subTest(meta=meta):
                response = self.post(
                    PRIMARY_URL, {'tournament_id': self.tournament.pk, 'meta': meta}, **AUTH,
                )

                self.assertEqual(response.status_code, 400)
                self.assertIsNone(self.refreshed().meta)

    def test_oversized_meta_rejected(self):
        oversized = draw_payload(padding='x' * (300 * 1024))

        response = self.post(
            PRIMARY_URL, {'tournament_id': self.tournament.pk, 'meta': oversized}, **AUTH,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.refreshed().meta)

    def test_meta_rejected_once_processing_finished(self):
        self.tournament.is_processing_finished = True
        self.tournament.save()

        response = self.post(
            PRIMARY_URL, {'tournament_id': self.tournament.pk, 'meta': draw_payload()}, **AUTH,
        )

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.refreshed().meta)

    def test_meta_change_audited_under_system_draw_user(self):
        self.post(PRIMARY_URL, {'tournament_id': self.tournament.pk, 'meta': draw_payload()}, **AUTH)

        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user.username, SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME)


class TournamentApiDrawIdTests(TournamentApiTestCase):
    def test_draw_id_is_blank_by_default(self):
        self.assertEqual(self.tournament.petanque_draw_id, '')

    def test_draw_id_is_set_on_both_endpoints(self):
        for url, value in zip(BOTH_URLS, ('draw-primary', 'draw-legacy')):
            with self.subTest(url=url):
                response = self.post(
                    url, {'tournament_id': self.tournament.pk, 'petanque_draw_id': value}, **AUTH,
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.refreshed().petanque_draw_id, value)

    def test_draw_id_can_be_cleared(self):
        self.tournament.petanque_draw_id = 'draw-1'
        self.tournament.save()

        self.post(PRIMARY_URL, {'tournament_id': self.tournament.pk, 'petanque_draw_id': ''}, **AUTH)

        self.assertEqual(self.refreshed().petanque_draw_id, '')

    def test_non_string_draw_id_rejected(self):
        response = self.post(
            PRIMARY_URL, {'tournament_id': self.tournament.pk, 'petanque_draw_id': 123}, **AUTH,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.refreshed().petanque_draw_id, '')

    def test_draw_id_change_audited_under_system_draw_user(self):
        self.post(
            PRIMARY_URL, {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-1'}, **AUTH,
        )

        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user.username, SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME)
        values = extract_changed_field_values(log_entry.change_message)
        self.assertEqual(values['petanque_draw_id'], {'old': '', 'new': 'draw-1'})


class TournamentApiResultsTests(TournamentApiTestCase):
    def test_results_are_applied_on_both_endpoints(self):
        for url in BOTH_URLS:
            with self.subTest(url=url):
                membership = self.register_team('Winner' + url)

                response = self.post(url, {
                    'tournament_id': self.tournament.pk,
                    'teams': [{'team_id': membership.team_id, 'place_min': 1}],
                }, **AUTH)

                membership.refresh_from_db()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['updated_teams'], [membership.team_id])
                self.assertEqual(membership.place_min, 1)

    def test_shared_places_are_applied(self):
        membership = self.register_team('Shared')

        self.post(PRIMARY_URL, {
            'tournament_id': self.tournament.pk,
            'teams': [{'team_id': membership.team_id, 'place_min': 3, 'place_max': 4}],
        }, **AUTH)

        membership.refresh_from_db()
        self.assertEqual((membership.place_min, membership.place_max), (3, 4))

    def test_unregistered_team_rejects_whole_submission(self):
        membership = self.register_team('Registered')

        response = self.post(PRIMARY_URL, {
            'tournament_id': self.tournament.pk,
            'teams': [
                {'team_id': membership.team_id, 'place_min': 1},
                {'team_id': 999999, 'place_min': 2},
            ],
        }, **AUTH)

        membership.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(membership.place_min, 0)

    def test_empty_teams_list_rejected(self):
        response = self.post(
            PRIMARY_URL, {'tournament_id': self.tournament.pk, 'teams': []}, **AUTH,
        )

        self.assertEqual(response.status_code, 400)

    def test_results_change_audited_under_system_results_user(self):
        membership = self.register_team('Audited')

        self.post(PRIMARY_URL, {
            'tournament_id': self.tournament.pk,
            'teams': [{'team_id': membership.team_id, 'place_min': 1}],
        }, **AUTH)

        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user.username, SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME)


class TournamentApiCombinedTests(TournamentApiTestCase):
    def test_all_three_attributes_in_one_request(self):
        membership = self.register_team('Combined')

        response = self.post(PRIMARY_URL, {
            'tournament_id': self.tournament.pk,
            'meta': draw_payload(),
            'petanque_draw_id': 'draw-1',
            'teams': [{'team_id': membership.team_id, 'place_min': 1}],
        }, **AUTH)

        tournament = self.refreshed()
        membership.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(tournament.meta), draw_payload())
        self.assertEqual(tournament.petanque_draw_id, 'draw-1')
        self.assertEqual(membership.place_min, 1)
        self.assertEqual(response.json()['updated_teams'], [membership.team_id])

    def test_invalid_team_rolls_back_meta_and_draw_id(self):
        response = self.post(PRIMARY_URL, {
            'tournament_id': self.tournament.pk,
            'meta': draw_payload(),
            'petanque_draw_id': 'draw-1',
            'teams': [{'team_id': 999999, 'place_min': 1}],
        }, **AUTH)

        tournament = self.refreshed()
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(tournament.meta)
        self.assertEqual(tournament.petanque_draw_id, '')

    def test_request_without_any_attribute_rejected(self):
        response = self.post(PRIMARY_URL, {'tournament_id': self.tournament.pk}, **AUTH)

        self.assertEqual(response.status_code, 400)

    def test_missing_tournament_id_rejected(self):
        response = self.post(PRIMARY_URL, {'petanque_draw_id': 'draw-1'}, **AUTH)

        self.assertEqual(response.status_code, 400)

    def test_invalid_json_rejected(self):
        response = self.post(PRIMARY_URL, 'not json', **AUTH)

        self.assertEqual(response.status_code, 400)

    def test_unknown_tournament_returns_404(self):
        response = self.post(
            PRIMARY_URL, {'tournament_id': 999999, 'petanque_draw_id': 'draw-1'}, **AUTH,
        )

        self.assertEqual(response.status_code, 404)

    def test_no_op_write_is_not_audited(self):
        body = {'tournament_id': self.tournament.pk, 'meta': draw_payload(), 'petanque_draw_id': 'd'}
        self.post(PRIMARY_URL, body, **AUTH)
        LogEntry.objects.all().delete()

        self.post(PRIMARY_URL, body, **AUTH)

        self.assertFalse(LogEntry.objects.exists())


class TournamentPageIsReadOnlyForDrawWritesTests(TestCase):
    """The tournament page no longer accepts draw writes of any kind."""

    def setUp(self):
        self.tournament = Tournament.objects.create(
            name='Page Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 7, 1),
            format='swiko',
        )
        self.url = reverse('tournament', kwargs={'id': self.tournament.pk})

    def test_page_get_still_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    @override_settings(API_PASSWORD=API_PASSWORD)
    def test_meta_post_to_page_is_ignored_even_with_api_password(self):
        """A `meta` field is now just an unknown form field: never written."""
        response = self.client.post(self.url, {'meta': json.dumps(draw_payload())}, **AUTH)

        self.tournament.refresh_from_db()
        self.assertIsNone(self.tournament.meta)
        # The page renders instead of answering as a JSON API.
        self.assertIn('text/html', response['Content-Type'])

    def test_page_post_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(self.url, {'tournament_detail_notes_content': 'notes'})

        self.assertEqual(response.status_code, 403)
