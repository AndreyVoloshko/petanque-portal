"""Lazy model accessors used to avoid audit/model import cycles."""

from functools import lru_cache

from django.core.exceptions import FieldDoesNotExist
from django.utils.text import capfirst


def get_model_field_label(model, field_name):
    """Return a model field's display label, or None for synthetic fields."""
    try:
        return capfirst(model._meta.get_field(field_name).verbose_name)
    except FieldDoesNotExist:
        return None


@lru_cache(maxsize=1)
def get_player_model():
    from federation.models.player import Player
    return Player


@lru_cache(maxsize=1)
def get_tournament_model():
    from federation.models.tournament import Tournament
    return Tournament


@lru_cache(maxsize=1)
def get_document_model():
    from federation.models.document import Document
    return Document


@lru_cache(maxsize=1)
def get_team_tournament_membership_model():
    from federation.models.tournament import TeamTournamentMembership
    return TeamTournamentMembership
