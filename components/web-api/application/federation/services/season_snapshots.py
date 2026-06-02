from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import federation.config.rating as rating_config
from federation.models.season import Season
from federation.models.tournament import TeamTournamentMembership


@dataclass
class SeasonSnapshotResult:
    year: int
    start_date: date
    end_date: date
    processed_memberships: int
    players_considered: int
    created: int
    updated: int
    skipped: int
    deleted: int
    duplicate_existing_rows: int


def generate_season_rating_snapshot(year, replace=False):
    year = int(year)
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    values_by_player_id, processed_memberships = calculate_season_rating_values(start_date, end_date)

    deleted = 0
    if replace:
        stale_rows = Season.objects.filter(year=year)
        if values_by_player_id:
            stale_rows = stale_rows.exclude(player_id__in=values_by_player_id.keys())
        deleted = stale_rows.count()
        stale_rows.delete()

    if not values_by_player_id:
        return SeasonSnapshotResult(
            year=year,
            start_date=start_date,
            end_date=end_date,
            processed_memberships=processed_memberships,
            players_considered=0,
            created=0,
            updated=0,
            skipped=0,
            deleted=deleted,
            duplicate_existing_rows=0,
        )

    existing_rows = (
        Season.objects
        .filter(year=year, player_id__in=values_by_player_id.keys())
        .select_related('player', 'club')
        .order_by('id')
    )
    existing_by_player_id = {}
    duplicate_existing_rows = 0
    for row in existing_rows:
        if row.player_id in existing_by_player_id:
            duplicate_existing_rows += 1
            continue
        existing_by_player_id[row.player_id] = row

    rows_to_create = []
    rows_to_update = []
    skipped = 0

    for player_id, values in values_by_player_id.items():
        existing = existing_by_player_id.get(player_id)
        if existing and not replace:
            skipped += 1
            continue

        if existing:
            _apply_values_to_season(existing, values)
            rows_to_update.append(existing)
        else:
            rows_to_create.append(Season(year=year, **values))

    if rows_to_create:
        Season.objects.bulk_create(rows_to_create)

    if rows_to_update:
        Season.objects.bulk_update(rows_to_update, ['club', 'rating', 'rating_b', 'rating_liga'])

    return SeasonSnapshotResult(
        year=year,
        start_date=start_date,
        end_date=end_date,
        processed_memberships=processed_memberships,
        players_considered=len(values_by_player_id),
        created=len(rows_to_create),
        updated=len(rows_to_update),
        skipped=skipped,
        deleted=deleted,
        duplicate_existing_rows=duplicate_existing_rows,
    )


def calculate_season_rating_values(start_date, end_date):
    points_by_player_id = defaultdict(lambda: {
        'rating': [],
        'rating_b': [],
        'rating_liga': [],
    })
    players_by_id = {}

    memberships = (
        TeamTournamentMembership.objects
        .filter(
            tournament__start_date__gte=start_date,
            tournament__start_date__lte=end_date,
            tournament__is_processing_finished=True,
        )
        .select_related('tournament', 'team')
        .prefetch_related('team__players')
        .order_by('tournament__start_date', 'id')
    )

    processed_memberships = 0
    for membership in memberships:
        rating_points = membership.rating_points or Decimal('0')
        tournament = membership.tournament
        rating_fields = []

        if tournament.is_goes_to_rating:
            rating_fields.append('rating')

        if tournament.is_b_tournament:
            rating_fields.append('rating_b')

        if tournament.is_ukrainian_league:
            rating_fields.append('rating_liga')

        if not rating_fields:
            continue

        processed_memberships += 1
        for player in membership.team.players.all():
            if not player.current_club_id:
                continue

            players_by_id[player.pk] = player
            player_points = points_by_player_id[player.pk]

            for rating_field in rating_fields:
                player_points[rating_field].append(rating_points)

    values_by_player_id = {}
    for player_id, player in players_by_id.items():
        player_points = points_by_player_id[player_id]
        rating = _top_tournament_points(player_points['rating'])
        rating_b = _top_tournament_points(player_points['rating_b'])
        rating_liga = _top_tournament_points(player_points['rating_liga'])

        if not any((rating, rating_b, rating_liga)):
            continue

        values_by_player_id[player_id] = {
            'player': player,
            'club': player.current_club,
            'rating': rating,
            'rating_b': rating_b,
            'rating_liga': rating_liga,
        }

    return values_by_player_id, processed_memberships


def _top_tournament_points(points):
    tournaments_count = rating_config.RATING_PLAYER_POWER_TOURNAMENTS_COUNT
    return sum(sorted(points, reverse=True)[:tournaments_count], Decimal('0'))


def _apply_values_to_season(season, values):
    season.club = values['club']
    season.rating = values['rating']
    season.rating_b = values['rating_b']
    season.rating_liga = values['rating_liga']
