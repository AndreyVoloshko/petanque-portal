import json
from datetime import date

from django.contrib.admin.models import LogEntry
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from federation.audit import (
    SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME,
    extract_changed_field_values,
)
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

    # -- audit: API writes are attributed to the system draw user --

    def test_api_meta_write_is_audited_under_system_draw_user(self):
        response = self.client.post(self.url, {'meta': draw_tool_payload()}, **AUTH)

        self.assertEqual(response.status_code, 200)
        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user.username, SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME)
        self.assertEqual(log_entry.object_id, str(self.tournament.pk))

    def test_no_op_meta_write_is_not_audited(self):
        payload = draw_tool_payload()
        self.client.post(self.url, {'meta': payload}, **AUTH)
        LogEntry.objects.all().delete()

        self.client.post(self.url, {'meta': payload}, **AUTH)

        self.assertFalse(LogEntry.objects.exists())


@override_settings(API_PASSWORD=API_PASSWORD)
class TournamentDrawIdEndpointTests(TestCase):
    def setUp(self):
        self.tournament = Tournament.objects.create(
            name='Draw Id Cup',
            category='open',
            place='Kyiv',
            start_date=date(2026, 7, 1),
            format='swiko',
        )
        self.url = reverse('tournament_draw_id')

    def post(self, body, **kwargs):
        return self.client.post(
            self.url, json.dumps(body), content_type='application/json', **kwargs,
        )

    def refreshed_draw_id(self):
        self.tournament.refresh_from_db()
        return self.tournament.petanque_draw_id

    # -- default --

    def test_petanque_draw_id_is_blank_by_default(self):
        self.assertEqual(self.tournament.petanque_draw_id, '')

    # -- happy path --

    def test_draw_id_is_set_with_api_password(self):
        response = self.post(
            {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-abc-123'},
            **AUTH,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'petanque_draw_id': 'draw-abc-123'})
        self.assertEqual(self.refreshed_draw_id(), 'draw-abc-123')

    def test_draw_id_can_be_cleared_with_empty_string(self):
        self.tournament.petanque_draw_id = 'draw-abc-123'
        self.tournament.save()

        response = self.post(
            {'tournament_id': self.tournament.pk, 'petanque_draw_id': ''}, **AUTH,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.refreshed_draw_id(), '')

    def test_draw_id_change_is_audited_under_system_draw_user(self):
        self.post(
            {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-abc-123'},
            **AUTH,
        )

        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user.username, SYSTEM_AUDIT_TOURNAMENT_DRAW_USERNAME)
        values = extract_changed_field_values(log_entry.change_message)
        self.assertEqual(values['petanque_draw_id'], {'old': '', 'new': 'draw-abc-123'})

    def test_no_op_draw_id_write_is_not_audited(self):
        self.tournament.petanque_draw_id = 'draw-abc-123'
        self.tournament.save()

        self.post(
            {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-abc-123'},
            **AUTH,
        )

        self.assertFalse(LogEntry.objects.exists())

    # -- auth --

    def test_draw_id_rejected_without_api_password(self):
        response = self.post(
            {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-abc-123'},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.refreshed_draw_id(), '')

    def test_draw_id_rejected_with_wrong_api_password(self):
        response = self.post(
            {'tournament_id': self.tournament.pk, 'petanque_draw_id': 'draw-abc-123'},
            headers={'authorization': 'wrong-password'},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.refreshed_draw_id(), '')

    # -- validation --

    def test_invalid_json_body_rejected(self):
        response = self.client.post(
            self.url, 'not json', content_type='application/json', **AUTH,
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_fields_rejected(self):
        for body in (
            {'petanque_draw_id': 'x'},
            {'tournament_id': self.tournament.pk},
        ):
            with self.subTest(body=body):
                response = self.post(body, **AUTH)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.refreshed_draw_id(), '')

    def test_non_string_draw_id_rejected(self):
        response = self.post(
            {'tournament_id': self.tournament.pk, 'petanque_draw_id': 123}, **AUTH,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.refreshed_draw_id(), '')

    def test_unknown_tournament_returns_404(self):
        response = self.post(
            {'tournament_id': 999999, 'petanque_draw_id': 'draw-abc-123'}, **AUTH,
        )

        self.assertEqual(response.status_code, 404)

    def test_get_not_allowed(self):
        response = self.client.get(self.url, **AUTH)

        self.assertEqual(response.status_code, 405)


class TournamentDrawIdAdminTests(TestCase):
    def test_draw_id_is_not_editable_in_admin(self):
        from django.contrib import admin as django_admin

        tournament_admin = django_admin.site._registry[Tournament]
        self.assertIn('petanque_draw_id', tournament_admin.get_readonly_fields(None))
