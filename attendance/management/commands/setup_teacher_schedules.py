from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import TeacherProfile
from academic.models import TeacherSubjectAssignment, AcademicYear
from attendance.models import TeacherSchedule, GeofenceLocation
from datetime import time

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up teacher schedules for automatic attendance tracking'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up teacher schedules for enhanced attendance tracking...'))
        
        # Create campus geofence location
        self.create_campus_geofence()
        
        # Get current academic year
        try:
            current_year = AcademicYear.objects.get(is_current=True)
        except AcademicYear.DoesNotExist:
            self.stdout.write(self.style.ERROR('No current academic year found. Please create one first.'))
            return
        
        # Get all teacher subject assignments
        assignments = TeacherSubjectAssignment.objects.filter(
            academic_year=current_year
        ).select_related('teacher__user', 'subject', 'class_assigned')
        
        if not assignments.exists():
            self.stdout.write(self.style.ERROR('No teacher subject assignments found. Please create assignments first.'))
            return
        
        # Clear existing schedules
        TeacherSchedule.objects.all().delete()
        
        # Create sample schedules for each teacher
        schedule_count = 0
        
        # Define time slots
        time_slots = [
            (time(9, 0), time(10, 0)),   # Period 1: 9:00-10:00
            (time(10, 15), time(11, 15)), # Period 2: 10:15-11:15
            (time(11, 30), time(12, 30)), # Period 3: 11:30-12:30
            (time(13, 30), time(14, 30)), # Period 4: 13:30-14:30 (after lunch)
            (time(14, 45), time(15, 45)), # Period 5: 14:45-15:45
        ]
        
        # Group assignments by teacher
        teacher_assignments = {}
        for assignment in assignments:
            teacher = assignment.teacher
            if teacher not in teacher_assignments:
                teacher_assignments[teacher] = []
            teacher_assignments[teacher].append(assignment)
        
        for teacher, teacher_assignment_list in teacher_assignments.items():
            self.stdout.write(f'\nCreating schedule for: {teacher.user.get_full_name()}')
            
            # Distribute assignments across weekdays and time slots
            assignment_index = 0
            
            for day_of_week in range(5):  # Monday to Friday (0-4)
                day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'][day_of_week]
                
                # Assign 2-3 classes per day for each teacher
                classes_per_day = min(3, len(teacher_assignment_list) - assignment_index)
                
                for slot_index in range(classes_per_day):
                    if assignment_index >= len(teacher_assignment_list):
                        break
                    
                    assignment = teacher_assignment_list[assignment_index]
                    start_time, end_time = time_slots[slot_index % len(time_slots)]
                    
                    # Create schedule
                    schedule = TeacherSchedule.objects.create(
                        teacher=teacher,
                        subject_assignment=assignment,
                        day_of_week=day_of_week,
                        start_time=start_time,
                        end_time=end_time,
                        classroom=f"Room {100 + assignment_index}",
                        is_active=True
                    )
                    
                    schedule_count += 1
                    assignment_index += 1
                    
                    self.stdout.write(f'  {day_name} {start_time}-{end_time}: {assignment.subject.name} - {assignment.class_assigned}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Created {schedule_count} schedule entries for {len(teacher_assignments)} teachers'))
        
        # Show summary
        self.show_schedule_summary()
        
        self.stdout.write(self.style.SUCCESS('\n🎯 Enhanced automatic attendance tracking is now ready!'))
        self.stdout.write('Teachers will be automatically tracked based on:')
        self.stdout.write('  ✅ Scheduled class attendance')
        self.stdout.write('  ✅ Real-time activity monitoring')
        self.stdout.write('  ✅ Location verification')
        self.stdout.write('  ✅ Performance scoring')
    
    def create_campus_geofence(self):
        """Create a sample campus geofence location"""
        geofence, created = GeofenceLocation.objects.get_or_create(
            name='Main Campus',
            defaults={
                'description': 'Primary school campus area',
                'center_lat': 27.7172,  # Sample coordinates (Kathmandu)
                'center_lng': 85.3240,
                'radius_meters': 500,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write('✓ Created campus geofence location')
        else:
            self.stdout.write('✓ Campus geofence location already exists')
    
    def show_schedule_summary(self):
        """Show summary of created schedules"""
        self.stdout.write('\n📊 SCHEDULE SUMMARY:')
        
        teachers = TeacherProfile.objects.filter(schedules__isnull=False).distinct()
        
        for teacher in teachers:
            schedules = TeacherSchedule.objects.filter(teacher=teacher, is_active=True)
            total_hours = sum(schedule.duration_minutes for schedule in schedules) / 60
            
            self.stdout.write(f'\n👤 {teacher.user.get_full_name()}:')
            self.stdout.write(f'   📅 Total Classes: {schedules.count()}')
            self.stdout.write(f'   ⏰ Weekly Hours: {total_hours:.1f}')
            
            # Show daily breakdown
            for day in range(5):
                day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][day]
                day_schedules = schedules.filter(day_of_week=day)
                if day_schedules.exists():
                    classes = ', '.join([f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}" for s in day_schedules])
                    self.stdout.write(f'   {day_name}: {classes}')