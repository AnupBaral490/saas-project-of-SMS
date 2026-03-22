from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from attendance.models import AttendanceSession
from academic.models import TeacherSubjectAssignment

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample attendance sessions for testing Recent Activities'

    def handle(self, *args, **options):
        # Get teacher assignments
        teacher_assignments = TeacherSubjectAssignment.objects.all()
        
        if not teacher_assignments.exists():
            self.stdout.write(self.style.ERROR('No teacher assignments found. Please create teacher assignments first.'))
            return

        created_count = 0
        
        # Create sample sessions for the last few days
        for i in range(5):  # Create 5 sample sessions
            date = timezone.now().date() - timedelta(days=i)
            
            for assignment in teacher_assignments[:2]:  # Use first 2 assignments
                try:
                    # Create a session
                    session = AttendanceSession.objects.create(
                        teacher_assignment=assignment,
                        date=date,
                        start_time=datetime.strptime('09:00', '%H:%M').time(),
                        end_time=datetime.strptime('10:00', '%H:%M').time(),
                        topic_covered=f'Sample topic for {assignment.subject.name}',
                        notes=f'Sample notes for {date}',
                        is_completed=i % 2 == 0  # Alternate between completed and not completed
                    )
                    created_count += 1
                    self.stdout.write(f'Created session: {session}')
                    
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Session might already exist for {assignment} on {date}: {e}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} sample attendance sessions.'
            )
        )