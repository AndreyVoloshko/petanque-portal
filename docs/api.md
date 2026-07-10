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
    "petanque_draw_id": "draw-abc-123",
    "start_date": "2024-06-01",
    "start_time": "10:00:00",
    "requires_insurance": false,
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
          "rating_place": 5,
          "insurance_valid": true
        }
      ]
    }
  ]
}
```

`teams[].club` and `teams[].club_logo_url` are populated only when every player in the exported team has the same current club; otherwise both values are `null`. `players[].rating` uses the tournament-specific rating field: regular, B, League, or inclusive.

`players[].insurance_valid` is `true` when the tournament does not require insurance, or when the player's insurance expiration date is today or later; it is `false` when the tournament requires insurance and the player's insurance is missing or expired.

**Response (CSV)**

Semicolon-delimited. First row contains the minimum team size. Second row is a header. Subsequent rows are one team per line with columns: `LASTNAME1`, `FIRSTNAME1`, `GENDER1`, `CLUB1`, … (repeated per player), `NAME`, `SEED`, `STATUS`, `RANK`.

---

## Authenticated endpoints

The external draw tool owns three tournament attributes — `meta` (draw state),
`petanque_draw_id`, and team results. All three are written through **one
handler**, exposed at two URLs:

| URL | Status |
|-----|--------|
| `POST /api/tournament/` | **Primary.** Use this. |
| `POST /api/tournament/results/` | Backward compatibility only. Identical behaviour. |

The tournament page (`/tournament/<id>`) is **read-only** for these attributes:
it accepts no draw writes and answers only `GET` plus the site's own
session-authenticated, CSRF-protected form posts.

**Authentication**

Pass the API password as the raw `Authorization` header value (no `Bearer`
prefix):

```
Authorization: <password>
```

The password is configured via `APP_CREDENTIALS.api_password` in `.env`. When
`api_password` is unset, both endpoints reject every request with `401` — they
fail closed rather than falling open.

Both endpoints are exempt from CSRF (they authenticate by header, not by session
cookie) and accept no session-based authentication: an authenticated admin
browsing the site cannot invoke them, and the API password alone cannot be used
to log in. Any method other than `POST` returns `405`.

---

### `POST /api/tournament/`

Update any combination of the draw-owned attributes in a single request.

**Request body** — JSON

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tournament_id` | integer | Yes | Tournament ID |
| `meta` | object \| string | No | Draw state. A JSON object, or its pre-serialized JSON text |
| `petanque_draw_id` | string | No | Identifier of this tournament inside the draw tool; pass `""` to clear |
| `teams` | array | No | Final placements; one entry per team |
| `teams[].team_id` | integer | Yes (within `teams`) | Team ID; must be registered in this tournament |
| `teams[].place_min` | integer | Yes (within `teams`) | Final place, or shared-place lower bound |
| `teams[].place_max` | integer | No | Shared-place upper bound; omit when the team finished alone |

At least one of `meta`, `petanque_draw_id` or `teams` must be present.
Attributes that are omitted are left untouched.

`meta` must be a JSON **object** containing at least the `games` and `teams`
keys, and must not exceed **256 KB** when UTF-8 encoded.

```json
{
  "tournament_id": 1,
  "petanque_draw_id": "draw-abc-123",
  "meta": { "games": [], "teams": [], "name": "..." },
  "teams": [
    { "team_id": 7, "place_min": 1 },
    { "team_id": 8, "place_min": 3, "place_max": 4 },
    { "team_id": 9, "place_min": 3, "place_max": 4 }
  ]
}
```

**Response**

```json
{ "status": "ok", "updated_teams": [7, 8, 9] }
```

`updated_teams` lists the team IDs whose placement was written, and is `[]` when
the request contained no `teams`.

**Atomicity**

The entire request is validated before anything is written, and applied inside a
single transaction with the tournament row and every affected membership row
locked. A rejected team therefore rolls back the `meta` and `petanque_draw_id`
writes that accompanied it — a request either fully applies or changes nothing.

**Restrictions**

`meta` cannot be written once the tournament's results have been processed
(`is_processing_finished`); such requests are rejected with `403`, leaving the
finished-tournament archive immutable. `petanque_draw_id` and `teams` are not
subject to this restriction.

**Reading the values back**

`GET /tournament/team_export/<id>?format=json` returns `tournament.meta` and
`tournament.petanque_draw_id`, plus each team's `place_min` / `place_max`.
`petanque_draw_id` is read-only in the Django admin and appears on no site form:
this API is the only way to set it.

**Error responses**

| Status | Meaning |
|--------|---------|
| 400 | Invalid JSON body; no updatable attribute supplied; `meta` is not a draw object or exceeds 256 KB; `petanque_draw_id` is not a string; a team entry is malformed or is not registered in this tournament |
| 401 | Missing or incorrect API password, or `api_password` is not configured |
| 403 | `meta` write attempted on a tournament whose processing is finished |
| 404 | Tournament not found |
| 405 | Method other than `POST` |

---

### `POST /api/tournament/results/`

**Deprecated — kept for backward compatibility.** Same handler, same request and
response format as `POST /api/tournament/`, including the optional `meta` and
`petanque_draw_id` fields. Existing clients that post only `tournament_id` and
`teams` continue to work unchanged and still receive `updated_teams` in the
response. New integrations should use `POST /api/tournament/`.

---

## Audit behaviour

Every write that actually changes a value creates a `Tournament` change entry in
the Django admin journal at `/admin/admin/logentry/`, attributed to a disabled
system user and storing the affected values before and after the request. Writes
that change nothing create no entry. An authorized admin can revert a recorded
change from the journal while the stored values still match what was recorded.
See [Audit log and reverting changes](features/audit-log.md).

| Attribute | System user |
|-----------|-------------|
| `meta`, `petanque_draw_id` | `system.petanque.draw` |
| Team placements (`teams`) | `system.tournament.results` |
