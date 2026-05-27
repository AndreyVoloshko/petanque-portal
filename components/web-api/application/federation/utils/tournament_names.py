import re


FORMAT_TIR = "Тир"
FORMAT_TETE_A_TETE = "Тет-а-тет"
FORMAT_DOUBLETS = "Дуплети"
FORMAT_TRIPLETS = "Триплети"
FORMAT_CLUBS = "Клуби"
FORMAT_SUPER_MELEE = "Супер-меле"

_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_SPACES_RE = re.compile(r"\s+")
_SEARCH_SEPARATOR_RE = re.compile(r"[\W_]+", re.UNICODE)

_FORMAT_ALIASES = {
    FORMAT_TIR: (
        r"(?<![0-9a-zа-яіїєґ])тир(?![0-9a-zа-яіїєґ])",
        r"shooting",
        r"precision\s+shooting",
    ),
    FORMAT_TETE_A_TETE: (
        r"тет[\s\-–—]*а[\s\-–—]*тет",
        r"(?<![0-9a-zа-яіїєґ])тет[иі]?(?![0-9a-zа-яіїєґ])",
        r"t[eê]te[\s\-–—]*[aà][\s\-–—]*t[eê]te",
        r"singles?",
    ),
    FORMAT_DOUBLETS: (
        r"дуплет[а-яіїєґ]*",
        r"doubles?",
        r"doublettes?",
    ),
    FORMAT_TRIPLETS: (
        r"триплет[а-яіїєґ]*",
        r"triples?",
        r"triplettes?",
    ),
    FORMAT_CLUBS: (
        r"клуб[а-яіїєґ]*",
        r"eurocup",
        r"clubs?",
    ),
    FORMAT_SUPER_MELEE: (
        r"супер[\s\-–—]*меле",
        r"super[\s\-–—]*melee",
        r"(?<![0-9a-zа-яіїєґ])меле(?![0-9a-zа-яіїєґ])",
    ),
}


def clean_tournament_name(name):
    return _SPACES_RE.sub(" ", str(name or "")).strip().rstrip(".").strip()


def get_tournament_year(tournament):
    start_date = getattr(tournament, "start_date", None)
    if not start_date:
        return None

    return start_date.year


def get_tournament_format_name(tournament):
    tournament_format = getattr(tournament, "format", None)
    if tournament_format == "tir":
        return FORMAT_TIR
    if tournament_format == "mele":
        return FORMAT_SUPER_MELEE

    players_min = getattr(tournament, "number_of_players_in_team_min", None)
    try:
        players_min = int(players_min)
    except (TypeError, ValueError):
        return None

    if players_min == 1:
        return FORMAT_TETE_A_TETE
    if players_min == 2:
        return FORMAT_DOUBLETS
    if players_min == 3:
        return FORMAT_TRIPLETS
    if players_min >= 6:
        return FORMAT_CLUBS

    return None


def normalize_tournament_name(base_name, year=None, format_name=None):
    display_parts = [clean_tournament_name(base_name)]
    source_name = display_parts[0]

    if year and not _name_contains_year(source_name):
        display_parts.append(str(year))

    if format_name and not _name_contains_format(source_name, format_name):
        display_parts.append(format_name)

    return ". ".join(part for part in display_parts if part)


def get_tournament_display_name(tournament):
    return normalize_tournament_name(
        getattr(tournament, "name", ""),
        year=get_tournament_year(tournament),
        format_name=get_tournament_format_name(tournament),
    )


def tournament_display_name_matches(tournament, search_text):
    search_text = _normalize_search_text(search_text)
    if not search_text:
        return False

    return search_text in _normalize_search_text(get_tournament_display_name(tournament))


def _name_contains_year(name):
    return bool(_YEAR_RE.search(name or ""))


def _name_contains_format(name, format_name):
    aliases = _FORMAT_ALIASES.get(format_name, (re.escape(format_name),))
    normalized_name = clean_tournament_name(name).lower()

    for alias in aliases:
        if re.search(alias, normalized_name, flags=re.IGNORECASE):
            return True

    return False


def _normalize_search_text(value):
    value = clean_tournament_name(value).lower()
    value = _SEARCH_SEPARATOR_RE.sub(" ", value)
    return _SPACES_RE.sub(" ", value).strip()
