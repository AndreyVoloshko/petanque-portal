# Season Rating Snapshots

This page describes how to generate historical season rating snapshots after the season snapshot code is deployed.

## What The Snapshot Uses

- Storage: existing `federation_season` table through the `Season` model.
- Source data: processed `TeamTournamentMembership.rating_points` rows for rating tournaments in the selected calendar year.
- Included athletes: players with non-zero points in at least one stored season rating field.
- Date range: January 1 through December 31 of the selected year.
- Safety: the command does not delete tournaments, tournament results, or players.

## Production Steps After Merge

1. Deploy the merged code using the normal production deployment process.
2. Rebuild or restart the service that runs Django and cron so the new command and cron file are loaded.
3. Generate missing seasons:

```bash
cd /path/to/petanque_portal
docker compose exec -T petanque_portal_web_api \
  python manage.py generate_season_rating_snapshot --from-year 2020 --to-year 2025
```

If production uses an explicit Compose project name, include it:

```bash
docker compose -p <project-name> exec -T petanque_portal_web_api \
  python manage.py generate_season_rating_snapshot --from-year 2020 --to-year 2025
```

Do not use `--replace` unless the existing rows for a year must intentionally be recalculated. With `--replace`, stale `Season` rows for that year are removed when they no longer have qualifying tournament results.

If any 2020-2025 rows were generated before this branch was merged, run the backfill with `--replace` once:

```bash
docker compose exec -T petanque_portal_web_api \
  python manage.py generate_season_rating_snapshot --from-year 2020 --to-year 2025 --replace
```

## Validation

Check counts by year:

```bash
docker compose exec -T petanque_portal_web_api python manage.py shell -c \
"from django.db.models import Count; from federation.models.season import Season; print(list(Season.objects.values('year').annotate(count=Count('id')).order_by('year')))"
```

Check pages in the browser:

- `/seasons`
- `/seasons/2025`
- `/seasons/2017`

The `/seasons` page should open the latest available season.

## Yearly Automation

The web service cron file includes:

```cron
5 0 1 1 * root cd /application && python manage_cron.py generate_season_rating_snapshot --previous-year >> /var/log/cron.log 2>&1
```

On January 1 it generates the previous calendar year's snapshot. For example, on January 1, 2027 it generates the 2026 season.
