from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TeacherAttendance, TeacherActivityLog, AttendanceSession
from accounts.models import TeacherProfile
from academic.models import TeacherSubjectAssignment
from saas.utils import get_request_organization


def get_current_organization(request):
    return get_request_organization(request) or getattr(request.user, 'organization', None)


def scoped_queryset(queryset, request):
    if getattr(request.user, 'is_superuser', False):
        return queryset
    organization = get_current_organization(request)
    if organization and any(field.name == 'organization' for field in queryset.model._meta.fields):
        return queryset.filter(organization=organization)
    return queryset


def scoped_profile_queryset(queryset, request):
    if getattr(request.user, 'is_superuser', False):
        return queryset
    organization = get_current_organization(request)
    if organization:
        return queryset.filter(user__organization=organization)
    return queryset

class TeacherAttendanceAdminView:
    """Custom admin view for teacher attendance dashboard"""
    
    def get_urls(self):
        urls = [
            path('teacher-attendance-dashboard/', 
                 self.admin_site.admin_view(self.teacher_attendance_dashboard_view),
                 name='attendance_teacherattendance_dashboard'),
            path('teacher-attendance-reports/', 
                 self.admin_site.admin_view(self.teacher_attendance_reports_view),
                 name='attendance_teacherattendance_reports'),
        ]
        return urls
    
    def teacher_attendance_dashboard_view(self, request):
        """Teacher attendance dashboard in admin"""
        today = timezone.now().date()
        
        # Get filter parameters
        selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
        
        try:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except:
            filter_date = today
        
        # Today's attendance summary
        total_teachers = scoped_profile_queryset(TeacherProfile.objects.all(), request).count()
        today_attendance = scoped_queryset(TeacherAttendance.objects.all(), request).filter(date=filter_date)
        
        present_count = today_attendance.filter(status__in=['present', 'late']).count()
        absent_count = today_attendance.filter(status='absent').count()
        late_count = today_attendance.filter(status='late').count()
        on_leave_count = today_attendance.filter(status='on_leave').count()
        
        # Calculate attendance percentage
        attendance_percentage = (present_count / total_teachers * 100) if total_teachers > 0 else 0
        
        # Recent activity
        recent_activities = scoped_queryset(TeacherActivityLog.objects.select_related('teacher__user'), request).order_by('-timestamp')[:10]
        
        # Teachers currently online (active in last 30 minutes)
        thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
        online_teachers = scoped_queryset(TeacherActivityLog.objects.all(), request).filter(
            timestamp__gte=thirty_minutes_ago
        ).values('teacher').distinct().count()
        
        # Detailed attendance for today with subject information
        detailed_attendance = scoped_queryset(TeacherAttendance.objects.all(), request).filter(
            date=filter_date
        ).select_related('teacher__user').order_by('teacher__user__first_name')
        
        # Add subject assignments and attendance sessions for each teacher
        enhanced_attendance = []
        for attendance in detailed_attendance:
            # Get teacher's subject assignments
            subject_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
                teacher=attendance.teacher
            ).select_related('subject', 'class_assigned')
            
            # Get attendance sessions for today
            attendance_sessions = scoped_queryset(AttendanceSession.objects.all(), request).filter(
                teacher_assignment__teacher=attendance.teacher,
                date=filter_date
            ).select_related('teacher_assignment__subject', 'teacher_assignment__class_assigned')
            
            enhanced_attendance.append({
                'attendance': attendance,
                'subject_assignments': subject_assignments,
                'attendance_sessions': attendance_sessions,
                'subjects_taught_today': attendance_sessions.count(),
                'classes_attended': attendance_sessions.filter(is_completed=True).count()
            })
        
        # Teachers without attendance record for today
        teachers_with_attendance = detailed_attendance.values_list('teacher_id', flat=True)
        teachers_without_attendance_list = []
        for teacher in scoped_profile_queryset(TeacherProfile.objects.all(), request).exclude(id__in=teachers_with_attendance).select_related('user'):
            # Get their subject assignments
            subject_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
                teacher=teacher
            ).select_related('subject', 'class_assigned')
            
            teachers_without_attendance_list.append({
                'teacher': teacher,
                'subject_assignments': subject_assignments
            })
        
        context = {
            'title': 'Teacher Attendance Dashboard',
            'today': today,
            'selected_date': selected_date,
            'filter_date': filter_date,
            'total_teachers': total_teachers,
            'present_count': present_count,
            'absent_count': absent_count,
            'late_count': late_count,
            'on_leave_count': on_leave_count,
            'attendance_percentage': round(attendance_percentage, 1),
            'recent_activities': recent_activities,
            'online_teachers': online_teachers,
            'enhanced_attendance': enhanced_attendance,
            'teachers_without_attendance': teachers_without_attendance_list,
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        
        return render(request, 'admin/attendance/teacher_attendance_dashboard.html', context)
    
    def teacher_attendance_reports_view(self, request):
        """Teacher attendance reports in admin"""
        
        # Get filter parameters
        teacher_id = request.GET.get('teacher')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        status_filter = request.GET.get('status')
        
        # Base queryset
        attendance_records = scoped_queryset(TeacherAttendance.objects.select_related('teacher__user'), request).order_by('-date')
        
        # Apply filters
        if teacher_id:
            attendance_records = attendance_records.filter(teacher_id=teacher_id)
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                attendance_records = attendance_records.filter(date__gte=start_date_obj)
            except:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                attendance_records = attendance_records.filter(date__lte=end_date_obj)
            except:
                pass
        
        if status_filter:
            attendance_records = attendance_records.filter(status=status_filter)
        
        # Limit to recent records for performance
        attendance_records = attendance_records[:100]
        
        # Enhance records with subject information
        enhanced_records = []
        for record in attendance_records:
            # Get teacher's subject assignments
            subject_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
                teacher=record.teacher
            ).select_related('subject', 'class_assigned')
            
            # Get attendance sessions for that date
            attendance_sessions = scoped_queryset(AttendanceSession.objects.all(), request).filter(
                teacher_assignment__teacher=record.teacher,
                date=record.date
            ).select_related('teacher_assignment__subject', 'teacher_assignment__class_assigned')
            
            enhanced_records.append({
                'record': record,
                'subject_assignments': subject_assignments,
                'attendance_sessions': attendance_sessions,
                'classes_conducted': attendance_sessions.filter(is_completed=True).count(),
                'total_sessions': attendance_sessions.count()
            })
        
        # Summary statistics
        total_records = len(enhanced_records)
        present_records = len([r for r in enhanced_records if r['record'].status in ['present', 'late']])
        absent_records = len([r for r in enhanced_records if r['record'].status == 'absent'])
        late_records = len([r for r in enhanced_records if r['record'].status == 'late'])
        
        # Get all teachers for filter dropdown
        teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
        
        context = {
            'title': 'Teacher Attendance Reports',
            'enhanced_records': enhanced_records,
            'teachers': teachers,
            'selected_teacher': teacher_id,
            'start_date': start_date,
            'end_date': end_date,
            'status_filter': status_filter,
            'total_records': total_records,
            'present_records': present_records,
            'absent_records': absent_records,
            'late_records': late_records,
            'attendance_percentage': (present_records / total_records * 100) if total_records > 0 else 0,
            'status_choices': TeacherAttendance.STATUS_CHOICES,
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        
        return render(request, 'admin/attendance/teacher_attendance_reports.html', context)


# Extend the existing TeacherAttendanceAdmin to include custom views
class TeacherAttendanceAdminExtended(admin.ModelAdmin, TeacherAttendanceAdminView):
    list_display = ['get_teacher_name', 'date', 'get_status_badge', 'check_in_time', 'check_out_time', 'total_hours', 'is_auto_marked']
    list_filter = ['status', 'date', 'is_auto_marked']
    search_fields = ['teacher__user__username', 'teacher__user__first_name', 'teacher__user__last_name']
    date_hierarchy = 'date'
    readonly_fields = ['total_hours', 'created_at', 'updated_at']
    ordering = ['-date', 'teacher__user__first_name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher__user')
    
    def get_teacher_name(self, obj):
        return obj.teacher.user.get_full_name() or obj.teacher.user.username
    get_teacher_name.short_description = 'Teacher'
    get_teacher_name.admin_order_field = 'teacher__user__first_name'
    
    def get_status_badge(self, obj):
        colors = {
            'present': '#28a745',
            'absent': '#dc3545',
            'late': '#ffc107',
            'half_day': '#fd7e14',
            'on_leave': '#17a2b8'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = 'Status'
    get_status_badge.admin_order_field = 'status'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = TeacherAttendanceAdminView.get_urls(self)
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """Add custom buttons to the changelist view"""
        extra_context = extra_context or {}
        extra_context['custom_buttons'] = [
            {
                'url': reverse('admin:attendance_teacherattendance_dashboard'),
                'title': 'Teacher Attendance Dashboard',
                'icon': 'fas fa-tachometer-alt',
                'class': 'btn-primary'
            },
            {
                'url': reverse('admin:attendance_teacherattendance_reports'),
                'title': 'Detailed Reports',
                'icon': 'fas fa-chart-bar',
                'class': 'btn-info'
            }
        ]
        return super().changelist_view(request, extra_context)