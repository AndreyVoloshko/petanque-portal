from django.db.models import Count


def rating_rank_map(queryset, ranking_field):
    rows = (
        queryset
        .values(ranking_field)
        .annotate(players_count=Count('id'))
        .order_by('-' + ranking_field)
    )

    ranks = {}
    higher_players_count = 0
    for row in rows:
        value = row[ranking_field]
        ranks[value] = higher_players_count + 1
        higher_players_count += row['players_count']

    return ranks


def attach_rating_positions(players, ranking_field, ranking_queryset, attr_name='rating_position_value'):
    ranks = rating_rank_map(ranking_queryset, ranking_field)

    for player in players:
        setattr(player, attr_name, ranks.get(getattr(player, ranking_field), ''))

    return players
