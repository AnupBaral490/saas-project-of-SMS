from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, time
from attendance.models import TeacherAttendance, TeacherActivityLog
from accounts.models import TeacherProfile
import random

class Command(BaseCommand):
    help = 'Create sample teacher attendance data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to create data for'
        )

    def handle(self, *args, **options):
        days = options['days']
        
        self.stdout.write(self.style.SUCCESS(f'Creating sample teacher attendance data for {days} days...'))
        
        teachers = TeacherProfile.objects.all()
        if not teachers.exists():
            self.stdout.write(self.style.ERROR('No teachers found. Please create teachers first.'))
            return
        
        today = timezone.now().date()
        
        for day_offset in range(days):
            date = today - timedelta(days=day_offset)
            
            self.stdout.write(f'Creating data for {date}...')
            
            for teacher in teachers:
                # Skip if attendance already exists
                if TeacherAttendance.objects.filter(teacher=teacher, date=date).exists():
                    continue
                
                # Random status with realistic distribution
                status_choices = ['present', 'present', 'present', 'late', 'absent']
                status = random.choice(status_choices)
                
                # Generate realistic times
                if status in ['present', 'late']:
                    if status == 'present':
                        check_in_hour = random.randint(8, 9)
                        check_in_minute = random.randint(0, 30)
                    else:  # late
                        check_in_hour = random.randint(9, 10)
                        check_in_minute = random.randint(31, 59)
                    
                    check_in_time = time(check_in_hour, check_in_minute)
                    
                    # Check out time (7-9 hours later)
                    work_hours = random.randint(7, 9)
                    check_out_hour = (check_in_hour + work_hours) % 24
                    check_out_minute = random.randint(0, 59)
                    check_out_time = time(check_out_hour, check_out_minute)
                    
                    total_hours = work_hours + random.uniform(-0.5, 0.5)
                else:
                    check_in_time = None
                    check_out_time = None
                    total_hours = 0
                
                # Create attendance record
                attendance = TeacherAttendance.objects.create(
                    teacher=teacher,
                    date=date,
                    status=status,
                    check_in_time=check_in_time,
                    check_out_time=check_out_time,
                    total_hours=round(total_hours, 2),
                    is_auto_marked=False,
                    remarks=f'Sample data for {date}'
                )
                
                # Create activity logs for present/late teachers
                if status in ['present', 'late']:
                    # Login activity
                    login_time = datetime.combine(date, check_in_time)
                    TeacherActivityLog.objects.create(
                        teacher=teacher,
                        activity_type='login',
                        description='Teacher logged in',
                        timestamp=timezone.make_aware(login_time)
                    )
                    
                    # Random activities during the day
                    activities = ['mark_attendance', 'create_assignment', 'view_report', 'other']
                    num_activities = random.randint(1, 4)
                    
                    for i in range(num_activities):
                        activity_time = login_time + timedelta(
                            hours=random.randint(1, 6),
                            minutes=random.randint(0, 59)
                        )
                        
                        TeacherActivityLog.objects.create(
                            teacher=teacher,
                            activity_type=random.choice(activities),
                            description=f'Sample {random.choice(activities)} activity',
                            timestamp=timezone.make_aware(activity_time)
                        )
                    
                    # Logout activity
                    if check_out_time:
                        logout_time = datetime.combine(date, check_out_time)
                        TeacherActivityLog.objects.create(
                            teacher=teacher,
                            activity_type='logout',
                            description='Teacher logged out',
                            timestamp=timezone.make_aware(logout_time)
                        )
                
                self.stdout.write(f'  Created {status} record for {teacher.user.get_full_name()}')
        
        # Summary
        total_records = TeacherAttendance.objects.count()
        today_records = TeacherAttendance.objects.filter(date=today).count()
        
        self.stdout.write(self.style.SUCCESS(f'Sample data creation completed!'))
        self.stdout.write(f'Total attendance records: {total_records}')
        self.stdout.write(f'Today\'s records: {today_records}')
        
        # Show today's summary
        if today_records > 0:
            self.stdout.write('\nToday\'s Attendance Summary:')
            for status, display in TeacherAttendance.STATUS_CHOICES:
                count = TeacherAttendance.objects.filter(date=today, status=status).count()
                if count > 0:
                    self.stdout.write(f'  {display}: {count}')