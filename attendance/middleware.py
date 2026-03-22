from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from datetime import datetime, time
from .models import TeacherAttendance, TeacherActivityLog, TeacherSchedule, GeofenceLocation

class EnhancedTeacherAttendanceMiddleware(MiddlewareMixin):
    """
    Enhanced middleware for automatic teacher attendance tracking with schedule validation
    """
    
    def process_request(self, request):
        # Only track authenticated users who are teachers
        if not request.user.is_authenticated:
            return None
        
        if request.user.user_type != 'teacher':
            return None
        
        if not hasattr(request.user, 'teacher_profile'):
            return None
        
        teacher = request.user.teacher_profile
        organization = getattr(request.user, 'organization', None)
        today = timezone.now().date()
        current_time = timezone.now()
        current_time_only = current_time.time()
        
        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent for device tracking
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        
        # Check if teacher is on campus (simulated for now)
        is_on_campus = self._verify_location(ip_address)
        
        # Get or create today's attendance record
        attendance, created = TeacherAttendance.objects.get_or_create(
            organization=organization,
            teacher=teacher,
            date=today,
            defaults={
                'check_in_time': current_time_only,
                'ip_address': ip_address,
                'device_info': user_agent,
                'is_auto_marked': True,
                'validation_method': 'schedule_based',
                'location_verified': is_on_campus,
                'status': 'present'  # Will be recalculated
            }
        )
        
        # If this is the first activity of the day, set real check-in time
        if created:
            attendance.first_activity_time = current_time
            self._log_activity(request, teacher, ip_address, user_agent, is_on_campus, is_first_activity=True)
        else:
            # Update last activity time
            attendance.last_activity_time = current_time
            self._log_activity(request, teacher, ip_address, user_agent, is_on_campus, is_first_activity=False)
        
        # Always update check-out time with current activity (last activity = check out)
        attendance.check_out_time = current_time_only
        
        # Calculate scheduled hours and determine status using enhanced logic
        attendance.calculate_scheduled_hours()
        attendance.calculate_hours()
        attendance.determine_status_advanced()
        attendance.save()
        
        return None
    
    def _verify_location(self, ip_address):
        """Verify if teacher is on campus based on IP or geolocation"""
        # For now, simulate campus verification
        # In real implementation, you would:
        # 1. Check IP against known campus IP ranges
        # 2. Use geolocation API to get coordinates
        # 3. Check against GeofenceLocation boundaries
        
        # Simulate: local IPs are considered on-campus
        if ip_address and (ip_address.startswith('192.168.') or 
                          ip_address.startswith('10.') or 
                          ip_address == '127.0.0.1'):
            return True
        
        return False
    
    def _log_activity(self, request, teacher, ip_address, user_agent, is_on_campus, is_first_activity=False):
        """Log specific teacher activities with enhanced tracking"""
        path = request.path
        method = request.method
        
        # Determine activity type and priority based on URL pattern
        activity_type = 'other'
        priority_level = 'low'
        description = ''
        related_schedule = None
        
        if 'login' in path or 'accounts/login' in path:
            activity_type = 'login'
            priority_level = 'medium'
            description = 'Teacher logged in to system'
        elif 'logout' in path:
            activity_type = 'logout'
            priority_level = 'medium'
            description = 'Teacher logged out from system'
        elif ('attendance/mark' in path or 'attendance/save' in path or 
              'save_attendance_ajax' in path) and method == 'POST':
            activity_type = 'mark_attendance'
            priority_level = 'high'
            description = 'Marked student attendance'
            # This is a significant activity - update teacher attendance status
            self._update_teacher_attendance_status(teacher)
            # Try to link to scheduled class
            related_schedule = self._find_current_schedule(teacher)
        elif 'assignment' in path and method == 'POST':
            activity_type = 'create_assignment'
            priority_level = 'high'
            description = 'Created/updated assignment'
        elif 'exam' in path or 'result' in path:
            activity_type = 'grade_exam'
            priority_level = 'high'
            description = 'Graded exam/entered results'
        elif 'message' in path and method == 'POST':
            activity_type = 'send_message'
            priority_level = 'medium'
            description = 'Sent message'
        elif 'report' in path:
            activity_type = 'view_report'
            priority_level = 'medium'
            description = 'Viewed reports'
        elif 'dashboard' in path:
            activity_type = 'dashboard_access'
            priority_level = 'low'
            description = 'Accessed dashboard'
        elif method == 'GET' and any(x in path for x in ['academic', 'attendance', 'accounts']):
            activity_type = 'system_navigation'
            priority_level = 'low'
            description = f'Navigated to {path}'
        
        # Mark first activity of the day specially
        if is_first_activity:
            if activity_type == 'other':
                activity_type = 'first_login'
                description = f'First system access of the day - {path}'
            else:
                description = f'FIRST ACTIVITY: {description}'
        
        # Log all activities with enhanced tracking
        TeacherActivityLog.objects.create(
            organization=getattr(teacher.user, 'organization', None),
            teacher=teacher,
            activity_type=activity_type,
            priority_level=priority_level,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            is_on_campus=is_on_campus,
            related_schedule=related_schedule
        )
    
    def _find_current_schedule(self, teacher):
        """Find the current scheduled class for the teacher"""
        current_time = timezone.now()
        weekday = current_time.weekday()
        current_time_only = current_time.time()
        
        # Find schedule that matches current time (within 30 minutes)
        schedules = TeacherSchedule.objects.filter(
            teacher=teacher,
            day_of_week=weekday,
            is_active=True,
            start_time__lte=current_time_only
        )
        
        for schedule in schedules:
            # Check if current time is within class period (with 30 min buffer)
            end_time_with_buffer = datetime.combine(
                current_time.date(), 
                schedule.end_time
            ) + timezone.timedelta(minutes=30)
            
            if current_time <= end_time_with_buffer:
                return schedule
        
        return None
    
    def _update_teacher_attendance_status(self, teacher):
        """Update teacher attendance status when they perform significant activities"""
        today = timezone.now().date()
        
        try:
            attendance = TeacherAttendance.objects.get(
                organization=getattr(teacher.user, 'organization', None),
                teacher=teacher,
                date=today,
            )
            # Recalculate status based on enhanced logic
            attendance.determine_status_advanced()
            attendance.save()
        except TeacherAttendance.DoesNotExist:
            # This shouldn't happen as attendance is created in process_request
            pass
