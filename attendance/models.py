from django.db import models
from django.utils import timezone
from accounts.models import StudentProfile, TeacherProfile
from academic.models import Subject, Class, TeacherSubjectAssignment
from datetime import datetime, time, timedelta

class AttendanceSession(models.Model):
    """Represents a single class session for attendance marking"""
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='attendance_sessions', null=True, blank=True)
    teacher_assignment = models.ForeignKey(TeacherSubjectAssignment, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    topic_covered = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'teacher_assignment', 'date', 'start_time'], name='unique_attendance_session_per_org'),
        ]
    
    def __str__(self):
        return f"{self.teacher_assignment.subject.name} - {self.teacher_assignment.class_assigned} - {self.date}"

class AttendanceRecord(models.Model):
    ATTENDANCE_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    )
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='attendance_records', null=True, blank=True)
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=ATTENDANCE_CHOICES)
    remarks = models.TextField(blank=True)
    marked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'session', 'student'], name='unique_attendance_record_per_org'),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.session} - {self.status}"

    def save(self, *args, **kwargs):
        if self.session_id and self.organization_id is None:
            self.organization = self.session.organization
        super().save(*args, **kwargs)

class AttendanceSummary(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='attendance_summaries', null=True, blank=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE)
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()
    total_sessions = models.PositiveIntegerField(default=0)
    sessions_attended = models.PositiveIntegerField(default=0)
    sessions_late = models.PositiveIntegerField(default=0)
    sessions_excused = models.PositiveIntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'student', 'subject', 'class_enrolled', 'month', 'year'], name='unique_attendance_summary_per_org'),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.name} - {self.month}/{self.year}"
    
    def calculate_percentage(self):
        if self.total_sessions > 0:
            # Count present, late, and excused as attended
            attended = self.sessions_attended + self.sessions_late + self.sessions_excused
            self.attendance_percentage = (attended / self.total_sessions) * 100
        else:
            self.attendance_percentage = 0.00
        return self.attendance_percentage


class TeacherSchedule(models.Model):
    """Weekly schedule for teachers"""
    WEEKDAYS = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='teacher_schedules', null=True, blank=True)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='schedules')
    subject_assignment = models.ForeignKey(TeacherSubjectAssignment, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'teacher', 'subject_assignment', 'day_of_week', 'start_time'], name='unique_teacher_schedule_per_org'),
        ]
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"
    
    @property
    def duration_minutes(self):
        """Calculate class duration in minutes"""
        start_datetime = datetime.combine(datetime.today(), self.start_time)
        end_datetime = datetime.combine(datetime.today(), self.end_time)
        return int((end_datetime - start_datetime).total_seconds() / 60)


class TeacherAttendance(models.Model):
    """Daily attendance record for teachers with enhanced automatic tracking"""
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
        ('partial', 'Partial Attendance'),
    )
    
    VALIDATION_METHODS = (
        ('schedule_based', 'Schedule Based'),
        ('activity_based', 'Activity Based'),
        ('geolocation', 'Geolocation'),
        ('biometric', 'Biometric'),
        ('manual', 'Manual Entry'),
    )
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='teacher_attendance_records', null=True, blank=True)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='absent')
    
    # Time tracking
    first_activity_time = models.DateTimeField(null=True, blank=True, help_text="Exact time of first activity")
    last_activity_time = models.DateTimeField(null=True, blank=True, help_text="Exact time of last activity")
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Schedule validation
    scheduled_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    classes_scheduled = models.IntegerField(default=0)
    classes_attended = models.IntegerField(default=0)
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Validation and tracking
    validation_method = models.CharField(max_length=20, choices=VALIDATION_METHODS, default='activity_based')
    is_auto_marked = models.BooleanField(default=True)
    location_verified = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    
    # Additional fields
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'teacher', 'date'], name='unique_teacher_attendance_per_org'),
        ]
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.date} - {self.status}"
    
    def calculate_scheduled_hours(self):
        """Calculate total scheduled hours for the day"""
        weekday = self.date.weekday()
        schedules = TeacherSchedule.objects.filter(
            organization=self.organization,
            teacher=self.teacher,
            day_of_week=weekday,
            is_active=True
        )
        
        total_minutes = sum(schedule.duration_minutes for schedule in schedules)
        self.scheduled_hours = round(total_minutes / 60, 2)
        self.classes_scheduled = schedules.count()
        return self.scheduled_hours
    
    def calculate_hours(self):
        """Calculate total hours worked based on real activity times or manual times"""
        if self.first_activity_time and self.last_activity_time:
            # Use real activity times for accurate calculation
            delta = self.last_activity_time - self.first_activity_time
            self.total_hours = round(delta.total_seconds() / 3600, 2)
        elif self.check_in_time and self.check_out_time:
            # Fallback to manual times
            check_in = datetime.combine(self.date, self.check_in_time)
            check_out = datetime.combine(self.date, self.check_out_time)
            delta = check_out - check_in
            self.total_hours = round(delta.total_seconds() / 3600, 2)
        return self.total_hours
    
    def calculate_attendance_percentage(self):
        """Calculate attendance percentage based on scheduled vs attended classes"""
        if self.classes_scheduled > 0:
            self.attendance_percentage = (self.classes_attended / self.classes_scheduled) * 100
        else:
            self.attendance_percentage = 0
        return self.attendance_percentage
    
    def determine_status_advanced(self):
        """Advanced status determination based on schedule compliance and activities"""
        # Calculate scheduled hours and classes
        self.calculate_scheduled_hours()
        
        # Count classes actually attended (where attendance was marked)
        weekday = self.date.weekday()
        scheduled_classes = TeacherSchedule.objects.filter(
            organization=self.organization,
            teacher=self.teacher,
            day_of_week=weekday,
            is_active=True
        )
        
        attended_classes = 0
        for schedule in scheduled_classes:
            # Check if teacher marked attendance for this scheduled class
            session_exists = AttendanceSession.objects.filter(
                organization=self.organization,
                teacher_assignment=schedule.subject_assignment,
                date=self.date,
                start_time__gte=schedule.start_time,
                start_time__lte=schedule.end_time,
                is_completed=True
            ).exists()
            
            if session_exists:
                attended_classes += 1
        
        self.classes_attended = attended_classes
        self.calculate_attendance_percentage()
        
        # Determine status based on comprehensive criteria
        if self.classes_scheduled == 0:
            # No classes scheduled - check for other activities
            if self.has_performed_duties():
                self.status = 'present'
            else:
                self.status = 'absent'
        else:
            # Has scheduled classes
            attendance_rate = self.attendance_percentage
            
            if attendance_rate >= 100:
                # Attended all scheduled classes
                if self.first_activity_time:
                    first_class_time = scheduled_classes.first().start_time if scheduled_classes.exists() else time(9, 0)
                    if self.first_activity_time.time() <= first_class_time:
                        self.status = 'present'
                    elif self.first_activity_time.time() <= time(first_class_time.hour, first_class_time.minute + 30):
                        self.status = 'late'
                    else:
                        self.status = 'late'
                else:
                    self.status = 'present'
            elif attendance_rate >= 75:
                # Attended most classes
                self.status = 'partial'
            elif attendance_rate >= 50:
                # Attended some classes
                self.status = 'half_day'
            elif attendance_rate > 0:
                # Attended few classes
                self.status = 'partial'
            else:
                # Attended no scheduled classes
                if self.has_performed_duties():
                    self.status = 'partial'  # Did some work but missed classes
                else:
                    self.status = 'absent'
        
        return self.status
    
    def has_performed_duties(self):
        """Check if teacher has performed actual duties today"""
        # Check if teacher marked attendance for any of their subjects
        attendance_sessions = AttendanceSession.objects.filter(
            organization=self.organization,
            teacher_assignment__teacher=self.teacher,
            date=self.date,
            is_completed=True
        )
        
        if attendance_sessions.exists():
            return True
        
        # Check for other significant activities
        significant_activities = TeacherActivityLog.objects.filter(
            organization=self.organization,
            teacher=self.teacher,
            timestamp__date=self.date,
            activity_type__in=['mark_attendance', 'create_assignment', 'grade_exam']
        )
        
        return significant_activities.exists()
    
    def get_schedule_compliance_report(self):
        """Get detailed report of schedule compliance"""
        weekday = self.date.weekday()
        scheduled_classes = TeacherSchedule.objects.filter(
            organization=self.organization,
            teacher=self.teacher,
            day_of_week=weekday,
            is_active=True
        ).order_by('start_time')
        
        compliance_report = []
        
        for schedule in scheduled_classes:
            # Check if class was conducted
            session = AttendanceSession.objects.filter(
                organization=self.organization,
                teacher_assignment=schedule.subject_assignment,
                date=self.date,
                start_time__gte=schedule.start_time,
                start_time__lte=schedule.end_time
            ).first()
            
            compliance_report.append({
                'schedule': schedule,
                'session': session,
                'conducted': session is not None and session.is_completed,
                'on_time': session and session.start_time <= schedule.start_time if session else False,
                'delay_minutes': self._calculate_delay(schedule, session) if session else None
            })
        
        return compliance_report
    
    def _calculate_delay(self, schedule, session):
        """Calculate delay in minutes between scheduled and actual time"""
        if not session:
            return None
        
        scheduled_datetime = datetime.combine(self.date, schedule.start_time)
        actual_datetime = datetime.combine(self.date, session.start_time)
        
        if actual_datetime > scheduled_datetime:
            return int((actual_datetime - scheduled_datetime).total_seconds() / 60)
        return 0
    
    def get_missed_classes(self):
        """Get list of classes that were scheduled but not conducted"""
        compliance_report = self.get_schedule_compliance_report()
        return [item for item in compliance_report if not item['conducted']]
    
    def get_performance_score(self):
        """Calculate overall performance score (0-100)"""
        from decimal import Decimal
        
        score = Decimal('0')
        
        # Schedule compliance (40 points)
        if self.classes_scheduled > 0:
            score += (Decimal(str(self.attendance_percentage)) / Decimal('100')) * Decimal('40')
        else:
            score += Decimal('40')  # Full points if no classes scheduled but other duties performed
        
        # Punctuality (20 points)
        compliance_report = self.get_schedule_compliance_report()
        on_time_classes = sum(1 for item in compliance_report if item['on_time'])
        if self.classes_scheduled > 0:
            punctuality_score = (Decimal(str(on_time_classes)) / Decimal(str(self.classes_scheduled))) * Decimal('20')
            score += punctuality_score
        else:
            score += Decimal('20')
        
        # Activity performance (40 points)
        if self.has_performed_duties():
            score += Decimal('40')
        
        return min(100, float(score.quantize(Decimal('0.1'))))
    
    def get_duties_performed(self):
        """Get list of duties performed today"""
        duties = []
        
        # Check attendance sessions
        attendance_sessions = AttendanceSession.objects.filter(
            organization=self.organization,
            teacher_assignment__teacher=self.teacher,
            date=self.date,
            is_completed=True
        ).select_related('teacher_assignment__subject', 'teacher_assignment__class_assigned')
        
        for session in attendance_sessions:
            duties.append({
                'type': 'attendance',
                'description': f"Marked attendance for {session.teacher_assignment.subject.name} - {session.teacher_assignment.class_assigned.name}",
                'time': session.created_at.time() if session.created_at else None
            })
        
        # Check other activities
        activities = TeacherActivityLog.objects.filter(
            organization=self.organization,
            teacher=self.teacher,
            timestamp__date=self.date,
            activity_type__in=['create_assignment', 'grade_exam', 'send_message']
        ).order_by('timestamp')
        
        for activity in activities:
            duties.append({
                'type': activity.activity_type,
                'description': activity.description,
                'time': activity.timestamp.time()
            })
        
        return duties
    
    def get_subjects_not_attended(self):
        """Get list of subjects teacher was supposed to attend but didn't"""
        from academic.models import TeacherSubjectAssignment
        
        # Get all teacher's assignments
        all_assignments = TeacherSubjectAssignment.objects.filter(
            organization=self.organization,
            teacher=self.teacher
        ).select_related('subject', 'class_assigned')
        
        # Get assignments where attendance was marked
        attended_assignments = AttendanceSession.objects.filter(
            organization=self.organization,
            teacher_assignment__teacher=self.teacher,
            date=self.date,
            is_completed=True
        ).values_list('teacher_assignment_id', flat=True)
        
        # Find assignments not attended
        not_attended = []
        for assignment in all_assignments:
            if assignment.id not in attended_assignments:
                not_attended.append({
                    'subject': assignment.subject.name,
                    'class': assignment.class_assigned.name,
                    'assignment_id': assignment.id
                })
        
        return not_attended


class TeacherActivityLog(models.Model):
    """Enhanced log of teacher activities for comprehensive attendance tracking"""
    ACTIVITY_CHOICES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('first_login', 'First Login'),
        ('mark_attendance', 'Mark Student Attendance'),
        ('create_assignment', 'Create Assignment'),
        ('grade_exam', 'Grade Exam'),
        ('send_message', 'Send Message'),
        ('view_report', 'View Report'),
        ('dashboard_access', 'Dashboard Access'),
        ('system_navigation', 'System Navigation'),
        ('classroom_entry', 'Classroom Entry'),
        ('biometric_scan', 'Biometric Verification'),
        ('location_check', 'Location Verification'),
        ('other', 'Other Activity'),
    )
    
    PRIORITY_LEVELS = (
        ('high', 'High Priority'),
        ('medium', 'Medium Priority'),
        ('low', 'Low Priority'),
    )
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='teacher_activity_logs', null=True, blank=True)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='activity_logs')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_CHOICES)
    priority_level = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    description = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Location and device tracking
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    location_lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    is_on_campus = models.BooleanField(default=False)
    
    # Related objects
    related_schedule = models.ForeignKey(TeacherSchedule, on_delete=models.SET_NULL, null=True, blank=True)
    related_session = models.ForeignKey(AttendanceSession, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['teacher', 'timestamp']),
            models.Index(fields=['activity_type', 'timestamp']),
            models.Index(fields=['priority_level', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.activity_type} - {self.timestamp}"
    
    def save(self, *args, **kwargs):
        # Auto-assign priority based on activity type
        if not self.priority_level:
            high_priority_activities = ['mark_attendance', 'create_assignment', 'grade_exam', 'classroom_entry']
            medium_priority_activities = ['send_message', 'view_report', 'biometric_scan']
            
            if self.activity_type in high_priority_activities:
                self.priority_level = 'high'
            elif self.activity_type in medium_priority_activities:
                self.priority_level = 'medium'
            else:
                self.priority_level = 'low'
        
        super().save(*args, **kwargs)


class TeacherLeave(models.Model):
    """Leave requests and approvals for teachers"""
    LEAVE_TYPES = (
        ('sick', 'Sick Leave'),
        ('casual', 'Casual Leave'),
        ('earned', 'Earned Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('emergency', 'Emergency Leave'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='teacher_leaves', null=True, blank=True)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.leave_type} - {self.start_date} to {self.end_date}"
    
    @property
    def total_days(self):
        """Calculate total leave days"""
        return (self.end_date - self.start_date).days + 1
    
    def affects_date(self, date):
        """Check if this leave affects a specific date"""
        return self.start_date <= date <= self.end_date and self.status == 'approved'


class GeofenceLocation(models.Model):
    """Define school campus boundaries for location-based attendance"""
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='geofence_locations', null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    center_lat = models.DecimalField(max_digits=10, decimal_places=8)
    center_lng = models.DecimalField(max_digits=11, decimal_places=8)
    radius_meters = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    def is_within_bounds(self, lat, lng):
        """Check if given coordinates are within the geofence"""
        from math import radians, cos, sin, asin, sqrt
        
        # Haversine formula to calculate distance
        lat1, lng1 = radians(float(self.center_lat)), radians(float(self.center_lng))
        lat2, lng2 = radians(float(lat)), radians(float(lng))
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
        c = 2 * asin(sqrt(a))
        distance_km = 6371 * c  # Earth's radius in kilometers
        distance_meters = distance_km * 1000
        
        return distance_meters <= self.radius_meters