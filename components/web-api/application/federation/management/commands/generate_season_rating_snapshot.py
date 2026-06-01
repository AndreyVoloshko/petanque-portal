from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from federation.services.season_snapshots import generate_season_rating_snapshot


class Command(BaseCommand):
    help = "Generate historical season rating snapshots into the existing Season table."

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Generate one season snapshot for this year.')
        parser.add_argument('--from-year', type=int, help='First year in a generated range.')
        parser.add_argument('--to-year', type=int, help='Last year in a generated range.')
        parser.add_argument(
            '--previous-year',
            action='store_true',
            help='Generate the snapshot for the previous calendar year.',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Replace existing season rows for the selected year with recalculated tournament-result rows.',
        )

    def handle(self, *args, **options):
        years = self._get_years(options)
        replace = options['replace']

        for year in years:
            result = generate_season_rating_snapshot(year, replace=replace)
            self.stdout.write(
                "Season {year}: {start} through {end}; memberships={memberships}; "
                "players={players}; created={created}; updated={updated}; skipped={skipped}; deleted={deleted}; "
                "duplicate_existing_rows={duplicates}".format(
                    year=result.year,
                    start=result.start_date,
                    end=result.end_date,
                    memberships=result.processed_memberships,
                    players=result.players_considered,
                    created=result.created,
                    updated=result.updated,
                    skipped=result.skipped,
                    deleted=result.deleted,
                    duplicates=result.duplicate_existing_rows,
                )
            )

        self.stdout.write(self.style.SUCCESS("Season rating snapshot generation finished."))

    def _get_years(self, options):
        selected_modes = [
            bool(options.get('year')),
            bool(options.get('previous_year')),
            bool(options.get('from_year') or options.get('to_year')),
        ]

        if sum(selected_modes) != 1:
            raise CommandError(
                "Choose exactly one mode: --year, --previous-year, or --from-year/--to-year."
            )

        if options.get('previous_year'):
            return [timezone.localdate().year - 1]

        if options.get('year'):
            return [options['year']]

        from_year = options.get('from_year')
        to_year = options.get('to_year')
        if not from_year or not to_year:
            raise CommandError("--from-year and --to-year must be used together.")

        if from_year > to_year:
            raise CommandError("--from-year must be less than or equal to --to-year.")

        return range(from_year, to_year + 1)
