from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from federation.models.city import City
from federation.models.club import Club
from federation.models.department import Department, PlayerDepartmentMembership
from federation.models.player import Player
from federation.views.api import clubs_list, departments_list
from federation.views.clubs import DEFAULT_CLUBS_PAGE_SIZE


def create_player(username, name='Олена', surname='Шевченко', **fields):
    return Player.objects.create(
        user=User.objects.create_user(username=username),
        name=name,
        surname=surname,
        birth_date=date(1990, 1, 1),
        gender='F',
        **fields,
    )


class DirectoryPresentationTests(SimpleTestCase):
    def test_directories_use_shared_card_and_route_assets(self):
        route_groups = {
            'departments': 'department_groups',
            'arbiters': 'player_choice_groups',
            'coaches': 'player_choice_groups',
            'national_teams': 'national_team_groups',
            'sport_titles': 'player_choice_groups',
        }
        player = Player(pk=42, name='Олена', surname='Шевченко',
                        birth_date=date(1990, 1, 1), gender='F', country='UA')
        groups = [{
            'key': 'first',
            'label': 'Directory group',
            'short_label': 'A',
            'items': [{
                'player': player,
                'title_short': 'Member',
                'title_label': 'Tournament committee',
            }],
        }, {
            'key': 'second',
            'label': 'Second group',
            'short_label': 'B',
            'items': [],
        }]

        for route, groups_function in route_groups.items():
            with self.subTest(route=route):
                with patch(f'federation.views.{route}.{groups_function}', return_value=groups):
                    response = self.client.get(reverse(route))
                self.assertContains(response, '/vite/assets/directories-')
                self.assertContains(response, '/vite/assets/athlete-card-')
                self.assertNotContains(response, '/style-v2.css')
                self.assertNotContains(response, 'connect.facebook.net')
                self.assertContains(response, 'athlete-card-has-title-status')
                self.assertContains(response, 'Tournament committee')
                self.assertContains(response, 'type="button" tabindex="-1"', count=1)

    def test_footer_links_to_news_and_feedback(self):
        with patch('federation.views.departments.department_groups', return_value=[]):
            response = self.client.get(reverse('departments'))
        self.assertContains(response, 'class="portal-footer-nav"')
        self.assertContains(response, '<a href="https://petanque.org.ua/" target="_blank" rel="noopener">')
        self.assertContains(response, '<a href="https://feedback.petanque.org.ua/" target="_blank" rel="noopener">')


class DepartmentsListTests(TestCase):
    url = '/api/departments/list/'

    @classmethod
    def setUpTestData(cls):
        cls.committee = Department.objects.create(name='Суддівський комітет', order=2)
        cls.board = Department.objects.create(name='Правління ФПУ', order=1)
        cls.second_board = Department.objects.create(name='Правління ФПУ', order=1)
        Department.objects.create(name='Порожній підрозділ', order=0)
        orphaned_department = Department.objects.create(name='Без гравців', order=0)
        PlayerDepartmentMembership.objects.create(team=orphaned_department, role='Вакансія')

        club = Club.objects.create(name='Київський петанк клуб', short_name='КПК')
        cls.chair = create_player('chair', avatar='portraits/chair.png', current_club=club, licence_number='12345')
        cls.advisor = create_player('advisor')
        PlayerDepartmentMembership.objects.create(team=cls.board, player=cls.chair, role='Радниця', order=2)
        PlayerDepartmentMembership.objects.create(team=cls.board, player=cls.advisor, role='Секретарка', order=2)
        PlayerDepartmentMembership.objects.create(
            team=cls.board, player=cls.chair, role='Голова', description='Обрана загальними зборами', order=1,
        )
        PlayerDepartmentMembership.objects.create(
            team=cls.committee, player=cls.chair, role='Членкиня', description='Призначена правлінням',
        )
        PlayerDepartmentMembership.objects.create(team=cls.second_board, player=cls.advisor, role=' ', description=' ')
        PlayerDepartmentMembership.objects.create(team=cls.board, role='Непризначена')

    @override_settings(AWS_STORAGE_BUCKET_NAME='public-media')
    def test_anonymous_directory_matches_public_page_and_keeps_membership_roles(self):
        portrait = 'https://media.example.org/portraits/chair.png'
        with patch.object(Player._meta.get_field('avatar').storage, 'url', return_value=portrait):
            response = self.client.get(self.url)
            page = self.client.get('/departments/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(page.status_code, 200)
        data = response.json()
        self.assertEqual([body['id'] for body in data], [self.board.pk, self.second_board.pk, self.committee.pk])

        chair = {
            'name': 'ШЕВЧЕНКО Олена',
            'profile_path': f'/player/{self.chair.pk}',
            'portrait_url': portrait,
            'club_name': 'КПК',
            'role': 'Голова',
            'role_note': 'Обрана загальними зборами',
        }
        advisor = {
            'name': 'ШЕВЧЕНКО Олена',
            'profile_path': f'/player/{self.advisor.pk}',
            'portrait_url': None,
            'club_name': None,
            'role': 'Секретарка',
            'role_note': None,
        }
        self.assertEqual(data[0], {
            'id': self.board.pk, 'name': self.board.name, 'badge': 'ПФ',
            'members': [chair, dict(chair, role='Радниця', role_note=None), advisor],
        })
        self.assertEqual(data[1]['members'], [dict(advisor, role=None)])
        self.assertEqual(data[2]['members'], [dict(chair, role='Членкиня', role_note='Призначена правлінням')])

        groups = page.context['title_registry']['groups']
        self.assertEqual(
            [(f"department-{body['id']}", body['badge'], len(body['members']),
              [member['profile_path'] for member in body['members']]) for body in data],
            [(group['key'], group['short_label'], group['players_count'],
              [f"/player/{entry['player'].pk}" for entry in group['items']]) for group in groups],
        )

    @override_settings(AWS_STORAGE_BUCKET_NAME=None)
    def test_directory_prefetches_members_and_clubs(self):
        request = RequestFactory().get(self.url)
        with patch('federation.views.api.default_storage', FileSystemStorage(base_url='/media/')):
            with self.assertNumQueries(2):
                self.assertEqual(departments_list(request).status_code, 200)

    def test_directory_rejects_non_get_requests(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response['Allow'], 'GET')


class ClubsListTests(TestCase):
    url = '/api/clubs/list/'

    @classmethod
    def setUpTestData(cls):
        city = City.objects.create(name='Київ', country='UA')
        cls.ranked = Club.objects.create(
            name='Київський петанк клуб', short_name='КПК', city=city,
            address='вул. Хрещатик, 1 & 2', logo='logos/club badge.png',
        )
        cls.unlicensed = Club.objects.create(name='Club with unlicensed players', short_name='UNC', city=city)
        cls.zero = Club.objects.create(name='Club with no athletes', short_name='AAA', address=' ')
        cls.tied = Club.objects.create(name='Another club with no athletes', short_name='AAA')
        cls.hidden = Club.objects.create(name='Hidden Club', short_name='HID', is_active=False)
        Club.objects.bulk_create([
            Club(name=f'Extra Club {index}', short_name=f'Extra {index}', city=city)
            for index in range(DEFAULT_CLUBS_PAGE_SIZE)
        ])

        create_player('rated', current_club=cls.ranked, current_rating=10, is_licence_active=True, licence_number='1')
        create_player('unlicensed', current_club=cls.ranked, current_rating=10)
        create_player('inactive', current_club=cls.unlicensed, current_rating=100, licence_number='2')
        create_player('blank', current_club=cls.unlicensed, current_rating=100, is_licence_active=True, licence_number='')
        create_player('absent', current_club=cls.unlicensed, current_rating=100, is_licence_active=True)

    @override_settings(AWS_STORAGE_BUCKET_NAME=None)
    def test_anonymous_directory_matches_all_public_pages_in_ranking_order(self):
        with patch.object(Club._meta.get_field('logo').storage, 'url', return_value='/media/logos/club%20badge.png'):
            with patch('federation.views.api.default_storage', FileSystemStorage(base_url='/media/')):
                response = self.client.get(self.url, secure=True)
            first_page = self.client.get('/clubs/')
            page_obj = first_page.context['page_obj']
            self.assertTrue(page_obj.has_next())
            public_rows = list(first_page.context['clubs'])
            for number in range(2, page_obj.paginator.num_pages + 1):
                page = self.client.get('/clubs/', {'page': number})
                self.assertEqual(page.status_code, 200)
                public_rows.extend(page.context['clubs'])

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), page_obj.paginator.count)
        self.assertEqual(len({club['id'] for club in data}), len(data))
        self.assertEqual(
            [(club['id'], club['athlete_count']) for club in data],
            [(club.pk, club.players_count) for club in public_rows],
        )
        self.assertEqual([club['id'] for club in data[:4]], [
            self.ranked.pk, self.unlicensed.pk, self.zero.pk, self.tied.pk,
        ])
        self.assertNotIn(self.hidden.pk, [club['id'] for club in data])
        self.assertEqual(data[0], {
            'id': self.ranked.pk,
            'detail_path': f'/club/{self.ranked.pk}',
            'short_name': 'КПК',
            'name': 'Київський петанк клуб',
            'city_id': self.ranked.city_id,
            'city_name': 'Київ',
            'country': 'UA',
            'address': 'вул. Хрещатик, 1 & 2',
            'athlete_count': 2,
            'logo_url': 'https://testserver/media/logos/club%20badge.png',
        })
        self.assertEqual(data[1]['city_id'], data[0]['city_id'])
        self.assertEqual(data[1]['athlete_count'], 3)
        self.assertIs(type(data[2]['athlete_count']), int)
        self.assertEqual(data[2]['athlete_count'], 0)
        for field in ('city_id', 'city_name', 'country', 'address', 'logo_url'):
            self.assertIsNone(data[2][field])

    @override_settings(AWS_STORAGE_BUCKET_NAME=None)
    def test_directory_loads_clubs_cities_and_counts_in_one_query(self):
        request = RequestFactory().get(self.url)
        with patch('federation.views.api.default_storage', FileSystemStorage(base_url='/media/')):
            with self.assertNumQueries(1):
                self.assertEqual(clubs_list(request).status_code, 200)

    def test_directory_rejects_non_get_requests(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response['Allow'], 'GET')


class HeaderSearchTests(TestCase):
    url = '/api/players_clubs_and_tournaments/list/'

    def test_search_matches_full_names_in_both_orders(self):
        player = create_player('header-search-player', name='Maria', surname='Melnik')

        for query in ('  Maria  Melnik ', 'Melnik Maria'):
            with self.subTest(query=query):
                response = self.client.get(self.url, {'typedText': query, 'limit_per_type': 4})
                self.assertEqual(response.json(), [{
                    'kind': 'player',
                    'href': f'/player/{player.pk}',
                    'value': player.get_name(),
                    'disabled': 0,
                }])

    def test_search_limits_each_kind_and_accepts_club_abbreviations(self):
        create_player('header-search-first', name='Portal', surname='Adams')
        create_player('header-search-second', name='Portal', surname='Brown')
        create_player('header-search-prefix', name='Portals', surname='Abbot')
        club = Club.objects.create(name='Visible Club', short_name='Portal Club', is_active=True)
        Club.objects.create(name='Hidden Portal Club', is_active=False)

        response = self.client.get(self.url, {'typedText': 'Portal', 'limit_per_type': 1})

        self.assertEqual(
            [(item['kind'], item['value']) for item in response.json()],
            [('player', 'ADAMS Portal'), ('club', club.name)],
        )
