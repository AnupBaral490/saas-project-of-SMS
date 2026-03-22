from django.core.management.base import BaseCommand
from academic.models import AcademicYear
from datetime import date

class Command(BaseCommand):
    help = 'Create a default academic year if none exists'

    def handle(self, *args, **options):
        # Check if there's already a current academic year
        current_year = AcademicYear.objects.filter(is_current=True).first()
        
        if current_year:
            self.stdout.write(
                self.style.SUCCESS(f'Current academic year already exists: {current_year.year}')
            )
            return
        
        # Create a default academic year
        academic_year = AcademicYear.objects.create(
            year="2025-2026",
            start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31),
            is_current=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created academic year: {academic_year.year}')
        )