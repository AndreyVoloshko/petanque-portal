import json
from datetime import date

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from federation.models.tournament import Tournament

API_PASSWORD = 'test-api-password'
AUTH = {'headers': {'authorization': API_PASSWORD}}


def draw_tool_payload(**overrides):
    """A meta payload shaped like what the external draw tool sends.

    Mirrors the invariant observed across all real payloads: a JSON object
    that always contains "games" and "teams" keys (other keys vary by
    tool version and tournament format).
    """
    payload = {
        'name': 'Meta Cup. Triplets',
        'portalIdTournament': 1,
        'system': 'swiss',
        'roundIsActive': True,
        'tournamentIsFinished': False,
        'useRating': True,
        'isPlayOff': False,
        'playoff': [],
        'ranking': [],
        'teams': [{'name': 'PLAYER One'}, {'name': 'PLAYER Two'}],
        'games': [[{
            'team_1': 'PLAYER One', 'team_1_score': 13,
            'team_2': 'PLAYER Two', 'team_2_score': 7,
        }]],
    }
    payload.update(overrides)
    return json.dumps(payload)


@override_settings(API_PASSWORD=API_PASSWORD)
class TournamentMetaEndpointTests(TestCase):
    def setUp(self):
        self.tournament = Tournament.objects.create(
            name='Meta Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 7, 1),
            format='swiko',
        )
        self.url = reverse('tournament', kwargs={'id': self.tournament.pk})

    def refreshed_meta(self):
        self.tournament.refresh_from_db()
        return self.tournament.meta

    # -- external draw tool compatibility (API password, no session/CSRF) --

    def test_draw_tool_payload_saved_with_api_password(self):
        payload = draw_tool_payload()
        response = self.client.post(self.url, {'meta': payload}, **AUTH)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertEqual(self.refreshed_meta(), payload)

    def test_draw_tool_payload_accepted_without_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        payload = draw_tool_payload()
        response = csrf_client.post(self.url, {'meta': payload}, **AUTH)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.refreshed_meta(), payload)

    # -- hardening: same API password mechanism as submit_tournament_results --

    def test_meta_rejected_without_api_password(self):
        response = self.client.post(self.url, {'meta': draw_tool_payload()})

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.refreshed_meta())

    def test_meta_rejected_with_wrong_api_password(self):
        response = self.client.post(
            self.url, {'meta': draw_tool_payload()},
            headers={'authorization': 'wrong-password'},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.refreshed_meta())

    @override_settings(API_PASSWORD=None)
    def test_meta_rejected_when_api_password_unconfigured(self):
        response = self.client.post(self.url, {'meta': draw_tool_payload()}, **AUTH)

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.refreshed_meta())

    # -- hardening: payload validation --

    def test_non_json_meta_rejected(self):
        response = self.client.post(
            self.url, {'meta': '<script>alert(1)</script>'}, **AUTH,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.refreshed_meta())

    def test_json_without_draw_shape_rejected(self):
        for payload in ('"just a string"', '[]', '{"foo": "bar"}', '{"games": []}'):
            with self.subTest(payload=payload):
                response = self.client.post(self.url, {'meta': payload}, **AUTH)

                self.assertEqual(response.status_code, 400)
                self.assertIsNone(self.refreshed_meta())

    def test_oversized_meta_rejected(self):
        oversized = draw_tool_payload(padding='x' * (300 * 1024))
        response = self.client.post(self.url, {'meta': oversized}, **AUTH)

        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.refreshed_meta())

    # -- hardening: state gate --

    def test_meta_rejected_after_tournament_processing_finished(self):
        self.tournament.is_processing_finished = True
        self.tournament.save()

        response = self.client.post(self.url, {'meta': draw_tool_payload()}, **AUTH)

        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.refreshed_meta())

    # -- hardening: CSRF restored for every other POST branch --

    def test_non_meta_post_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            self.url, {'tournament_detail_notes_content': 'notes'},
        )

        self.assertEqual(response.status_code, 403)
