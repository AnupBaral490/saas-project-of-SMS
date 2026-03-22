from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from attendance.models import TeacherAttendance
from accounts.models import TeacherProfile

class Command(BaseCommand):
    help = 'Update teacher attendance status based on real activities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to update (YYYY-MM-DD format). If not provided, updates today.',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to update (default: 1)',
        )
        parser.add_argument(
            '--all-teachers',
            action='store_true',
            help='Update all teachers, creating attendance records if they don\'t exist',
        )

    def handle(self, *args, **options):
        # Determine date range
        if options['date']:
            try:
                start_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD.')
                )
                return
        else:
            start_date = timezone.now().date()

        days = options['days']
        dates_to_update = [start_date - timedelta(days=i) for i in range(days)]

        self.stdout.write(f'Updating teacher attendance for {days} day(s) starting from {start_date}')

        total_updated = 0
        total_created = 0

        for date in dates_to_update:
            self.stdout.write(f'\nProcessing date: {date}')
            
            if options['all_teachers']:
                # Get all teachers and ensure they have attendance records
                teachers = TeacherProfile.objects.all()
                
                for teacher in teachers:
                    attendance, created = TeacherAttendance.objects.get_or_create(
                        teacher=teacher,
                        date=date,
                        defaults={
                            'status': 'absent',
                            'is_auto_marked': True
                        }
                    )
                    
                    if created:
                        total_created += 1
                        self.stdout.write(f'  Created attendance record for {teacher.user.get_full_name()}')
                    
                    # Update status based on real activities
                    old_status = attendance.status
                    attendance.determine_status_advanced()
                    attendance.save()
                    
                    if old_status != attendance.status:
                        total_updated += 1
                        self.stdout.write(
                            f'  Updated {teacher.user.get_full_name()}: {old_status} → {attendance.status}'
                        )
                        
                        # Show duties performed
                        duties = attendance.get_duties_performed()
                        if duties:
                            self.stdout.write(f'    Duties: {len(duties)} activities performed')
                        else:
                            self.stdout.write(f'    No duties performed')
                        
                        # Show subjects not attended
                        not_attended = attendance.get_subjects_not_attended()
                        if not_attended:
                            self.stdout.write(f'    Subjects not attended: {len(not_attended)}')
            else:
                # Update existing attendance records only
                attendance_records = TeacherAttendance.objects.filter(date=date)
                
                for attendance in attendance_records:
                    old_status = attendance.status
                    attendance.determine_status_advanced()
                    attendance.save()
                    
                    if old_status != attendance.status:
                        total_updated += 1
                        self.stdout.write(
                            f'  Updated {attendance.teacher.user.get_full_name()}: {old_status} → {attendance.status}'
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {total_created} new records, updated {total_updated} existing records.'
            )
        )
        
        # Show summary statistics
        self.stdout.write('\nSummary for processed dates:')
        for date in dates_to_update:
            attendance_records = TeacherAttendance.objects.filter(date=date)
            present_count = attendance_records.filter(status__in=['present', 'late']).count()
            absent_count = attendance_records.filter(status='absent').count()
            total_count = attendance_records.count()
            
            if total_count > 0:
                percentage = (present_count / total_count) * 100
                self.stdout.write(
                    f'  {date}: {present_count}/{total_count} present ({percentage:.1f}%), {absent_count} absent'
                )
