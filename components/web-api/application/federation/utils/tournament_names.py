import re

from django.utils.translation import get_language


FORMAT_TIR = "Тир"
FORMAT_TETE_A_TETE = "Тет-а-тет"
FORMAT_DOUBLETS = "Дуплети"
FORMAT_TRIPLETS = "Триплети"
FORMAT_CLUBS = "Клуби"
FORMAT_SUPER_MELEE = "Супер-меле"

_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_SPACES_RE = re.compile(r"\s+")
_SEARCH_SEPARATOR_RE = re.compile(r"[\W_]+", re.UNICODE)
_TRAILING_SEPARATOR_RE = re.compile(r"[\s.\-–—,:;]+$")
_LEADING_SEPARATOR_RE = re.compile(r"^[\s.\-–—,:;]+")

_FORMAT_LABELS = {
    FORMAT_TIR: {
        "uk": "Тир",
        "en": "Shooting",
    },
    FORMAT_TETE_A_TETE: {
        "uk": "Тет-а-тет",
        "en": "Tete-a-tete",
    },
    FORMAT_DOUBLETS: {
        "uk": "Дуплети",
        "en": "Doubles",
    },
    FORMAT_TRIPLETS: {
        "uk": "Триплети",
        "en": "Triples",
    },
    FORMAT_CLUBS: {
        "uk": "Клуби",
        "en": "Clubs",
    },
    FORMAT_SUPER_MELEE: {
        "uk": "Супер-меле",
        "en": "Super melee",
    },
}

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
        r"(?<![0-9a-zа-яіїєґ])клуби(?![0-9a-zа-яіїєґ])",
        r"eurocup",
        r"clubs?",
    ),
    FORMAT_SUPER_MELEE: (
        r"супер[\s\-–—]*меле",
        r"super[\s\-–—]*melee",
        r"(?<![0-9a-zа-яіїєґ])меле(?![0-9a-zа-яіїєґ])",
    ),
}

_AUDIENCE_LABELS = (
    (r"жінк[аи]?|women|female", {"uk": "Жінки", "en": "Women"}),
    (r"чоловік[и]?|men|male", {"uk": "Чоловіки", "en": "Men"}),
    (r"молодь|youth", {"uk": "Молодь", "en": "Youth"}),
    (r"юніори?|juniors?", {"uk": "Юніори", "en": "Juniors"}),
    (r"юнаки|cadets?", {"uk": "Юнаки", "en": "Cadets"}),
    (r"ветерани?|veterans?", {"uk": "Ветерани", "en": "Veterans"}),
    (r"дорослі|adults?", {"uk": "Дорослі", "en": "Adults"}),
    (r"мікст|mix|mixed", {"uk": "Мікст", "en": "Mixed"}),
)


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


def get_localized_tournament_format_name(format_name):
    if not format_name:
        return None

    language = _current_language()
    return _FORMAT_LABELS.get(format_name, {}).get(language, format_name)


def get_tournament_card_metadata(tournament):
    raw_name = clean_tournament_name(getattr(tournament, "name", ""))
    format_name = _find_format_in_text(raw_name) or get_tournament_format_name(tournament)
    base_name, audience_tags = _extract_card_name_parts(raw_name, format_name)

    return {
        "name": base_name,
        "format": get_localized_tournament_format_name(format_name),
        "format_source": format_name,
        "audience_tags": audience_tags,
    }


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


def _find_format_in_text(text):
    normalized_text = clean_tournament_name(text).lower()
    for format_name, aliases in _FORMAT_ALIASES.items():
        for alias in aliases:
            if re.search(alias, normalized_text, flags=re.IGNORECASE):
                return format_name

    return None


def _extract_card_name_parts(name, format_name):
    audience_tags = []
    base_name = _remove_parenthetical_descriptors(name, format_name, audience_tags)
    base_name = _remove_structured_suffixes(base_name, format_name, audience_tags)
    base_name = _remove_inline_suffixes(base_name, format_name, audience_tags)
    base_name = _clean_display_part(base_name)

    if not base_name:
        base_name = clean_tournament_name(name)

    return base_name, audience_tags


def _remove_parenthetical_descriptors(name, format_name, audience_tags):
    def replace_match(match):
        descriptor = match.group(1)
        descriptor_tags = _extract_audience_tags(descriptor, format_name)
        if descriptor_tags and _contains_only_card_metadata(descriptor, format_name):
            _append_unique(audience_tags, descriptor_tags)
            return ""

        if _text_contains_format(descriptor, format_name) and _contains_only_card_metadata(descriptor, format_name):
            return ""

        return match.group(0)

    return re.sub(r"\(([^()]*)\)", replace_match, name)


def _remove_structured_suffixes(name, format_name, audience_tags):
    parts = [part.strip() for part in re.split(r"\s*\.\s*", name) if part.strip()]
    if len(parts) <= 1:
        return name

    while len(parts) > 1:
        last_part = parts[-1]
        if _YEAR_RE.fullmatch(last_part):
            parts.pop()
            continue

        descriptor_tags = _extract_audience_tags(last_part, format_name)
        if descriptor_tags and _contains_only_card_metadata(last_part, format_name):
            _append_unique(audience_tags, descriptor_tags)
            parts.pop()
            continue

        if _text_contains_format(last_part, format_name) and _contains_only_card_metadata(last_part, format_name):
            parts.pop()
            continue

        break

    return ". ".join(parts)


def _remove_inline_suffixes(name, format_name, audience_tags):
    value = name

    value = re.sub(r"\s*(?:[.\-–—]\s*)?(?:19|20)\d{2}\s*$", "", value)
    value = _remove_trailing_format(value, format_name)

    descriptor_tags = _extract_trailing_audience_tags(value, format_name)
    if descriptor_tags:
        _append_unique(audience_tags, descriptor_tags)
        for tag in descriptor_tags:
            value = _remove_trailing_audience_label(value, tag)

    value = _remove_trailing_format(value, format_name)
    value = re.sub(r"\s*(?:[.\-–—]\s*)?(?:19|20)\d{2}\s*$", "", value)

    return value


def _remove_trailing_format(value, format_name):
    if not format_name:
        return value

    result = value
    for alias in _FORMAT_ALIASES.get(format_name, ()):
        result = re.sub(
            r"[\s.\-–—,:;]*" + alias + r"\s*$",
            "",
            result,
            flags=re.IGNORECASE,
        )

    return result


def _extract_trailing_audience_tags(value, format_name):
    pieces = re.split(r"[\s.\-–—,:;]+", value)
    if not pieces:
        return []

    last_piece = pieces[-1]
    return _extract_audience_tags(last_piece, format_name)


def _remove_trailing_audience_label(value, tag):
    for pattern, labels in _AUDIENCE_LABELS:
        if tag in labels.values():
            return re.sub(
                r"[\s.\-–—,:;]*" + pattern + r"\s*$",
                "",
                value,
                flags=re.IGNORECASE,
            )

    return value


def _extract_audience_tags(text, format_name):
    tags = []
    pieces = [piece.strip() for piece in re.split(r"[,;/]+", clean_tournament_name(text)) if piece.strip()]
    if not pieces:
        return []

    for piece in pieces:
        piece_without_format = _remove_format_aliases(piece, format_name)
        piece_without_format = _YEAR_RE.sub("", piece_without_format)
        piece_without_format = _clean_display_part(piece_without_format)

        if not piece_without_format:
            continue

        tag = _normalize_audience_tag(piece_without_format)
        if tag:
            _append_unique(tags, [tag])

    return tags


def _contains_only_card_metadata(text, format_name):
    pieces = [piece.strip() for piece in re.split(r"[,;/]+", clean_tournament_name(text)) if piece.strip()]
    if not pieces:
        return False

    contains_metadata = False
    for piece in pieces:
        piece_without_format = _remove_format_aliases(piece, format_name)
        if piece_without_format != piece:
            contains_metadata = True

        piece_without_year = _YEAR_RE.sub("", piece_without_format)
        if piece_without_year != piece_without_format:
            contains_metadata = True

        remaining = _clean_display_part(piece_without_year)
        if not remaining:
            continue

        if _normalize_audience_tag(remaining):
            contains_metadata = True
            continue

        return False

    return contains_metadata


def _remove_format_aliases(value, format_name):
    result = value
    formats_to_remove = [format_name] if format_name else list(_FORMAT_ALIASES)

    for current_format in formats_to_remove:
        if not current_format:
            continue
        for alias in _FORMAT_ALIASES.get(current_format, ()):
            result = re.sub(alias, "", result, flags=re.IGNORECASE)

    return result


def _text_contains_format(text, format_name):
    if format_name and _name_contains_format(text, format_name):
        return True

    return _find_format_in_text(text) is not None


def _normalize_audience_tag(value):
    normalized = clean_tournament_name(value).lower()
    if not normalized:
        return None

    language = _current_language()
    for pattern, labels in _AUDIENCE_LABELS:
        if re.fullmatch(pattern, normalized, flags=re.IGNORECASE):
            return labels[language]

    rank_match = re.fullmatch(r"([ivxіїvх]+)\s*ранг", normalized, flags=re.IGNORECASE)
    if rank_match:
        roman_rank = rank_match.group(1).upper()
        return f"{roman_rank} ранг" if language == "uk" else f"{roman_rank} rank"

    group_match = re.fullmatch(r"група\s+([a-zа-яіїєґ])", normalized, flags=re.IGNORECASE)
    if group_match:
        group_name = group_match.group(1).upper()
        return f"Група {group_name}" if language == "uk" else f"Group {group_name}"

    return None


def _append_unique(target, values):
    for value in values:
        if value and value not in target:
            target.append(value)


def _clean_display_part(value):
    value = _SPACES_RE.sub(" ", str(value or "")).strip()
    value = _TRAILING_SEPARATOR_RE.sub("", value)
    value = _LEADING_SEPARATOR_RE.sub("", value)
    return value.strip()


def _current_language():
    language = get_language() or "uk"
    return "uk" if language.startswith("uk") else "en"


def _normalize_search_text(value):
    value = clean_tournament_name(value).lower()
    value = _SEARCH_SEPARATOR_RE.sub(" ", value)
    return _SPACES_RE.sub(" ", value).strip()
