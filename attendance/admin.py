from django.contrib import admin
from django.utils.html import format_html
from .models import AttendanceSession, AttendanceRecord, AttendanceSummary


class CourseClassFilter(admin.SimpleListFilter):
    """Custom filter to show Course - Class combinations"""
    title = 'Course and Class'
    parameter_name = 'course_class'

    def lookups(self, request, model_admin):
        """Return unique course-class combinations"""
        from academic.models import Class
        classes = Class.objects.select_related('course').order_by('course__name', 'name')
        return [(f"{c.course.id}_{c.id}", f"{c.course.name} - {c.name}") for c in classes]

    def queryset(self, request, queryset):
        """Filter queryset based on selected course-class"""
        if self.value():
            try:
                course_id, class_id = self.value().split('_')
                return queryset.filter(
                    session__teacher_assignment__class_assigned__course__id=course_id,
                    session__teacher_assignment__class_assigned__id=class_id
                )
            except ValueError:
                pass
        return queryset


class SubjectClassFilter(admin.SimpleListFilter):
    """Custom filter to show Subject - Class combinations"""
    title = 'Subject and Class'
    parameter_name = 'subject_class'

    def lookups(self, request, model_admin):
        """Return unique subject-class combinations from teacher assignments"""
        from academic.models import TeacherSubjectAssignment
        assignments = TeacherSubjectAssignment.objects.select_related(
            'subject', 'class_assigned', 'class_assigned__course'
        ).order_by('class_assigned__course__name', 'class_assigned__name', 'subject__name')
        
        seen = set()
        lookups = []
        for assignment in assignments:
            key = f"{assignment.subject.id}_{assignment.class_assigned.id}"
            if key not in seen:
                seen.add(key)
                lookups.append((
                    key,
                    f"{assignment.class_assigned.course.name} - {assignment.class_assigned.name} - {assignment.subject.name}"
                ))
        return lookups

    def queryset(self, request, queryset):
        """Filter queryset based on selected subject-class"""
        if self.value():
            try:
                subject_id, class_id = self.value().split('_')
                return queryset.filter(
                    session__teacher_assignment__subject__id=subject_id,
                    session__teacher_assignment__class_assigned__id=class_id
                )
            except ValueError:
                pass
        return queryset

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('get_subject', 'get_class', 'get_course', 'date', 'start_time', 'end_time', 'is_completed', 'get_teacher', 'get_student_count')
    search_fields = (
        'teacher_assignment__teacher__user__username',
        'teacher_assignment__teacher__user__first_name',
        'teacher_assignment__teacher__user__last_name',
        'teacher_assignment__subject__name',
        'teacher_assignment__class_assigned__name',
        'teacher_assignment__class_assigned__course__name'
    )
    list_filter = (
        CourseClassFilter,
        SubjectClassFilter,
        'teacher_assignment__class_assigned__course',
        'teacher_assignment__subject',
        'teacher_assignment__class_assigned',
        'date',
        'is_completed'
    )
    date_hierarchy = 'date'
    ordering = ('-date', 'teacher_assignment__class_assigned__course', 'teacher_assignment__subject')
    
    def get_subject(self, obj):
        return obj.teacher_assignment.subject.name
    get_subject.short_description = 'Subject'
    get_subject.admin_order_field = 'teacher_assignment__subject__name'
    
    def get_class(self, obj):
        return obj.teacher_assignment.class_assigned.name
    get_class.short_description = 'Class'
    get_class.admin_order_field = 'teacher_assignment__class_assigned__name'
    
    def get_course(self, obj):
        return obj.teacher_assignment.class_assigned.course.name
    get_course.short_description = 'Course'
    get_course.admin_order_field = 'teacher_assignment__class_assigned__course__name'
    
    def get_teacher(self, obj):
        return obj.teacher_assignment.teacher.user.get_full_name()
    get_teacher.short_description = 'Teacher'
    get_teacher.admin_order_field = 'teacher_assignment__teacher__user__last_name'
    
    def get_student_count(self, obj):
        count = obj.attendancerecord_set.count()
        return format_html(
            '<span style="background: #417690; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            count
        )
    get_student_count.short_description = 'Students'

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    change_list_template = 'admin/attendance/attendancerecord_change_list.html'
    
    list_display = (
        'get_student_name',
        'get_student_id',
        'get_subject',
        'get_course',
        'get_class',
        'get_session_date',
        'get_status_badge',
        'marked_at'
    )
    search_fields = (
        'student__user__username',
        'student__user__first_name',
        'student__user__last_name',
        'student__student_id',
        'session__teacher_assignment__subject__name',
        'session__teacher_assignment__class_assigned__name',
        'session__teacher_assignment__class_assigned__course__name'
    )
    list_filter = (
        CourseClassFilter,
        SubjectClassFilter,
        'session__teacher_assignment__class_assigned__course',
        'session__teacher_assignment__subject',
        'session__teacher_assignment__class_assigned',
        'status',
        'session__date',
        'marked_at'
    )
    date_hierarchy = 'session__date'
    ordering = (
        '-session__date',
        'session__teacher_assignment__class_assigned__course',
        'session__teacher_assignment__subject',
        'student__user__last_name'
    )
    list_per_page = 50
    
    def changelist_view(self, request, extra_context=None):
        """Add grouped data to the changelist context"""
        extra_context = extra_context or {}
        
        # Get the filtered queryset
        response = super().changelist_view(request, extra_context)
        
        # If it's a TemplateResponse, add our custom context
        if hasattr(response, 'context_data'):
            cl = response.context_data['cl']
            queryset = cl.queryset
            
            # Group records by class and course
            from collections import defaultdict
            grouped_records = defaultdict(lambda: defaultdict(list))
            
            for record in queryset:
                try:
                    course_name = record.session.teacher_assignment.class_assigned.course.name
                    class_name = record.session.teacher_assignment.class_assigned.name
                    subject_name = record.session.teacher_assignment.subject.name
                    
                    # Create a detailed key for the class/subject combination
                    class_key = f"{class_name} - {subject_name}"
                    grouped_records[course_name][class_key].append(record)
                except AttributeError:
                    # Skip records with missing relationships
                    continue
            
            # Convert to regular dict for template
            final_grouped = {}
            for course_name, classes in grouped_records.items():
                final_grouped[course_name] = dict(classes)
            
            response.context_data['grouped_records'] = final_grouped
            response.context_data['show_grouped_view'] = len(final_grouped) > 0
        
        return response
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Session Information', {
            'fields': ('session',),
            'description': 'The class session this attendance record belongs to'
        }),
        ('Attendance Details', {
            'fields': ('status', 'remarks')
        }),
    )
    
    def get_student_name(self, obj):
        return obj.student.user.get_full_name()
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'student__user__last_name'
    
    def get_student_id(self, obj):
        return obj.student.student_id
    get_student_id.short_description = 'Student ID'
    get_student_id.admin_order_field = 'student__student_id'
    
    def get_subject(self, obj):
        return obj.session.teacher_assignment.subject.name
    get_subject.short_description = 'Subject'
    get_subject.admin_order_field = 'session__teacher_assignment__subject__name'
    
    def get_course(self, obj):
        return obj.session.teacher_assignment.class_assigned.course.name
    get_course.short_description = 'Course'
    get_course.admin_order_field = 'session__teacher_assignment__class_assigned__course__name'
    
    def get_class(self, obj):
        return obj.session.teacher_assignment.class_assigned.name
    get_class.short_description = 'Class'
    get_class.admin_order_field = 'session__teacher_assignment__class_assigned__name'
    
    def get_session_date(self, obj):
        return obj.session.date
    get_session_date.short_description = 'Session Date'
    get_session_date.admin_order_field = 'session__date'
    
    def get_status_badge(self, obj):
        colors = {
            'present': '#28a745',
            'absent': '#dc3545',
            'late': '#ffc107',
            'excused': '#17a2b8'
        }
        color = colors.get(obj.status.lower(), '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'

@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = (
        'get_student_name',
        'get_student_id',
        'subject',
        'get_course',
        'class_enrolled',
        'month',
        'year',
        'total_sessions',
        'sessions_attended',
        'get_attendance_percentage'
    )
    search_fields = (
        'student__user__username',
        'student__user__first_name',
        'student__user__last_name',
        'student__student_id',
        'subject__name',
        'class_enrolled__name',
        'class_enrolled__course__name'
    )
    list_filter = (
        'class_enrolled__course',
        'subject',
        'class_enrolled',
        'year',
        'month'
    )
    ordering = ('-year', '-month', 'class_enrolled__course', 'subject', 'student__user__last_name')
    
    def get_student_name(self, obj):
        return obj.student.user.get_full_name()
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'student__user__last_name'
    
    def get_student_id(self, obj):
        return obj.student.student_id
    get_student_id.short_description = 'Student ID'
    get_student_id.admin_order_field = 'student__student_id'
    
    def get_course(self, obj):
        return obj.class_enrolled.course.name
    get_course.short_description = 'Course'
    get_course.admin_order_field = 'class_enrolled__course__name'
    
    def get_attendance_percentage(self, obj):
        percentage = obj.attendance_percentage
        if percentage >= 75:
            color = '#28a745'
        elif percentage >= 60:
            color = '#ffc107'
        else:
            color = '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.2f}%</span>',
            color,
            percentage
        )
    get_attendance_percentage.short_description = 'Attendance %'
    get_attendance_percentage.admin_order_field = 'attendance_percentage'

# Teacher Attendance Admin
from .models import TeacherAttendance, TeacherActivityLog, TeacherLeave
from .admin_views import TeacherAttendanceAdminExtended

# Unregister the old TeacherAttendance admin if it exists
try:
    admin.site.unregister(TeacherAttendance)
except admin.sites.NotRegistered:
    pass

# Register with extended functionality
admin.site.register(TeacherAttendance, TeacherAttendanceAdminExtended)

@admin.register(TeacherActivityLog)
class TeacherActivityLogAdmin(admin.ModelAdmin):
    list_display = ['get_teacher_name', 'activity_type', 'description', 'timestamp', 'ip_address']
    list_filter = ['activity_type', 'timestamp']
    search_fields = ['teacher__user__username', 'teacher__user__first_name', 'teacher__user__last_name', 'description']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    list_per_page = 50
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__user')
    
    def get_teacher_name(self, obj):
        return obj.teacher.user.get_full_name() or obj.teacher.user.username
    get_teacher_name.short_description = 'Teacher'
    get_teacher_name.admin_order_field = 'teacher__user__first_name'

@admin.register(TeacherLeave)
class TeacherLeaveAdmin(admin.ModelAdmin):
    list_display = ['get_teacher_name', 'leave_type', 'start_date', 'end_date', 'get_status_badge', 'total_days', 'approved_by']
    list_filter = ['leave_type', 'status', 'start_date']
    search_fields = ['teacher__user__username', 'teacher__user__first_name', 'teacher__user__last_name', 'reason']
    date_hierarchy = 'start_date'
    readonly_fields = ['total_days', 'created_at', 'updated_at']
    ordering = ['-start_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__user', 'approved_by')
    
    def get_teacher_name(self, obj):
        return obj.teacher.user.get_full_name() or obj.teacher.user.username
    get_teacher_name.short_description = 'Teacher'
    get_teacher_name.admin_order_field = 'teacher__user__first_name'
    
    def get_status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'cancelled': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'