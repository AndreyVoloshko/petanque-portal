# Homepage Tournament Cards Redesign Task

## Goal

Improve the homepage tournament cards in this PR so tournament information is readable, normalized, and not dependent on manually cleaned database names.

The UI should stop treating the tournament name as one large text blob. It should display separate, scan-friendly fields:

- base tournament name
- normalized localized format
- date
- location
- organizer club and country
- audience/category tags such as `жінки`, `чоловіки`, `молодь`, `юніори`, `юнаки`
- registered teams
- registration action
- rating power

No database cleanup should be required for this card redesign. Any cleanup/parsing should happen only during rendering.

## Current Problems

The current card design is hard to scan:

- The title contains too much mixed information: base name, year, format, gender/category, sometimes rank.
- Format is inconsistently written in saved names: `тир`, `дуплети`, `супермеле`, `супер-меле`, etc.
- The red `Без клубу` badge is noisy and takes visual priority even though missing club is not useful to public users.
- Date, club, country, and location are squeezed into small inline rows with inconsistent alignment.
- The bottom row has unrelated controls competing for attention: teams count, register button, power.
- Cards have uneven visual weight because long names dominate the card.
- On mobile, six items per section is too much; users should see three concise cards and use “view all” for the rest.
- Desktop section headers need clear right-top “view all” actions for each entity/category.

## Display-Only Normalization

Introduce a richer display metadata helper instead of only returning one display string.

Suggested helper shape:

```python
get_tournament_display_metadata(tournament) -> {
    "name": "Чемпіонат України",
    "format": "Тир",
    "date": "05.06.2026",
    "location": "Закарпатська",
    "club": "KSL",
    "country": "Україна",
    "audience_tags": ["жінки"],
    "registered_teams": 16,
    "registration_url": "...",
    "power": "24,2627",
}
```

This should be display-only. `Tournament.name` must not be mutated.

## Example Rendering

Saved DB name:

```txt
Чемпіонат України (тир, жінки)
```

Card should render as:

```txt
Чемпіонат України
Тир
Жінки
05.06.2026
Закарпатська
KSL, Україна
16 teams
Register button
Rating power
```

Saved DB name:

```txt
Всеукраїнські змагання "Паланок" (дуплети)
```

Card should render as:

```txt
Всеукраїнські змагання "Паланок"
Дуплети
<date>
<location>
<club if present>, Україна
```

## Format Normalization

Formats must always be canonical and localized.

Examples:

| Raw variants | Ukrainian display | English display |
| --- | --- | --- |
| `тет-а-тет`, `тети`, `tete-a-tete` | `Тет-а-тет` | `Tete-a-tete` |
| `дуплет`, `дуплети`, `doubles` | `Дуплети` | `Doubles` |
| `триплет`, `триплети`, `triples` | `Триплети` | `Triples` |
| `тир`, `shooting`, `precision shooting` | `Тир` | `Shooting` |
| `супермеле`, `супер-меле`, `super melee` | `Супер-меле` | `Super melee` |
| `клуби`, `club`, `clubs`, `EuroCup` | `Клуби` | `Clubs` |

Implementation note: avoid hardcoded Ukrainian labels in templates. Keep canonical format labels in one helper/localization map so English/Ukrainian views stay consistent.

## Audience / Category Tags

The card needs a separate “audience” area for descriptors that are not the tournament format.

Good candidates for tags:

- `Жінки`
- `Чоловіки`
- `Чоловіки, жінки`
- `Молодь`
- `Юніори`
- `Юнаки`
- `Ветерани`
- `ІІІ ранг`
- `Мікст`

Display recommendation:

- Put audience/category tags directly under the format chip.
- Use low-contrast neutral chips, not loud badges.
- Keep format as the primary chip.
- Keep audience chips secondary.
- If there are more than three tags, show the first two plus a compact `+N` chip or wrap to a second line on desktop.

Examples:

```txt
Чемпіонат України
[Тир] [Жінки] [ІІІ ранг]
```

```txt
Чемпіонат України
[Тет-а-тет] [Молодь] [Юніори] [Юнаки]
```

```txt
Чемпіонат Закарпаття
[Тир] [Чоловіки, жінки]
```

Parsing idea:

- Remove recognized format tokens from parentheses and trailing name segments.
- Keep remaining meaningful descriptors as audience tags.
- If parentheses become empty after removing format, remove the whole parentheses block from the base name.
- If parentheses contain both format and audience, keep only audience tags.

Examples:

| Saved name | Base name | Format | Audience tags |
| --- | --- | --- | --- |
| `Чемпіонат України (тир, жінки)` | `Чемпіонат України` | `Тир` | `Жінки` |
| `Чемпіонат України (дуплети, чоловіки)` | `Чемпіонат України` | `Дуплети` | `Чоловіки` |
| `Чемпіонат України (молодь, юніори, юнаки) тети` | `Чемпіонат України` | `Тет-а-тет` | `Молодь`, `Юніори`, `Юнаки` |
| `Всеукраїнські змагання "Паланок" (дуплети)` | `Всеукраїнські змагання "Паланок"` | `Дуплети` | none |

## Proposed Card Layout

Desktop card structure:

```txt
┌──────────────────────────────────────────┐
│ Чемпіонат України                        │
│ [Тир] [Жінки]                            │
│                                          │
│ calendar 05.06.2026                      │
│ pin Закарпатська                         │
│ people KSL, Україна                      │
│                                          │
│ teams 16        star 24,2627   Register  │
└──────────────────────────────────────────┘
```

Mobile card structure:

```txt
Чемпіонат України
[Тир] [Жінки]
05.06.2026 · Закарпатська
KSL, Україна
16 teams · power 24,2627
[Register]
```

Design rules:

- The title should be the base name only.
- The format should be a chip, not part of the title.
- Do not show `Без клубу` on public cards. If there is no organizer club, show only country.
- Keep country visible but not dominant.
- Use one consistent number format for power.
- If power is `0` or `0,0000`, consider muting it or hiding it unless the project wants all powers visible.
- Registration button should be the strongest action, but not stretch the card awkwardly.
- Registered teams count should be labeled by tooltip and icon, but visually clear enough without guessing.

## Homepage Section Behavior

Current homepage sections:

- rating competitions
- nearest upcoming
- athlete ranking sections

New behavior:

- Desktop: show up to six tournament cards per tournament section.
- Mobile: show only three tournament cards per tournament section.
- Keep the query limit at six, then hide cards 4-6 with responsive utility classes on mobile.
- Add a right-top “view all” button to each homepage section header.

Suggested section header layout:

```txt
Rating competitions                         View all
Nearest upcoming                            View all
Men                                         View all
Women                                       View all
Veterans                                    View all
Juniors and youth                           View all
```

For desktop, align the button to the top right of the section header. For mobile, keep it in the same row if it fits; otherwise place it under the heading as a compact button.

## Implementation Checklist

1. Add tournament display metadata helper.
2. Normalize format aliases into canonical gettext labels.
3. Extract audience/category tags from existing saved names without changing DB data.
4. Keep legacy duplication protection from the current PR.
5. Update `main_page/tournaments_list.html` to use structured metadata instead of `tournament_display_name`.
6. Redesign tournament card markup with title, chips, facts, and footer actions.
7. Update homepage section headers to include right-top “view all” links.
8. Show six cards on desktop and three cards on mobile.
9. Hide `Без клубу` on public homepage cards.
10. Add tests for metadata extraction and format normalization.
11. Browser-check desktop and mobile homepage layouts.

## Acceptance Criteria

- `Чемпіонат України (тир, жінки)` renders as base name `Чемпіонат України`, format `Тир`, and audience tag `Жінки`.
- `Всеукраїнські змагання "Паланок" (дуплети)` renders as base name `Всеукраїнські змагання "Паланок"` and format `Дуплети`.
- `супермеле`, `супер-меле`, and `super melee` render as one canonical localized format.
- Tournament DB names are not changed.
- Legacy tournament names do not duplicate year or format.
- Public cards do not show `Без клубу`; they show club only when present.
- Mobile homepage shows three tournament cards per section.
- Desktop homepage shows up to six tournament cards per section.
- Each homepage section has a clear “view all” action in the top-right header area.
- The card remains readable with long Ukrainian tournament names.
