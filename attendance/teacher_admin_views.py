from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date
import csv
from .models import TeacherAttendance, TeacherActivityLog, TeacherLeave, AttendanceSession
from accounts.models import TeacherProfile
from academic.models import TeacherSubjectAssignment
from saas.utils import get_request_organization
from saas.db_router import get_tenant_db

def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'


def get_current_organization(request):
    return get_request_organization(request) or getattr(request.user, 'organization', None)


def scoped_queryset(queryset, request):
    organization = get_current_organization(request)
    if organization and any(field.name == 'organization' for field in queryset.model._meta.fields):
        if get_tenant_db().startswith('tenant_'):
            return queryset
        else:
            return queryset.filter(organization=organization)
    return queryset


def scoped_profile_queryset(queryset, request):
    organization = get_current_organization(request)
    if organization:
        if get_tenant_db().startswith('tenant_'):
            return queryset
        else:
            return queryset.filter(user__organization=organization)
    return queryset

@login_required
@user_passes_test(is_admin)
def teacher_attendance_dashboard(request):
    """Main dashboard for teacher attendance with real activity tracking"""
    today = timezone.now().date()
    
    # Get filter parameters
    selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
    selected_month = request.GET.get('month', today.strftime('%Y-%m'))
    
    try:
        filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        filter_date = today
    
    try:
        year, month = map(int, selected_month.split('-'))
    except:
        year, month = today.year, today.month
    
    # Get all teachers
    all_teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
    total_teachers = all_teachers.count()
    
    # Process each teacher's attendance for the selected date
    enhanced_attendance = []
    present_count = 0
    absent_count = 0
    late_count = 0
    on_leave_count = 0
    
    for teacher in all_teachers:
        # Get or create attendance record
        attendance, created = TeacherAttendance.objects.get_or_create(
            organization=get_current_organization(request),
            teacher=teacher,
            date=filter_date,
            defaults={
                'status': 'absent',
                'is_auto_marked': True
            }
        )
        
        # Update status based on real activities
        attendance.determine_status_advanced()
        attendance.save()
        
        # Count statuses
        if attendance.status in ['present', 'late']:
            if attendance.status == 'present':
                present_count += 1
            else:
                late_count += 1
        elif attendance.status == 'on_leave':
            on_leave_count += 1
        else:
            absent_count += 1
        
        # Get teacher's subject assignments
        subject_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
            teacher=teacher
        ).select_related('subject', 'class_assigned')
        
        # Get attendance sessions for the selected date
        attendance_sessions = scoped_queryset(AttendanceSession.objects.all(), request).filter(
            teacher_assignment__teacher=teacher,
            date=filter_date
        ).select_related('teacher_assignment__subject', 'teacher_assignment__class_assigned')
        
        # Get duties performed and subjects not attended
        duties_performed = attendance.get_duties_performed()
        subjects_not_attended = attendance.get_subjects_not_attended()
        
        enhanced_attendance.append({
            'attendance': attendance,
            'subject_assignments': subject_assignments,
            'attendance_sessions': attendance_sessions,
            'subjects_taught_today': attendance_sessions.count(),
            'classes_attended': attendance_sessions.filter(is_completed=True).count(),
            'duties_performed': duties_performed,
            'subjects_not_attended': subjects_not_attended,
            'has_real_activities': attendance.has_performed_duties(),
            'real_check_in': attendance.first_activity_time.time() if attendance.first_activity_time else None,
            'real_check_out': attendance.last_activity_time.time() if attendance.last_activity_time else None,
        })
    
    # Calculate attendance percentage
    attendance_percentage = (present_count / total_teachers * 100) if total_teachers > 0 else 0
    
    # Monthly statistics
    monthly_attendance = scoped_queryset(TeacherAttendance.objects.all(), request).filter(
        date__year=year,
        date__month=month
    )
    
    monthly_stats = {
        'total_working_days': monthly_attendance.values('date').distinct().count(),
        'avg_attendance': monthly_attendance.filter(status__in=['present', 'late']).count() / total_teachers if total_teachers > 0 else 0,
        'total_late_instances': monthly_attendance.filter(status='late').count(),
        'total_leaves': monthly_attendance.filter(status='on_leave').count(),
    }
    
    # Recent activity
    recent_activities = scoped_queryset(TeacherActivityLog.objects.select_related('teacher__user'), request).order_by('-timestamp')[:10]
    
    # Teachers currently online (active in last 30 minutes)
    thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
    online_teachers = scoped_queryset(TeacherActivityLog.objects.all(), request).filter(
        timestamp__gte=thirty_minutes_ago
    ).values('teacher').distinct().count()
    
    context = {
        'today': today,
        'selected_date': selected_date,
        'selected_month': selected_month,
        'filter_date': filter_date,
        'total_teachers': total_teachers,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'on_leave_count': on_leave_count,
        'attendance_percentage': round(attendance_percentage, 1),
        'monthly_stats': monthly_stats,
        'recent_activities': recent_activities,
        'online_teachers': online_teachers,
        'enhanced_attendance': enhanced_attendance,
    }
    
    return render(request, 'attendance/teacher_attendance_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def teacher_attendance_reports(request):
    """Detailed teacher attendance reports with subject information"""
    
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
    
    # Limit to 100 records for performance
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
    
    # Handle CSV export
    if request.GET.get('export') == 'csv':
        return export_enhanced_teacher_attendance(enhanced_records)
    
    context = {
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
    }
    
    return render(request, 'admin/attendance/teacher_attendance_reports.html', context)

@login_required
@user_passes_test(is_admin)
def export_teacher_attendance(request):
    """Export teacher attendance to CSV"""
    
    # Get filter parameters (same as reports view)
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
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teacher_attendance.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Teacher Name', 'Date', 'Status', 'Check In', 'Check Out', 
        'Total Hours', 'IP Address', 'Remarks'
    ])
    
    for record in attendance_records:
        writer.writerow([
            record.teacher.user.get_full_name(),
            record.date,
            record.get_status_display(),
            record.check_in_time or '',
            record.check_out_time or '',
            record.total_hours,
            record.ip_address or '',
            record.remarks
        ])
    
    return response

def export_enhanced_teacher_attendance(enhanced_records):
    """Export enhanced teacher attendance to CSV"""
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="enhanced_teacher_attendance.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Teacher Name', 'Date', 'Status', 'Check In', 'Check Out', 
        'Total Hours', 'Subjects Assigned', 'Classes Conducted', 'Total Sessions',
        'Auto Marked', 'Remarks'
    ])
    
    for item in enhanced_records:
        record = item['record']
        subjects = ', '.join([f"{sa.subject.name} ({sa.class_assigned})" for sa in item['subject_assignments']])
        
        writer.writerow([
            record.teacher.user.get_full_name(),
            record.date,
            record.get_status_display(),
            record.check_in_time or '',
            record.check_out_time or '',
            record.total_hours,
            subjects,
            item['classes_conducted'],
            item['total_sessions'],
            'Yes' if record.is_auto_marked else 'No',
            record.remarks
        ])
    
    return response

@login_required
@user_passes_test(is_admin)
def teacher_activity_logs(request):
    """View teacher activity logs"""
    
    teacher_id = request.GET.get('teacher')
    activity_type = request.GET.get('activity_type')
    date_filter = request.GET.get('date')
    
    # Base queryset
    activities = scoped_queryset(TeacherActivityLog.objects.select_related('teacher__user'), request).order_by('-timestamp')
    
    # Apply filters
    if teacher_id:
        activities = activities.filter(teacher_id=teacher_id)
    
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date=filter_date)
        except:
            pass
    
    # Pagination
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get teachers and activity types for filters
    teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
    activity_types = TeacherActivityLog.ACTIVITY_CHOICES
    
    context = {
        'page_obj': page_obj,
        'teachers': teachers,
        'activity_types': activity_types,
        'selected_teacher': teacher_id,
        'selected_activity_type': activity_type,
        'selected_date': date_filter,
    }
    
    return render(request, 'attendance/teacher_activity_logs.html', context)

@login_required
@user_passes_test(is_admin)
def teacher_detailed_activities(request):
    """Detailed breakdown of teacher activities by category with timestamps"""
    today = timezone.now().date()
    
    # Get filter parameters
    selected_teacher_id = request.GET.get('teacher')
    selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
    
    try:
        filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        filter_date = today
    
    # Get all teachers for dropdown
    teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
    
    context = {
        'teachers': teachers,
        'selected_date': selected_date,
        'filter_date': filter_date,
    }
    
    if selected_teacher_id:
        try:
            selected_teacher = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).get(id=selected_teacher_id)
            context['selected_teacher'] = selected_teacher
            context['selected_teacher_id'] = int(selected_teacher_id)
            
            # Get attendance record
            try:
                attendance_record = scoped_queryset(TeacherAttendance.objects.all(), request).get(
                    teacher=selected_teacher,
                    date=filter_date
                )
                context['attendance_record'] = attendance_record
            except TeacherAttendance.DoesNotExist:
                context['attendance_record'] = None
            
            # Get all activities for the teacher on the selected date
            all_activities = scoped_queryset(TeacherActivityLog.objects.all(), request).filter(
                teacher=selected_teacher,
                timestamp__date=filter_date
            ).order_by('-timestamp')
            
            # Categorize activities
            attendance_activities = all_activities.filter(activity_type='mark_attendance')
            assignment_activities = all_activities.filter(activity_type='create_assignment')
            grading_activities = all_activities.filter(activity_type='grade_exam')
            communication_activities = all_activities.filter(activity_type='send_message')
            
            # Activity counts
            context.update({
                'attendance_count': attendance_activities.count(),
                'assignment_count': assignment_activities.count(),
                'grading_count': grading_activities.count(),
                'message_count': communication_activities.count(),
                'total_activities': all_activities.count(),
                
                'attendance_activities': attendance_activities,
                'assignment_activities': assignment_activities,
                'grading_activities': grading_activities,
                'communication_activities': communication_activities,
            })
            
            # Calculate productivity metrics
            educational_activities = attendance_activities.count() + assignment_activities.count() + grading_activities.count()
            total_activities_count = all_activities.count()
            
            if total_activities_count > 0:
                educational_percentage = (educational_activities / total_activities_count) * 100
            else:
                educational_percentage = 0
            
            context['educational_percentage'] = educational_percentage
            
            # Calculate duties completed vs missed
            if attendance_record:
                duties_performed = attendance_record.get_duties_performed()
                subjects_not_attended = attendance_record.get_subjects_not_attended()
                
                context['duties_completed'] = len(duties_performed)
                context['duties_missed'] = len(subjects_not_attended)
            else:
                context['duties_completed'] = 0
                context['duties_missed'] = 0
                
        except TeacherProfile.DoesNotExist:
            pass
    
    return render(request, 'attendance/teacher_detailed_activities.html', context)

@login_required
@user_passes_test(is_admin)
def teacher_activity_timeline(request):
    """Detailed timeline view of teacher activities with exact timestamps"""
    today = timezone.now().date()
    
    # Get filter parameters
    selected_teacher = request.GET.get('teacher')
    selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
    selected_activity_type = request.GET.get('activity_type')
    
    try:
        filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        filter_date = today
    
    # Base queryset for activities
    activities = scoped_queryset(TeacherActivityLog.objects.select_related('teacher__user'), request).filter(
        timestamp__date=filter_date
    ).order_by('-timestamp')
    
    # Apply filters
    if selected_teacher:
        activities = activities.filter(teacher_id=selected_teacher)
    
    if selected_activity_type:
        activities = activities.filter(activity_type=selected_activity_type)
    
    # Statistics
    total_activities = activities.count()
    attendance_activities = activities.filter(activity_type='mark_attendance').count()
    assignment_activities = activities.filter(activity_type='create_assignment').count()
    
    # Active teachers (last 30 minutes)
    thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
    active_teachers = scoped_queryset(TeacherActivityLog.objects.all(), request).filter(
        timestamp__gte=thirty_minutes_ago
    ).values('teacher').distinct().count()
    
    # Pagination
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all teachers for filter dropdown
    teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
    
    context = {
        'activities': page_obj,
        'teachers': teachers,
        'activity_types': TeacherActivityLog.ACTIVITY_CHOICES,
        'selected_teacher': selected_teacher,
        'selected_date': selected_date,
        'selected_activity_type': selected_activity_type,
        'filter_date': filter_date,
        'total_activities': total_activities,
        'attendance_activities': attendance_activities,
        'assignment_activities': assignment_activities,
        'active_teachers': active_teachers,
    }
    
    return render(request, 'attendance/teacher_activity_timeline.html', context)

@login_required
@user_passes_test(is_admin)
def manual_teacher_attendance(request):
    """Manually mark teacher attendance"""
    
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        date_str = request.POST.get('date')
        status = request.POST.get('status')
        check_in_time = request.POST.get('check_in_time')
        check_out_time = request.POST.get('check_out_time')
        remarks = request.POST.get('remarks', '')
        
        try:
            teacher = scoped_profile_queryset(TeacherProfile.objects.all(), request).get(id=teacher_id)
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Create or update attendance record
            attendance, created = TeacherAttendance.objects.get_or_create(
                organization=get_current_organization(request),
                teacher=teacher,
                date=attendance_date,
                defaults={
                    'status': status,
                    'check_in_time': check_in_time if check_in_time else None,
                    'check_out_time': check_out_time if check_out_time else None,
                    'remarks': remarks,
                    'is_auto_marked': False
                }
            )
            
            if not created:
                attendance.status = status
                attendance.check_in_time = check_in_time if check_in_time else None
                attendance.check_out_time = check_out_time if check_out_time else None
                attendance.remarks = remarks
                attendance.is_auto_marked = False
                attendance.save()
            
            attendance.calculate_hours()
            attendance.save()
            
            messages.success(request, f'Attendance marked successfully for {teacher.user.get_full_name()}')
            
        except Exception as e:
            messages.error(request, f'Error marking attendance: {str(e)}')
        
        return redirect('attendance:manual_teacher_attendance')
    
    # GET request - show form
    teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
    today = timezone.now().date()
    
    context = {
        'teachers': teachers,
        'today': today,
        'status_choices': TeacherAttendance.STATUS_CHOICES,
    }
    
    return render(request, 'attendance/manual_teacher_attendance.html', context)