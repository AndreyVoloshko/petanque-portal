import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.forms import modelform_factory
from django.test import RequestFactory, TestCase, override_settings
from django.utils.translation import gettext as _, override

from federation.audit import (
    AUDIT_CHANGE_MESSAGE_VALUES_KEY,
    PLAYER_CHANGE_FIELD_AVATAR,
    PLAYER_CHANGE_FIELD_CURRENT_CLUB,
    PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE,
    PLAYER_CHANGE_FIELD_PASSWORD,
    PLAYER_CHANGE_FIELD_SPORT_TITLE,
    PLAYER_CHANGE_FILTER_CLUB,
    PLAYER_CHANGE_IGNORED_FIELDS,
    PLAYER_CHANGE_MESSAGE_CHANGED_KEY,
    PLAYER_CHANGE_MESSAGE_FIELDS_KEY,
    SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME,
    TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,
    capture_player_change_values,
    extract_changed_field_values,
    format_player_change_fields,
    get_player_change_filter_choices,
    get_revert_source_log_entry_id,
    log_model_change,
    log_player_change,
    record_model_change,
)
from federation.admin_actions import player as player_admin_actions
from federation.models.club import Club
from federation.models.document import Document, DocumentCategory
from federation.models.player import Player
from federation.models.team import PlayerTeamMembership, Team
from federation.models.tournament import TeamTournamentMembership, Tournament


class PlayerProfileAuditLogTests(TestCase):
    def get_changed_fields(self, log_entry):
        change_message = json.loads(log_entry.change_message)[0]
        return change_message[PLAYER_CHANGE_MESSAGE_CHANGED_KEY][PLAYER_CHANGE_MESSAGE_FIELDS_KEY]

    def create_player(self, username='profile-log-player', name='Profile', surname='Player', club_name='Old Club'):
        user = User.objects.create_user(
            username=username,
            email='{}@example.com'.format(username),
            password='OldPass123!',
        )
        club = Club.objects.create(
            name=club_name,
            short_name=username[:20].upper(),
            address='Old address',
        )
        player = Player.objects.create(
            user=user,
            name=name,
            surname=surname,
            birth_date=date(1990, 1, 1),
            current_club=club,
            country='UA',
            gender='M',
        )
        return user, player

    def test_profile_club_change_creates_player_log_entry(self):
        user, player = self.create_player()
        new_club = Club.objects.create(
            name='New Club',
            short_name='NEW',
            address='New address',
        )
        self.client.login(username=user.username, password='OldPass123!')

        response = self.client.post('/profile/', {
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': str(new_club.pk),
            'country': 'UA',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': user.email,
        })

        self.assertEqual(response.status_code, 200)
        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user, user)
        self.assertEqual(log_entry.object_id, str(player.pk))
        self.assertIn(PLAYER_CHANGE_FIELD_CURRENT_CLUB, self.get_changed_fields(log_entry))

        with override('en'):
            self.assertEqual(format_player_change_fields(log_entry.change_message), 'Club')

    def test_profile_country_change_creates_player_log_entry(self):
        user, player = self.create_player()
        self.client.login(username=user.username, password='OldPass123!')

        response = self.client.post('/profile/', {
            'name': player.name,
            'surname': player.surname,
            'second_name': '',
            'birth_date': '1990-01-01',
            'current_club': str(player.current_club_id),
            'country': 'FR',
            'gender': player.gender,
            'facebook': '',
            'twitter': '',
            'instagram': '',
            'website': '',
            'email': user.email,
        })

        self.assertEqual(response.status_code, 200)
        player.refresh_from_db()
        self.assertEqual(player.country.code, 'FR')
        values = extract_changed_field_values(LogEntry.objects.get().change_message)
        self.assertEqual(values['country'], {'old': 'UA', 'new': 'FR'})

    def test_password_change_creates_player_log_entry(self):
        user, player = self.create_player()
        self.client.login(username=user.username, password='OldPass123!')

        response = self.client.post('/profile/', {
            'old_password': 'OldPass123!',
            'new_password1': 'NewPass123!',
            'new_password2': 'NewPass123!',
        })

        self.assertEqual(response.status_code, 200)
        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user, user)
        self.assertEqual(log_entry.object_id, str(player.pk))
        self.assertIn(PLAYER_CHANGE_FIELD_PASSWORD, self.get_changed_fields(log_entry))
        self.assertTrue(self.client.login(username=user.username, password='NewPass123!'))

    def test_player_admin_change_message_uses_stable_field_keys(self):
        _user, player = self.create_player()
        new_club = Club.objects.create(
            name='Admin New Club',
            short_name='ADMINNEW',
            address='New address',
        )
        form_class = modelform_factory(Player, fields=(PLAYER_CHANGE_FIELD_CURRENT_CLUB,))
        form = form_class(data={PLAYER_CHANGE_FIELD_CURRENT_CLUB: str(new_club.pk)}, instance=player)
        self.assertTrue(form.is_valid())

        player_admin = admin.site._registry[Player]
        request = RequestFactory().post('/admin/federation/player/{}/change/'.format(player.pk))
        change_message = player_admin.construct_change_message(request, form, [], add=False)

        changed_fields = change_message[0][PLAYER_CHANGE_MESSAGE_CHANGED_KEY][
            PLAYER_CHANGE_MESSAGE_FIELDS_KEY
        ]
        self.assertEqual(changed_fields, [PLAYER_CHANGE_FIELD_CURRENT_CLUB])

    def test_admin_club_filter_includes_club_changes_only(self):
        admin_user = User.objects.create_superuser(
            username='audit-admin',
            email='audit-admin@example.com',
            password='AdminPass123!',
        )
        _club_user, club_player = self.create_player(
            username='club-log-player',
            name='Club',
            surname='Changed',
            club_name='Club Log Old Club',
        )
        _avatar_user, avatar_player = self.create_player(
            username='avatar-log-player',
            name='Avatar',
            surname='Changed',
            club_name='Avatar Log Old Club',
        )
        log_player_change(admin_user, club_player, [PLAYER_CHANGE_FIELD_CURRENT_CLUB])
        log_player_change(admin_user, avatar_player, [PLAYER_CHANGE_FIELD_AVATAR])
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/', {
            'changed_field': PLAYER_CHANGE_FILTER_CLUB,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, club_player.get_name())
        self.assertNotContains(response, avatar_player.get_name())

    def test_admin_sports_title_filter_includes_sports_title_changes_only(self):
        admin_user = User.objects.create_superuser(
            username='sport-title-audit-admin',
            email='sport-title-audit-admin@example.com',
            password='AdminPass123!',
        )
        _sport_title_user, sport_title_player = self.create_player(
            username='sport-title-log-player',
            name='Title',
            surname='Changed',
            club_name='Sport Title Log Old Club',
        )
        _avatar_user, avatar_player = self.create_player(
            username='sport-title-avatar-player',
            name='Avatar',
            surname='Changed',
            club_name='Sport Title Avatar Log Old Club',
        )
        log_player_change(admin_user, sport_title_player, [PLAYER_CHANGE_FIELD_SPORT_TITLE])
        log_player_change(admin_user, avatar_player, [PLAYER_CHANGE_FIELD_AVATAR])
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/', {
            'changed_field': PLAYER_CHANGE_FIELD_SPORT_TITLE,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, sport_title_player.get_name())
        self.assertNotContains(response, avatar_player.get_name())

    def test_document_name_filter_matches_document_logs(self):
        admin_user = User.objects.create_superuser(
            username='document-filter-audit-admin',
            email='document-filter-audit-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player(
            username='document-filter-player',
            name='Player',
            surname='Changed',
            club_name='Document Filter Club',
        )
        category = DocumentCategory.objects.create(
            code='document-filter-category',
            name='Document filter category',
        )
        document = Document.objects.create(
            name='Document Filter Target',
            file='documents/test.pdf',
            category=category,
            is_active=True,
        )
        log_player_change(admin_user, player, [PLAYER_CHANGE_FIELD_AVATAR])
        log_model_change(admin_user, document, ['name'])
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/', {
            'content_type__id__exact': ContentType.objects.get_for_model(Document).pk,
            'changed_field': 'name',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, document.name)
        self.assertNotContains(response, player.get_name())

    def test_tournament_team_places_filter_matches_tournament_logs(self):
        admin_user = User.objects.create_superuser(
            username='tournament-filter-audit-admin',
            email='tournament-filter-audit-admin@example.com',
            password='AdminPass123!',
        )
        tournament = Tournament.objects.create(
            name='Tournament Filter Target',
            category='open',
            place='Kyiv',
            country='UA',
            start_date=date.today(),
            end_date=date.today(),
            number_of_players_in_team_min=1,
            number_of_players_in_team_max=1,
            format='swiss',
        )
        log_model_change(admin_user, tournament, [TOURNAMENT_CHANGE_FIELD_TEAM_PLACES])
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/', {
            'content_type__id__exact': ContentType.objects.get_for_model(Tournament).pk,
            'changed_field': TOURNAMENT_CHANGE_FIELD_TEAM_PLACES,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, tournament.name)

    def test_derived_rating_fields_are_not_filter_choices(self):
        filter_choices = dict(get_player_change_filter_choices())

        for field in PLAYER_CHANGE_IGNORED_FIELDS:
            self.assertNotIn(field, filter_choices)

    def test_rating_only_player_admin_change_is_not_logged(self):
        admin_user = User.objects.create_superuser(
            username='rating-form-audit-admin',
            email='rating-form-audit-admin@example.com',
            password='AdminPass123!',
        )
        _user, player = self.create_player()
        form_class = modelform_factory(Player, fields=('current_rating',))
        form = form_class(data={'current_rating': '12.0000'}, instance=player)
        self.assertTrue(form.is_valid())

        player_admin = admin.site._registry[Player]
        request = RequestFactory().post('/admin/federation/player/{}/change/'.format(player.pk))
        request.user = admin_user
        change_message = player_admin.construct_change_message(request, form, [], add=False)
        player_admin.log_change(request, player, change_message)

        self.assertEqual(change_message, [])
        self.assertFalse(LogEntry.objects.exists())

    def test_rating_admin_action_changes_are_not_logged(self):
        admin_user = User.objects.create_superuser(
            username='rating-action-audit-admin',
            email='rating-action-audit-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        player.current_rating = Decimal('12.0000')
        player.current_rating_b = Decimal('5.0000')
        player.current_rating_inclusive = Decimal('2.0000')
        player.current_rating_liga = Decimal('1.0000')
        player.save()
        request = RequestFactory().post('/admin/federation/player/', {'post': 'yes'})
        request.user = admin_user

        with patch.object(player_admin_actions.messages, 'success'), patch.object(
            player_admin_actions.messages,
            'error',
        ):
            player_admin_actions.erase_ratings(None, request, Player.objects.filter(pk=player.pk))

        self.assertFalse(LogEntry.objects.exists())

    def test_player_admin_action_changes_are_logged(self):
        admin_user = User.objects.create_superuser(
            username='licence-audit-admin',
            email='licence-audit-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        player.is_licence_active = False
        player.save()
        request = RequestFactory().post('/admin/federation/player/', {'post': 'yes'})
        request.user = admin_user

        with patch.object(player_admin_actions.messages, 'success'), patch.object(
            player_admin_actions.messages,
            'error',
        ):
            player_admin_actions.activate_licence(None, request, Player.objects.filter(pk=player.pk))

        log_entry = LogEntry.objects.get()
        self.assertEqual(log_entry.user, admin_user)
        self.assertEqual(log_entry.object_id, str(player.pk))
        self.assertIn(PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE, self.get_changed_fields(log_entry))
        field_values = extract_changed_field_values(log_entry.change_message)
        self.assertFalse(field_values[PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE]['old'])
        self.assertTrue(field_values[PLAYER_CHANGE_FIELD_IS_LICENCE_ACTIVE]['new'])

    def test_no_op_player_admin_action_is_not_logged(self):
        admin_user = User.objects.create_superuser(
            username='licence-no-op-audit-admin',
            email='licence-no-op-audit-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        player.is_licence_active = True
        player.save()
        request = RequestFactory().post('/admin/federation/player/', {'post': 'yes'})
        request.user = admin_user

        with patch.object(player_admin_actions.messages, 'success'), patch.object(
            player_admin_actions.messages,
            'error',
        ):
            player_admin_actions.activate_licence(None, request, Player.objects.filter(pk=player.pk))

        self.assertFalse(LogEntry.objects.exists())

    def test_record_model_change_captures_values_and_skips_no_op(self):
        admin_user = User.objects.create_superuser(
            username='generic-record-audit-admin',
            email='generic-record-audit-admin@example.com',
            password='AdminPass123!',
        )
        category = DocumentCategory.objects.create(code='no-op-document-category', name='No-op documents')
        document = Document.objects.create(
            name='Original document',
            file='documents/test.pdf',
            category=category,
            is_active=True,
        )
        before_document = Document.objects.get(pk=document.pk)
        document.name = 'Updated document'
        document.save()

        log_entry = record_model_change(admin_user, before_document, document)

        values = extract_changed_field_values(log_entry.change_message)
        self.assertEqual(values['name'], {'old': 'Original document', 'new': 'Updated document'})
        self.assertIsNone(record_model_change(admin_user, document, document))
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_no_op_tournament_meta_and_notes_are_not_logged(self):
        admin_user = User.objects.create_superuser(
            username='tournament-no-op-audit-admin',
            email='tournament-no-op-audit-admin@example.com',
            password='AdminPass123!',
        )
        tournament = Tournament.objects.create(
            name='No-op Audit Tournament',
            category='open',
            place='Kyiv',
            country='UA',
            start_date=date.today(),
            number_of_players_in_team_min=1,
            number_of_players_in_team_max=1,
            format='swiss',
            meta='{"games": [], "teams": [], "round": 1}',
            final_notes='Existing notes',
        )
        self.client.force_login(admin_user)

        meta_response = self.client.post('/tournament/{}'.format(tournament.pk), {'meta': tournament.meta})
        notes_response = self.client.post(
            '/tournament/{}'.format(tournament.pk),
            {'tournament_notes_content': tournament.final_notes},
        )

        self.assertEqual(meta_response.status_code, 200)
        self.assertEqual(notes_response.status_code, 302)
        self.assertFalse(LogEntry.objects.exists())

    def test_log_entry_detail_decodes_change_message_fields(self):
        admin_user = User.objects.create_superuser(
            username='detail-audit-admin',
            email='detail-audit-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        LogEntry.objects.log_actions(
            user_id=admin_user.pk,
            queryset=[player],
            action_flag=CHANGE,
            change_message=[{
                'changed': {
                    'fields': ['Дата народження (дд.мм.рррр)', 'Middle name'],
                },
            }],
            single_object=True,
        )
        log_entry = LogEntry.objects.get()
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/{}/change/'.format(log_entry.pk))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Змінені поля')
        self.assertNotContains(response, 'Changed fields')
        self.assertContains(response, 'Дата народження')
        self.assertContains(response, 'По батькові')
        self.assertNotContains(response, 'Middle name')
        self.assertNotContains(response, '\\u0414')

    def test_admin_audit_filter_headings_are_localized(self):
        admin_user = User.objects.create_superuser(
            username='filter-heading-audit-admin',
            email='filter-heading-audit-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player(username='filter-heading-player')
        log_player_change(admin_user, player, [PLAYER_CHANGE_FIELD_AVATAR])
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Показати кількість')
        self.assertContains(response, 'За типом вмісту')
        self.assertContains(response, 'За зміненим полем')
        self.assertContains(response, 'За ким змінено')
        self.assertContains(response, 'За дією')
        self.assertContains(response, 'За часом дії')

        response = self.client.get('/admin/admin/logentry/', {'_facets': 'True'})
        self.assertContains(response, 'Сховати кількість')


class AuditLogRevertTests(TestCase):
    def create_player(self, username='audit-player', club_name='Audit Club'):
        user = User.objects.create_user(
            username=username,
            email='{}@example.com'.format(username),
            password='OldPass123!',
        )
        club = Club.objects.create(
            name=club_name,
            short_name=username[:20].upper(),
            address='Address',
        )
        player = Player.objects.create(
            user=user,
            name='Audit',
            surname='Player',
            birth_date=date(1990, 1, 1),
            current_club=club,
            country='UA',
            gender='M',
        )
        return user, player

    def test_document_admin_change_message_stores_revert_values(self):
        category = DocumentCategory.objects.create(code='audit-document-category', name='Audit documents')
        document = Document.objects.create(
            name='Old document',
            file='documents/test.pdf',
            category=category,
            is_active=True,
        )
        form_class = modelform_factory(Document, fields=('name',))
        form = form_class(data={'name': 'New document'}, instance=document)
        self.assertTrue(form.is_valid())

        document_admin = admin.site._registry[Document]
        request = RequestFactory().post('/admin/federation/document/{}/change/'.format(document.pk))
        request.user = User.objects.create_superuser(
            username='document-audit-admin',
            email='document-audit-admin@example.com',
            password='AdminPass123!',
        )
        updated_document = form.save(commit=False)
        document_admin.save_model(request, updated_document, form, change=True)
        change_message = document_admin.construct_change_message(request, form, [], add=False)

        values = change_message[0][PLAYER_CHANGE_MESSAGE_CHANGED_KEY][AUDIT_CHANGE_MESSAGE_VALUES_KEY]
        self.assertEqual(values['name']['old'], 'Old document')
        self.assertEqual(values['name']['new'], 'New document')

    def test_reverting_player_change_restores_previous_values_and_creates_revert_log(self):
        admin_user = User.objects.create_superuser(
            username='player-revert-admin',
            email='player-revert-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        new_club = Club.objects.create(name='New Club', short_name='NEWCLUB', address='Address')
        player_before = Player.objects.select_related('user').get(pk=player.pk)
        player.current_club = new_club
        player.facebook = 'https://facebook.example/new'
        player.save()

        field_values = capture_player_change_values(
            player_before,
            player,
            [PLAYER_CHANGE_FIELD_CURRENT_CLUB, 'facebook'],
        )
        original_log_entry = log_player_change(
            admin_user,
            player,
            [PLAYER_CHANGE_FIELD_CURRENT_CLUB, 'facebook'],
            field_values=field_values,
        )
        self.client.force_login(admin_user)

        response = self.client.post('/admin/admin/logentry/{}/revert/'.format(original_log_entry.pk))

        self.assertEqual(response.status_code, 302)
        player.refresh_from_db()
        self.assertEqual(player.current_club_id, player_before.current_club_id)
        self.assertEqual(player.facebook, player_before.facebook)
        self.assertEqual(LogEntry.objects.count(), 2)

        revert_log_entry = LogEntry.objects.exclude(pk=original_log_entry.pk).get()
        self.assertEqual(get_revert_source_log_entry_id(revert_log_entry.change_message), original_log_entry.pk)
        revert_values = extract_changed_field_values(revert_log_entry.change_message)
        self.assertEqual(
            revert_values[PLAYER_CHANGE_FIELD_CURRENT_CLUB]['new'],
            field_values[PLAYER_CHANGE_FIELD_CURRENT_CLUB]['old'],
        )

    def test_player_email_revert_requires_change_user_permission(self):
        staff_user = User.objects.create_user(
            username='restricted-player-revert-admin',
            email='restricted-player-revert-admin@example.com',
            password='AdminPass123!',
            is_staff=True,
        )
        staff_user.user_permissions.add(
            Permission.objects.get(content_type__app_label='admin', codename='view_logentry'),
            Permission.objects.get(content_type__app_label='federation', codename='change_player'),
        )
        _player_user, player = self.create_player()
        player_before = Player.objects.select_related('user').get(pk=player.pk)
        player.user.email = 'new-player-email@example.com'
        player.user.save()
        field_values = capture_player_change_values(player_before, player, ['email'])
        original_log_entry = log_player_change(
            staff_user,
            player,
            ['email'],
            field_values=field_values,
        )
        self.client.force_login(staff_user)

        response = self.client.post('/admin/admin/logentry/{}/revert/'.format(original_log_entry.pk))

        self.assertEqual(response.status_code, 302)
        player.user.refresh_from_db()
        self.assertEqual(player.user.email, 'new-player-email@example.com')
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_stale_player_change_is_not_reverted(self):
        admin_user = User.objects.create_superuser(
            username='stale-player-revert-admin',
            email='stale-player-revert-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        player_before = Player.objects.select_related('user').get(pk=player.pk)
        player.facebook = 'https://facebook.example/audited'
        player.save()
        field_values = capture_player_change_values(player_before, player, ['facebook'])
        original_log_entry = log_player_change(
            admin_user,
            player,
            ['facebook'],
            field_values=field_values,
        )
        player.facebook = 'https://facebook.example/newer'
        player.save()
        self.client.force_login(admin_user)

        response = self.client.post('/admin/admin/logentry/{}/revert/'.format(original_log_entry.pk))

        self.assertEqual(response.status_code, 302)
        player.refresh_from_db()
        self.assertEqual(player.facebook, 'https://facebook.example/newer')
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_revert_revalidation_failure_returns_to_log_entry(self):
        admin_user = User.objects.create_superuser(
            username='concurrent-player-revert-admin',
            email='concurrent-player-revert-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        player_before = Player.objects.select_related('user').get(pk=player.pk)
        player.facebook = 'https://facebook.example/audited'
        player.save()
        field_values = capture_player_change_values(player_before, player, ['facebook'])
        original_log_entry = log_player_change(
            admin_user,
            player,
            ['facebook'],
            field_values=field_values,
        )
        self.client.force_login(admin_user)

        with patch(
            'federation.player_change_log_admin.revert_log_entry',
            side_effect=ValueError('The object changed during revert.'),
        ):
            response = self.client.post('/admin/admin/logentry/{}/revert/'.format(original_log_entry.pk))

        self.assertRedirects(
            response,
            '/admin/admin/logentry/{}/change/'.format(original_log_entry.pk),
        )
        self.assertEqual(LogEntry.objects.count(), 1)

    def test_old_player_log_without_values_shows_revert_unavailable_message(self):
        admin_user = User.objects.create_superuser(
            username='player-old-log-admin',
            email='player-old-log-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player()
        LogEntry.objects.log_actions(
            user_id=admin_user.pk,
            queryset=[player],
            action_flag=CHANGE,
            change_message=[{
                'changed': {
                    'fields': ['Middle name'],
                },
            }],
            single_object=True,
        )
        log_entry = LogEntry.objects.get()
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/{}/change/'.format(log_entry.pk))

        self.assertEqual(response.status_code, 200)
        with override('uk'):
            self.assertContains(
                response,
                _('This log entry does not contain enough data to revert the change.'),
            )

    def test_old_document_log_uses_current_field_label_on_detail_page(self):
        admin_user = User.objects.create_superuser(
            username='document-old-log-admin',
            email='document-old-log-admin@example.com',
            password='AdminPass123!',
        )
        category = DocumentCategory.objects.create(
            code='old-document-log-category',
            name='Old document log category',
        )
        document = Document.objects.create(
            name='Legacy document',
            file='documents/test.pdf',
            category=category,
            is_active=True,
        )
        LogEntry.objects.log_actions(
            user_id=admin_user.pk,
            queryset=[document],
            action_flag=CHANGE,
            change_message=[{
                'changed': {
                    'fields': ['Name'],
                },
            }],
            single_object=True,
        )
        log_entry = LogEntry.objects.get()
        self.client.force_login(admin_user)

        response = self.client.get('/admin/admin/logentry/{}/change/'.format(log_entry.pk))

        self.assertEqual(response.status_code, 200)
        with override('uk'):
            self.assertContains(response, _('Name'))

    @override_settings(API_PASSWORD='test-api-password')
    def test_tournament_results_api_logs_and_reverts_team_places(self):
        admin_user = User.objects.create_superuser(
            username='tournament-revert-admin',
            email='tournament-revert-admin@example.com',
            password='AdminPass123!',
        )
        _player_user, player = self.create_player(username='tournament-player', club_name='Tournament Club')
        tournament = Tournament.objects.create(
            name='Audit Tournament',
            category='open',
            place='Kyiv',
            country='UA',
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() - timedelta(days=1),
            number_of_players_in_team_min=1,
            number_of_players_in_team_max=1,
            format='swiss',
        )
        team = Team.objects.create(name='Audit Team')
        PlayerTeamMembership.objects.create(player=player, team=team, is_capitan=True)
        membership = TeamTournamentMembership.objects.create(tournament=tournament, team=team, place_min=0, place_max=0)

        response = self.client.post(
            '/api/tournament/results/',
            data=json.dumps({
                'tournament_id': tournament.pk,
                'teams': [{
                    'team_id': team.pk,
                    'place_min': 1,
                    'place_max': 1,
                }],
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='test-api-password',
        )

        self.assertEqual(response.status_code, 200)
        membership.refresh_from_db()
        self.assertEqual(membership.place_min, 1)
        self.assertEqual(membership.place_max, 1)

        api_user = User.objects.get(username=SYSTEM_AUDIT_TOURNAMENT_RESULTS_USERNAME)
        log_entry = LogEntry.objects.get(user=api_user, object_id=str(tournament.pk))
        values = extract_changed_field_values(log_entry.change_message)
        self.assertIn(TOURNAMENT_CHANGE_FIELD_TEAM_PLACES, values)

        self.client.force_login(admin_user)
        revert_response = self.client.post('/admin/admin/logentry/{}/revert/'.format(log_entry.pk))

        self.assertEqual(revert_response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(membership.place_min, 0)
        self.assertEqual(membership.place_max, 0)
        self.assertEqual(LogEntry.objects.filter(object_id=str(tournament.pk)).count(), 2)

    @override_settings(API_PASSWORD='test-api-password')
    def test_tournament_results_api_rejects_without_partial_updates(self):
        _player_user, player = self.create_player(
            username='partial-results-player',
            club_name='Partial Results Club',
        )
        tournament = Tournament.objects.create(
            name='Partial Results Tournament',
            category='open',
            place='Kyiv',
            country='UA',
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() - timedelta(days=1),
            number_of_players_in_team_min=1,
            number_of_players_in_team_max=1,
            format='swiss',
        )
        registered_team = Team.objects.create(name='Registered Team')
        PlayerTeamMembership.objects.create(player=player, team=registered_team, is_capitan=True)
        membership = TeamTournamentMembership.objects.create(
            tournament=tournament,
            team=registered_team,
            place_min=4,
            place_max=4,
        )
        unregistered_team = Team.objects.create(name='Unregistered Team')

        response = self.client.post(
            '/api/tournament/results/',
            data=json.dumps({
                'tournament_id': tournament.pk,
                'teams': [
                    {
                        'team_id': registered_team.pk,
                        'place_min': 1,
                        'place_max': 1,
                    },
                    {
                        'team_id': unregistered_team.pk,
                        'place_min': 2,
                        'place_max': 2,
                    },
                ],
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION='test-api-password',
        )

        self.assertEqual(response.status_code, 400)
        membership.refresh_from_db()
        self.assertEqual(membership.place_min, 4)
        self.assertEqual(membership.place_max, 4)
        self.assertFalse(LogEntry.objects.exists())
