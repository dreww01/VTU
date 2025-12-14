from django.core.management.base import BaseCommand
from transactions.services.verification import recheck_pending_vtu

class Command(BaseCommand):
    help = "Recheck pending VTU transactions and update their status based on VTPass"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-age",
            type=int,
            default=10,
            help="Only recheck transactions pending for more than this many minutes (default: 10)",
        )

    def handle(self, *args, **options):
        max_age = options["max_age"]
        
        self.stdout.write(
            self.style.WARNING(
                f"Rechecking pending transactions older than {max_age} minutes..."
            )
        )

        stats = recheck_pending_vtu(max_age_minutes=max_age)

        # Display results
        self.stdout.write(self.style.SUCCESS("\n=== Recheck Complete ==="))
        self.stdout.write(f"Checked: {stats['checked']}")
        self.stdout.write(self.style.SUCCESS(f"Completed: {stats['completed']}"))
        self.stdout.write(self.style.ERROR(f"Failed: {stats['failed']}"))
        self.stdout.write(f"Still Pending: {stats['still_pending']}")
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {stats['errors']}"))
            self.stdout.write(self.style.ERROR("Check logs for details or run with --verbosity=2"))
        
        self.stdout.write("")