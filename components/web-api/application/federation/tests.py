from datetime import date

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.middleware.locale import LocaleMiddleware
from django.test import RequestFactory
from django.test import TestCase
from django.utils.translation import get_language

from federation.forms.registration_player_form import RegistrationPlayerForm
from federation.middleware import InitialLanguageMiddleware
from federation.models.email_confirmation import EmailConfirmation
from federation.models.player import Player
from federation.models.team import PlayerTeamMembership, Team
from federation.views.login import _needs_email_prompt


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
