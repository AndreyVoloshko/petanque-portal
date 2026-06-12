# API Reference

Endpoints that return JSON or CSV. All URLs are relative to the site root (e.g. `http://localhost:60102`).

---

## Public endpoints

No authentication required.

### `GET /api/tournaments/list/`

Returns tournaments in a date range, formatted for FullCalendar.

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start` | ISO datetime | Yes | Range start |
| `end` | ISO datetime | Yes | Range end |

**Response** — JSON array

```json
[
  {
    "id": 1,
    "url": "/tournament/1",
    "title": "Tournament Name",
    "start": "2024-06-01",
    "end": "2024-06-02",
    "className": "tournament tournament_goes_to_rating tournament_open",
    "allDay": true
  }
]
```

---

### `GET /api/players_clubs_and_tournaments/list/`

Full-text search across players, clubs, and tournaments. Used by the site-wide autocomplete.

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `typedText` | string | Yes | Search query |

**Response** — JSON array

```json
[
  {
    "href": "/player/42",
    "value": "John Doe",
    "disabled": 0
  }
]
```

---

### `GET /api/players_list/list/`

Player search in Select2 format. Used by admin forms.

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |

**Response** — JSON

```json
{
  "results": [
    { "id": 42, "text": "John Doe" }
  ],
  "pagination": { "more": false }
}
```

---

### `GET /tournament/team_export/<id>?format=json`

Returns tournament data with registered teams and players.

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `format` | `json` \| `csv` | Yes | Use `json` or `csv`; defaults to HTML |

**Response (JSON)**

```json
{
  "tournament": {
    "id": 1,
    "name": "Tournament Name",
    "display_name": "Tournament Name (Open)",
    "meta": "...",
    "start_date": "2024-06-01",
    "start_time": "10:00:00",
    "player_rating_field": "current_rating",
    "organizer_club": { "id": 3, "name": "Club Name" },
    "main_organizer": { "id": 10, "name": "Ivan", "surname": "Petrenko", "second_name": "", "avatar_url": "https://example.com/media/player.jpg" },
    "federation_delegat": { "id": 11, "name": "Olena", "surname": "Kovalenko", "second_name": "", "avatar_url": null },
    "arbiters": [
      { "id": 12, "name": "Mykola", "surname": "Sydorenko", "second_name": "", "avatar_url": null, "is_main_arbiter": true }
    ]
  },
  "teams": [
    {
      "id": 7,
      "name": "Team Name",
      "power": 1500,
      "team_power": 1500,
      "club": { "id": 3, "name": "Club Name", "short_name": "CN", "logo_url": "https://example.com/media/club.png" },
      "club_logo_url": "https://example.com/media/club.png",
      "place_min": 1,
      "place_max": 2,
      "date_registration": "2024-05-01T12:00:00Z",
      "rating_points": 120,
      "rating_power": 1480,
      "players": [
        {
          "id": 42,
          "name": "John",
          "surname": "Doe",
          "second_name": "",
          "avatar_url": "https://example.com/media/player.jpg",
          "club": "Club Name",
          "club_id": 3,
          "club_short_name": "CN",
          "club_logo_url": "https://example.com/media/club.png",
          "sport_title": "",
          "rating": 320,
          "rating_field": "current_rating",
          "rating_place": 5
        }
      ]
    }
  ]
}
```

`teams[].club` and `teams[].club_logo_url` are populated only when every player in the exported team has the same current club; otherwise both values are `null`. `players[].rating` uses the tournament-specific rating field: regular, B, League, or inclusive.

**Response (CSV)**

Semicolon-delimited. First row contains the minimum team size. Second row is a header. Subsequent rows are one team per line with columns: `LASTNAME1`, `FIRSTNAME1`, `GENDER1`, `CLUB1`, … (repeated per player), `NAME`, `SEED`, `STATUS`, `RANK`.

---

## Authenticated endpoints

### `POST /api/tournament/results/`

Submit tournament placement results from an external application.

**Authentication**

Pass the API password in the `Authorization` header:

```
Authorization: <password>
```

The password is configured via `APP_CREDENTIALS.api_password` in `.env`.

**Request body** — JSON

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tournament_id` | integer | Yes | Tournament ID |
| `teams` | array | Yes | One entry per team |
| `teams[].team_id` | integer | Yes | Team ID |
| `teams[].place_min` | integer | Yes | Final place (or shared-place lower bound) |
| `teams[].place_max` | integer | No | Shared-place upper bound; omit if team finished alone in their place |

```json
{
  "tournament_id": 1,
  "teams": [
    { "team_id": 7, "place_min": 1 },
    { "team_id": 8, "place_min": 3, "place_max": 4 },
    { "team_id": 9, "place_min": 3, "place_max": 4 }
  ]
}
```

**Response**

```json
{ "updated_teams": [7, 8, 9] }
```

**Audit behavior**

A successful request that changes at least one submitted team's place creates a
`Tournament` change entry in the Django admin journal at
`/admin/admin/logentry/`. The entry is attributed to the disabled system user
`system.tournament.results` and stores the affected membership-place values
before and after the request. An authorized admin can revert the result change
from the journal while those memberships still match the recorded new values.

Requests that leave every submitted place unchanged do not create an audit
entry. See [Audit log and reverting changes](features/audit-log.md).

**Error responses**

| Status | Meaning |
|--------|---------|
| 400 | Validation error — `error` field contains details |
| 401 | Missing or incorrect API password |
| 404 | Tournament not found |
