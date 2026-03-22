from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime
from .models import AttendanceSession, AttendanceRecord, AttendanceSummary, TeacherAttendance
from .forms import AttendanceSessionForm, QuickAttendanceForm, AttendanceFilterForm, AttendanceRecordFormSet
from academic.models import TeacherSubjectAssignment, StudentEnrollment, Class
from accounts.models import StudentProfile, TeacherProfile
from saas.utils import get_request_organization
from saas.db_router import get_tenant_db

def is_teacher_or_admin(user):
    return user.is_authenticated and user.user_type in ['admin', 'teacher']


def get_current_organization(request):
    return get_request_organization(request) or getattr(request.user, 'organization', None)


def scoped_queryset(queryset, request):
    organization = get_current_organization(request)
    if organization and any(field.name == 'organization' for field in queryset.model._meta.fields):
        # In tenant DBs, organization_id is often NULL; avoid filtering it out.
        if get_tenant_db().startswith('tenant_'):
            return queryset
        return queryset.filter(organization=organization)
    return queryset


def scoped_profile_queryset(queryset, request):
    organization = get_current_organization(request)
    if organization:
        if get_tenant_db().startswith('tenant_'):
            return queryset
        return queryset.filter(user__organization=organization)
    return queryset


def assign_organization(instance, request):
    organization = get_current_organization(request)
    if organization and hasattr(instance, 'organization_id') and instance.organization_id is None:
        instance.organization = organization
    return instance

@login_required
@user_passes_test(is_teacher_or_admin)
def get_students_for_assignment(request):
    """AJAX view to get students for a specific teacher assignment"""
    if request.method == 'GET':
        assignment_id = request.GET.get('assignment_id')
        
        if not assignment_id:
            return JsonResponse({'error': 'Assignment ID is required'}, status=400)
        
        try:
            assignment = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).get(
                id=assignment_id,
                teacher=request.user.teacher_profile
            )
            
            # Get students enrolled in this class
            enrollments = scoped_queryset(StudentEnrollment.objects.all(), request).filter(
                class_enrolled=assignment.class_assigned,
                is_active=True
            ).select_related('student__user')
            
            students_data = []
            for enrollment in enrollments:
                # Get student name with fallback to username
                student_name = enrollment.student.user.get_full_name()
                if not student_name.strip():
                    student_name = enrollment.student.user.username
                
                students_data.append({
                    'id': enrollment.student.id,
                    'name': student_name,
                    'student_id': enrollment.student.student_id,
                    'email': enrollment.student.user.email
                })
            
            return JsonResponse({
                'students': students_data,
                'assignment': {
                    'id': assignment.id,
                    'subject': assignment.subject.name,
                    'class': assignment.class_assigned.name
                }
            })
            
        except TeacherSubjectAssignment.DoesNotExist:
            return JsonResponse({'error': 'Assignment not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
@user_passes_test(is_teacher_or_admin)
def save_attendance_ajax(request):
    """AJAX view to save attendance data"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            assignment_id = data.get('assignment_id')
            date = data.get('date')
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            topic_covered = data.get('topic_covered', '')
            attendance_data = data.get('attendance_data', [])
            
            if not all([assignment_id, date, start_time, end_time]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)
            
            # Get the teacher assignment
            assignment = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).get(
                id=assignment_id,
                teacher=request.user.teacher_profile
            )
            
            # Create or get attendance session
            session, created = AttendanceSession.objects.get_or_create(
                organization=get_current_organization(request),
                teacher_assignment=assignment,
                date=date,
                start_time=start_time,
                defaults={
                    'end_time': end_time,
                    'topic_covered': topic_covered,
                    'is_completed': True
                }
            )
            
            if not created:
                # Update existing session
                session.end_time = end_time
                session.topic_covered = topic_covered
                session.is_completed = True
                session.save()
            
            # Save attendance records
            saved_count = 0
            for record_data in attendance_data:
                student_id = record_data.get('student_id')
                status = record_data.get('status')
                remarks = record_data.get('remarks', '')
                
                if student_id and status:
                    try:
                        student = scoped_profile_queryset(StudentProfile.objects.all(), request).get(id=student_id)
                        
                        # Create or update attendance record
                        attendance_record, created = AttendanceRecord.objects.get_or_create(
                            organization=get_current_organization(request),
                            session=session,
                            student=student,
                            defaults={
                                'status': status,
                                'remarks': remarks
                            }
                        )
                        
                        if not created:
                            attendance_record.status = status
                            attendance_record.remarks = remarks
                            attendance_record.save()
                        
                        saved_count += 1
                        
                    except StudentProfile.DoesNotExist:
                        continue
            
            return JsonResponse({
                'success': True,
                'message': f'Attendance saved successfully for {saved_count} students!',
                'session_id': session.id
            })
            
        except TeacherSubjectAssignment.DoesNotExist:
            return JsonResponse({'error': 'Assignment not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required
@user_passes_test(is_teacher_or_admin)
def mark_attendance(request):
    """Main attendance marking view for teachers"""
    
    # Check if user is admin or has teacher profile
    if request.user.user_type == 'admin':
        # Admin users should be redirected to a selection page or shown all teachers
        messages.warning(request, 'Please access attendance marking through a specific teacher account or select a teacher.')
        return redirect('accounts:admin_user_list')
    
    # Check if teacher profile exists
    if not hasattr(request.user, 'teacher_profile'):
        messages.error(request, 'Teacher profile not found. Please contact the administrator.')
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        if 'create_session' in request.POST:
            # Create new attendance session
            form = QuickAttendanceForm(request.POST, teacher=request.user.teacher_profile)
            if form.is_valid():
                # Create attendance session
                session = AttendanceSession.objects.create(
                    organization=get_current_organization(request),
                    teacher_assignment=form.cleaned_data['teacher_assignment'],
                    date=form.cleaned_data['date'],
                    start_time=form.cleaned_data['start_time'],
                    end_time=form.cleaned_data['end_time'],
                    topic_covered=form.cleaned_data['topic_covered']
                )
                return redirect('attendance:mark_attendance_session', session_id=session.id)
        
        elif 'session_id' in request.POST:
            # Mark attendance for existing session
            session_id = request.POST.get('session_id')
            session = get_object_or_404(scoped_queryset(AttendanceSession.objects.all(), request), id=session_id)
            
            # Get all students in the class
            enrollments = scoped_queryset(StudentEnrollment.objects.all(), request).filter(
                class_enrolled=session.teacher_assignment.class_assigned,
                is_active=True
            )
            
            # Process attendance data
            for enrollment in enrollments:
                student_id = enrollment.student.id
                status = request.POST.get(f'status_{student_id}', 'absent')
                remarks = request.POST.get(f'remarks_{student_id}', '')
                
                # Create or update attendance record
                attendance_record, created = AttendanceRecord.objects.get_or_create(
                    organization=get_current_organization(request),
                    session=session,
                    student=enrollment.student,
                    defaults={'status': status, 'remarks': remarks}
                )
                
                if not created:
                    attendance_record.status = status
                    attendance_record.remarks = remarks
                    attendance_record.save()
            
            # Mark session as completed
            session.is_completed = True
            session.save()
            
            messages.success(request, f'Attendance marked successfully for {enrollments.count()} students!')
            return redirect('attendance:attendance_reports')
    
    else:
        form = QuickAttendanceForm(teacher=request.user.teacher_profile, organization=get_current_organization(request))
    
    # Get teacher assignments for the dropdown
    teacher_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
        teacher=request.user.teacher_profile
    ).select_related('subject', 'class_assigned')
    
    # Get recent sessions for this teacher
    recent_sessions = scoped_queryset(AttendanceSession.objects.all(), request).filter(
        teacher_assignment__teacher=request.user.teacher_profile
    ).order_by('-date', '-start_time')[:5]
    
    context = {
        'form': form,
        'teacher_assignments': teacher_assignments,
        'recent_sessions': recent_sessions,
        'today': timezone.now().date()
    }
    
    return render(request, 'attendance/mark_attendance.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def mark_attendance_session(request, session_id):
    """Mark attendance for a specific session"""
    session = get_object_or_404(scoped_queryset(AttendanceSession.objects.all(), request), id=session_id)
    
    # Check if user is admin or has teacher profile
    if request.user.user_type == 'admin':
        # Admin can view but should be warned
        messages.info(request, 'Viewing as administrator. Attendance marking is typically done by teachers.')
    elif not hasattr(request.user, 'teacher_profile'):
        messages.error(request, 'Teacher profile not found. Please contact the administrator.')
        return redirect('accounts:dashboard')
    elif session.teacher_assignment.teacher != request.user.teacher_profile:
        messages.error(request, 'You can only mark attendance for your own classes.')
        return redirect('attendance:mark_attendance')
    
    # Check if user has permission to mark attendance for this session
    if request.user.user_type == 'teacher' and session.teacher_assignment.teacher != request.user.teacher_profile:
        messages.error(request, 'You do not have permission to mark attendance for this session.')
        return redirect('attendance:mark_attendance')
    
    # Get all students in the class
    enrollments = scoped_queryset(StudentEnrollment.objects.all(), request).filter(
        class_enrolled=session.teacher_assignment.class_assigned,
        is_active=True
    ).select_related('student__user')
    
    # Get existing attendance records
    existing_records = {}
    for record in scoped_queryset(AttendanceRecord.objects.all(), request).filter(session=session):
        existing_records[record.student.id] = record
    
    # Prepare student data with existing attendance
    students_data = []
    for enrollment in enrollments:
        existing_record = existing_records.get(enrollment.student.id)
        students_data.append({
            'student': enrollment.student,
            'existing_status': existing_record.status if existing_record else 'present',
            'existing_remarks': existing_record.remarks if existing_record else ''
        })
    
    context = {
        'session': session,
        'students_data': students_data,
        'attendance_choices': AttendanceRecord.ATTENDANCE_CHOICES
    }
    
    return render(request, 'attendance/mark_attendance_session.html', context)

@login_required
def view_attendance(request):
    """View attendance records - accessible by all user types"""
    
    if request.user.user_type == 'student':
        # Student can only view their own attendance
        print("=== STUDENT ATTENDANCE VIEW STARTED ===")
        try:
            student_profile = request.user.student_profile
            enrollment = student_profile.get_current_enrollment()
            
            if not enrollment:
                messages.warning(request, 'You are not enrolled in any class.')
                context = {
                    'attendance_records': [],
                    'subject_groups_list': [],
                    'filter_form': None,
                    'enrollment': None,
                    'total_sessions': 0,
                    'present_sessions': 0,
                    'absent_sessions': 0,
                    'attendance_percentage': 0
                }
                return render(request, 'attendance/view_attendance.html', context)
            
            filter_form = AttendanceFilterForm(request.GET, user=request.user, organization=get_current_organization(request))
            
            attendance_records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(
                student=student_profile
            ).select_related('session__teacher_assignment__subject', 'session__teacher_assignment__teacher__user')
            
            # Apply filters
            if filter_form.is_valid():
                if filter_form.cleaned_data.get('subject'):
                    attendance_records = attendance_records.filter(
                        session__teacher_assignment__subject=filter_form.cleaned_data['subject']
                    )
                if filter_form.cleaned_data.get('date_from'):
                    attendance_records = attendance_records.filter(
                        session__date__gte=filter_form.cleaned_data['date_from']
                    )
                if filter_form.cleaned_data.get('date_to'):
                    attendance_records = attendance_records.filter(
                        session__date__lte=filter_form.cleaned_data['date_to']
                    )
                if filter_form.cleaned_data.get('status'):
                    attendance_records = attendance_records.filter(
                        status=filter_form.cleaned_data['status']
                    )
            
            attendance_records = attendance_records.order_by('-session__date', '-session__start_time')
            
            # Calculate attendance summary
            total_sessions = attendance_records.count()
            present_sessions = attendance_records.filter(status__in=['present', 'late']).count()
            absent_sessions = total_sessions - present_sessions
            attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0
            
            # Group records by subject with statistics
            from collections import defaultdict
            subject_groups = defaultdict(lambda: {'records': [], 'total': 0, 'present': 0, 'percentage': 0})
            
            for record in attendance_records:
                subject_name = record.session.teacher_assignment.subject.name
                subject_groups[subject_name]['records'].append(record)
                subject_groups[subject_name]['total'] += 1
                if record.status in ['present', 'late']:
                    subject_groups[subject_name]['present'] += 1
            
            # Calculate percentages and convert to list
            subject_groups_list = []
            for subject_name, data in subject_groups.items():
                total = data['total']
                present = data['present']
                percentage = round((present / total * 100), 2) if total > 0 else 0
                subject_groups_list.append({
                    'subject_name': subject_name,
                    'records': data['records'],
                    'total': total,
                    'present': present,
                    'percentage': percentage
                })
            
            # Debug print
            print(f"DEBUG: User type: {request.user.user_type}")
            print(f"DEBUG: Subject groups count: {len(subject_groups_list)}")
            print(f"DEBUG: Subject groups: {[g['subject_name'] for g in subject_groups_list]}")
            
            context = {
                'attendance_records': attendance_records,
                'subject_groups_list': subject_groups_list,
                'filter_form': filter_form,
                'enrollment': enrollment,
                'total_sessions': total_sessions,
                'present_sessions': present_sessions,
                'absent_sessions': absent_sessions,
                'attendance_percentage': round(attendance_percentage, 2)
            }
            
        except Exception as e:
            print(f"Error in student attendance view: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, 'An error occurred while loading attendance data.')
            context = {
                'attendance_records': [],
                'subject_groups_list': [],
                'filter_form': None,
                'enrollment': None,
                'total_sessions': 0,
                'present_sessions': 0,
                'absent_sessions': 0,
                'attendance_percentage': 0
            }
    
    elif request.user.user_type == 'teacher':
        # Check if teacher profile exists
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, 'Teacher profile not found. Please contact the administrator.')
            return redirect('accounts:dashboard')
        
        filter_form = AttendanceFilterForm(request.GET, user=request.user, organization=get_current_organization(request))
        
        # Teacher can view attendance for their classes
        teacher_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
            teacher=request.user.teacher_profile
        )
        
        attendance_records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(
            session__teacher_assignment__in=teacher_assignments
        ).select_related('student__user', 'session__teacher_assignment__subject')
        
        # Apply filters
        if filter_form.is_valid():
            if filter_form.cleaned_data.get('subject'):
                attendance_records = attendance_records.filter(
                    session__teacher_assignment__subject=filter_form.cleaned_data['subject']
                )
            if filter_form.cleaned_data.get('class_filter'):
                attendance_records = attendance_records.filter(
                    session__teacher_assignment__class_assigned=filter_form.cleaned_data['class_filter']
                )
            if filter_form.cleaned_data.get('date_from'):
                attendance_records = attendance_records.filter(
                    session__date__gte=filter_form.cleaned_data['date_from']
                )
            if filter_form.cleaned_data.get('date_to'):
                attendance_records = attendance_records.filter(
                    session__date__lte=filter_form.cleaned_data['date_to']
                )
            if filter_form.cleaned_data.get('status'):
                attendance_records = attendance_records.filter(
                    status=filter_form.cleaned_data['status']
                )
        
        attendance_records = attendance_records.order_by('-session__date', '-session__start_time')
        
        context = {
            'attendance_records': attendance_records,
            'filter_form': filter_form
        }
    
    else:  # Admin or parent
        filter_form = AttendanceFilterForm(request.GET, user=request.user, organization=get_current_organization(request))
        
        if request.user.user_type == 'parent':
            # Parent can view attendance for their children
            try:
                parent_profile = request.user.parent_profile
                children = parent_profile.children.all()
                
                if not children.exists():
                    messages.warning(request, 'No children linked to your account.')
                    context = {
                        'attendance_records': [],
                        'filter_form': filter_form
                    }
                    return render(request, 'attendance/view_attendance.html', context)
                
                # Get attendance records for all children
                attendance_records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(
                    student__in=children
                ).select_related(
                    'student__user', 'session__teacher_assignment__subject', 
                    'session__teacher_assignment__teacher__user'
                )
                
                # Apply filters
                if filter_form.is_valid():
                    if filter_form.cleaned_data.get('subject'):
                        attendance_records = attendance_records.filter(
                            session__teacher_assignment__subject=filter_form.cleaned_data['subject']
                        )
                    if filter_form.cleaned_data.get('class_filter'):
                        attendance_records = attendance_records.filter(
                            session__teacher_assignment__class_assigned=filter_form.cleaned_data['class_filter']
                        )
                    if filter_form.cleaned_data.get('date_from'):
                        attendance_records = attendance_records.filter(
                            session__date__gte=filter_form.cleaned_data['date_from']
                        )
                    if filter_form.cleaned_data.get('date_to'):
                        attendance_records = attendance_records.filter(
                            session__date__lte=filter_form.cleaned_data['date_to']
                        )
                    if filter_form.cleaned_data.get('status'):
                        attendance_records = attendance_records.filter(
                            status=filter_form.cleaned_data['status']
                        )
                
                attendance_records = attendance_records.order_by('-session__date', '-session__start_time')
                
                context = {
                    'attendance_records': attendance_records,
                    'filter_form': filter_form,
                    'children': children
                }
                
            except Exception as e:
                print(f"Error in parent attendance view: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, 'An error occurred while loading attendance data.')
                context = {
                    'attendance_records': [],
                    'filter_form': filter_form
                }
        else:
            # Admin can view all attendance records
            attendance_records = scoped_queryset(AttendanceRecord.objects.all(), request).select_related(
                'student__user', 'session__teacher_assignment__subject', 
                'session__teacher_assignment__teacher__user'
            )
            
            # Apply filters (admin has access to all filters)
            if filter_form.is_valid():
                if filter_form.cleaned_data.get('subject'):
                    attendance_records = attendance_records.filter(
                        session__teacher_assignment__subject=filter_form.cleaned_data['subject']
                    )
                if filter_form.cleaned_data.get('class_filter'):
                    attendance_records = attendance_records.filter(
                        session__teacher_assignment__class_assigned=filter_form.cleaned_data['class_filter']
                    )
                if filter_form.cleaned_data.get('date_from'):
                    attendance_records = attendance_records.filter(
                        session__date__gte=filter_form.cleaned_data['date_from']
                    )
                if filter_form.cleaned_data.get('date_to'):
                    attendance_records = attendance_records.filter(
                        session__date__lte=filter_form.cleaned_data['date_to']
                    )
                if filter_form.cleaned_data.get('status'):
                    attendance_records = attendance_records.filter(
                        status=filter_form.cleaned_data['status']
                    )
            
            attendance_records = attendance_records.order_by('-session__date', '-session__start_time')
            
            context = {
                'attendance_records': attendance_records,
                'filter_form': filter_form
            }
    
    return render(request, 'attendance/view_attendance.html', context)

@login_required
def real_teacher_attendance(request):
    """View real teacher attendance based on activities"""
    today = timezone.now().date()
    
    # Get filter parameters
    selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
    
    try:
        filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        filter_date = today
    
    # Get all teachers
    all_teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
    total_teachers = all_teachers.count()
    
    # Process each teacher's attendance for the selected date
    enhanced_attendance = []
    present_count = 0
    absent_count = 0
    late_count = 0
    
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
        if attendance.status == 'present':
            present_count += 1
        elif attendance.status == 'late':
            late_count += 1
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
            'has_real_activities': attendance.has_performed_duties()
        })
    
    # Calculate attendance percentage
    attendance_percentage = round((present_count + late_count) / total_teachers * 100, 1) if total_teachers > 0 else 0
    
    context = {
        'enhanced_attendance': enhanced_attendance,
        'selected_date': selected_date,
        'filter_date': filter_date,
        'total_teachers': total_teachers,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'attendance_percentage': attendance_percentage,
    }
    
    return render(request, 'attendance/real_teacher_attendance.html', context)
    """Generate attendance reports"""
    context = {}
    
    if request.user.user_type == 'student':
        # Student attendance summary
        try:
            enrollment = request.user.student_profile.get_current_enrollment()
            
            if enrollment:
                # Get attendance summary by subject
                from academic.models import Subject
                subjects = Subject.objects.filter(
                    course=enrollment.class_enrolled.course,
                    year=enrollment.class_enrolled.year,
                    semester=enrollment.class_enrolled.semester
                )
                
                subject_summaries = []
                for subject in subjects:
                    records = AttendanceRecord.objects.filter(
                        student=request.user.student_profile,
                    session__teacher_assignment__subject=subject
                )
                
                total = records.count()
                present = records.filter(status__in=['present', 'late']).count()
                percentage = (present / total * 100) if total > 0 else 0
                
                subject_summaries.append({
                    'subject': subject,
                    'total_sessions': total,
                    'present_sessions': present,
                    'absent_sessions': total - present,
                    'percentage': round(percentage, 2)
                })
            
                context = {
                    'enrollment': enrollment,
                    'subject_summaries': subject_summaries
                }
            else:
                context = {
                    'enrollment': None,
                    'subject_summaries': []
                }
            
        except (StudentProfile.DoesNotExist, AttributeError):
            messages.error(request, 'You are not enrolled in any class.')
            context = {}
    
    elif request.user.user_type == 'teacher':
        # Check if teacher profile exists
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, 'Teacher profile not found. Please contact the administrator.')
            return redirect('accounts:dashboard')
        
        # Get filter parameters
        selected_class = request.GET.get('class_filter', '')
        selected_month = request.GET.get('month_filter', '')  # Empty means all months
        
        # Teacher's class attendance reports
        teacher_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
            teacher=request.user.teacher_profile
        ).select_related('subject', 'class_assigned')
        
        # Get all classes for filter dropdown
        teacher_classes = scoped_queryset(Class.objects.all(), request).filter(
            id__in=teacher_assignments.values_list('class_assigned_id', flat=True)
        ).distinct()
        
        # Filter assignments if class is selected
        if selected_class:
            teacher_assignments = teacher_assignments.filter(class_assigned_id=selected_class)
        
        # Parse month filter (only if specified)
        year = None
        month = None
        if selected_month:
            try:
                year, month = map(int, selected_month.split('-'))
            except:
                pass
        
        # Get all students from teacher's classes with their attendance data
        student_reports = []
        overall_present = 0
        overall_total = 0
        best_class = None
        best_class_percentage = 0
        
        class_summaries = []
        for assignment in teacher_assignments:
            # Get all students in this class
            enrollments = scoped_queryset(StudentEnrollment.objects.all(), request).filter(
                class_enrolled=assignment.class_assigned,
                is_active=True
            ).select_related('student__user')
            
            # Get attendance sessions for this assignment
            sessions = scoped_queryset(AttendanceSession.objects.all(), request).filter(
                teacher_assignment=assignment
            )
            
            # Apply month filter only if specified
            if year and month:
                sessions = sessions.filter(date__year=year, date__month=month)
            
            total_sessions = sessions.count()
            total_students = enrollments.count()
            
            class_present = 0
            class_total = 0
            
            # Get detailed student attendance for this class
            for enrollment in enrollments:
                student = enrollment.student
                
                # Get attendance records for this student in this class
                records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(
                    session__in=sessions,
                    student=student
                )
                
                total_classes = records.count()
                present_count = records.filter(status='present').count()
                absent_count = records.filter(status='absent').count()
                late_count = records.filter(status='late').count()
                excused_count = records.filter(status='excused').count()
                
                if total_classes > 0:
                    attendance_percentage = ((present_count + late_count) / total_classes) * 100
                    
                    # Determine status
                    if attendance_percentage >= 90:
                        status = 'Excellent'
                        status_class = 'success'
                    elif attendance_percentage >= 80:
                        status = 'Good'
                        status_class = 'success'
                    elif attendance_percentage >= 70:
                        status = 'Average'
                        status_class = 'warning'
                    else:
                        status = 'Poor'
                        status_class = 'danger'
                    
                    student_reports.append({
                        'student': student,
                        'class_name': assignment.class_assigned.name,
                        'total_classes': total_classes,
                        'present': present_count,
                        'absent': absent_count,
                        'late': late_count,
                        'excused': excused_count,
                        'percentage': round(attendance_percentage, 1),
                        'status': status,
                        'status_class': status_class
                    })
                    
                    class_present += present_count + late_count
                    class_total += total_classes
            
            # Calculate class average
            if class_total > 0:
                avg_attendance = (class_present / class_total * 100)
                
                if avg_attendance > best_class_percentage:
                    best_class_percentage = avg_attendance
                    best_class = assignment.class_assigned.name
            else:
                avg_attendance = 0
            
            overall_present += class_present
            overall_total += class_total
            
            class_summaries.append({
                'assignment': assignment,
                'total_sessions': total_sessions,
                'total_students': total_students,
                'avg_attendance': round(avg_attendance, 2)
            })
        
        # Calculate overall attendance
        overall_attendance = (overall_present / overall_total * 100) if overall_total > 0 else 0
        
        # Sort student reports by percentage (descending)
        student_reports.sort(key=lambda x: x['percentage'], reverse=True)
        
        context = {
            'class_summaries': class_summaries,
            'student_reports': student_reports,
            'overall_attendance': round(overall_attendance, 1),
            'best_class': best_class,
            'best_class_percentage': round(best_class_percentage, 1),
            'teacher_classes': teacher_classes,
            'selected_class': selected_class,
            'selected_month': selected_month
        }
    
    else:  # Admin
        # Overall system attendance reports
        total_students = scoped_profile_queryset(StudentProfile.objects.all(), request).count()
        total_sessions = scoped_queryset(AttendanceSession.objects.all(), request).count()
        total_records = scoped_queryset(AttendanceRecord.objects.all(), request).count()
        present_records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(status__in=['present', 'late']).count()
        
        overall_attendance = (present_records / total_records * 100) if total_records > 0 else 0
        
        # Department-wise attendance
        from academic.models import Department
        departments = scoped_queryset(Department.objects.all(), request)
        dept_summaries = []
        
        for dept in departments:
            dept_records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(
                session__teacher_assignment__class_assigned__course__department=dept
            )
            dept_total = dept_records.count()
            dept_present = dept_records.filter(status__in=['present', 'late']).count()
            dept_percentage = (dept_present / dept_total * 100) if dept_total > 0 else 0
            
            dept_summaries.append({
                'department': dept,
                'total_records': dept_total,
                'present_records': dept_present,
                'percentage': round(dept_percentage, 2)
            })
        
        context = {
            'total_students': total_students,
            'total_sessions': total_sessions,
            'total_records': total_records,
            'present_records': present_records,
            'overall_attendance': round(overall_attendance, 2),
            'dept_summaries': dept_summaries
        }
    
    return render(request, 'attendance/attendance_reports.html', context)


@login_required
def real_teacher_attendance(request):
    """View real teacher attendance based on activities"""
    today = timezone.now().date()
    
    # Get filter parameters
    selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
    
    try:
        filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        filter_date = today
    
    # Get all teachers
    all_teachers = scoped_profile_queryset(TeacherProfile.objects.select_related('user'), request).order_by('user__first_name')
    total_teachers = all_teachers.count()
    
    # Process each teacher's attendance for the selected date
    enhanced_attendance = []
    present_count = 0
    absent_count = 0
    late_count = 0
    
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
        if attendance.status == 'present':
            present_count += 1
        elif attendance.status == 'late':
            late_count += 1
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
            'has_real_activities': attendance.has_performed_duties()
        })
    
    # Calculate attendance percentage
    attendance_percentage = round((present_count + late_count) / total_teachers * 100, 1) if total_teachers > 0 else 0
    
    context = {
        'enhanced_attendance': enhanced_attendance,
        'selected_date': selected_date,
        'filter_date': filter_date,
        'total_teachers': total_teachers,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'attendance_percentage': attendance_percentage,
    }
    
    return render(request, 'attendance/real_teacher_attendance.html', context)

@login_required
def attendance_reports(request):
    """Generate attendance reports"""
    from academic.models import TeacherSubjectAssignment, Class, AcademicYear
    
    # Get current academic year
    current_academic_year = scoped_queryset(AcademicYear.objects.all(), request).filter(is_current=True).first()
    if not current_academic_year:
        current_academic_year = scoped_queryset(AcademicYear.objects.all(), request).first()
    
    # Get filter parameters
    selected_class = request.GET.get('class_filter', '')
    selected_month = request.GET.get('month_filter', '')
    
    # Parse month filter
    year = None
    month = None
    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
        except:
            pass
    
    # Get all teacher assignments for current academic year
    teacher_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
        academic_year=current_academic_year
    ).select_related('teacher', 'subject', 'class_assigned')
    
    # Get all classes for filter dropdown
    all_classes = scoped_queryset(Class.objects.all(), request).filter(
        academic_year=current_academic_year
    ).distinct()
    
    # Filter assignments if class is selected
    if selected_class:
        teacher_assignments = teacher_assignments.filter(class_assigned_id=selected_class)
        all_classes = all_classes.filter(id=selected_class)
    
    # Initialize variables
    student_reports = []
    overall_present = 0
    overall_total = 0
    best_class = None
    best_class_percentage = 0
    class_summaries = []
    
    # Process each assignment
    for assignment in teacher_assignments:
        # Get all students in this class
        enrollments = scoped_queryset(StudentEnrollment.objects.all(), request).filter(
            class_enrolled=assignment.class_assigned,
            is_active=True
        ).select_related('student__user')
        
        # Get attendance sessions for this assignment
        sessions = scoped_queryset(AttendanceSession.objects.all(), request).filter(
            teacher_assignment=assignment
        )
        
        # Apply month filter if specified
        if year and month:
            sessions = sessions.filter(date__year=year, date__month=month)
        
        total_sessions = sessions.count()
        total_students = enrollments.count()
        
        class_present = 0
        class_total = 0
        
        # Get detailed student attendance for this class
        for enrollment in enrollments:
            student = enrollment.student
            
            # Get attendance records for this student in this class
            records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(
                session__in=sessions,
                student=student
            )
            
            total_classes = records.count()
            present_count = records.filter(status='present').count()
            absent_count = records.filter(status='absent').count()
            late_count = records.filter(status='late').count()
            excused_count = records.filter(status='excused').count()
            
            if total_classes > 0:
                attendance_percentage = ((present_count + late_count) / total_classes) * 100
                
                # Determine status
                if attendance_percentage >= 90:
                    status = 'Excellent'
                    status_class = 'success'
                elif attendance_percentage >= 80:
                    status = 'Good'
                    status_class = 'success'
                elif attendance_percentage >= 70:
                    status = 'Average'
                    status_class = 'warning'
                else:
                    status = 'Poor'
                    status_class = 'danger'
                
                student_reports.append({
                    'student': student,
                    'class_name': assignment.class_assigned.name,
                    'subject_name': assignment.subject.name,
                    'total_classes': total_classes,
                    'present': present_count,
                    'absent': absent_count,
                    'late': late_count,
                    'excused': excused_count,
                    'percentage': round(attendance_percentage, 1),
                    'status': status,
                    'status_class': status_class
                })
                
                class_present += present_count + late_count
                class_total += total_classes
        
        # Calculate class average
        if class_total > 0:
            avg_attendance = (class_present / class_total * 100)
            
            if avg_attendance > best_class_percentage:
                best_class_percentage = avg_attendance
                best_class = assignment.class_assigned.name
        else:
            avg_attendance = 0
        
        overall_present += class_present
        overall_total += class_total
        
        class_summaries.append({
            'assignment': assignment,
            'total_sessions': total_sessions,
            'total_students': total_students,
            'avg_attendance': round(avg_attendance, 2)
        })
    
    # Calculate overall attendance
    overall_attendance = (overall_present / overall_total * 100) if overall_total > 0 else 0
    
    # Sort student reports by percentage (descending)
    student_reports.sort(key=lambda x: x['percentage'], reverse=True)
    
    # If no data found, try to get some basic stats
    if not student_reports:
        # Get overall system stats
        total_students = scoped_profile_queryset(StudentProfile.objects.all(), request).count()
        total_sessions = scoped_queryset(AttendanceSession.objects.all(), request).count()
        total_records = scoped_queryset(AttendanceRecord.objects.all(), request).count()
        present_records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(status__in=['present', 'late']).count()
        
        if total_records > 0:
            overall_attendance = (present_records / total_records * 100)
        
        # Try to get some sample data from any academic year
        sample_assignments = scoped_queryset(TeacherSubjectAssignment.objects.all(), request)[:5]
        for assignment in sample_assignments:
            enrollments = scoped_queryset(StudentEnrollment.objects.all(), request).filter(
                class_enrolled=assignment.class_assigned,
                is_active=True
            )[:3]  # Just get a few students
            
            sessions = scoped_queryset(AttendanceSession.objects.all(), request).filter(
                teacher_assignment=assignment
            )[:5]  # Just get a few sessions
            
            for enrollment in enrollments:
                records = scoped_queryset(AttendanceRecord.objects.all(), request).filter(
                    session__in=sessions,
                    student=enrollment.student
                )
                
                if records.exists():
                    total_classes = records.count()
                    present_count = records.filter(status='present').count()
                    absent_count = records.filter(status='absent').count()
                    late_count = records.filter(status='late').count()
                    excused_count = records.filter(status='excused').count()
                    
                    attendance_percentage = ((present_count + late_count) / total_classes) * 100
                    
                    if attendance_percentage >= 90:
                        status = 'Excellent'
                        status_class = 'success'
                    elif attendance_percentage >= 80:
                        status = 'Good'
                        status_class = 'success'
                    elif attendance_percentage >= 70:
                        status = 'Average'
                        status_class = 'warning'
                    else:
                        status = 'Poor'
                        status_class = 'danger'
                    
                    student_reports.append({
                        'student': enrollment.student,
                        'class_name': assignment.class_assigned.name,
                        'subject_name': assignment.subject.name,
                        'total_classes': total_classes,
                        'present': present_count,
                        'absent': absent_count,
                        'late': late_count,
                        'excused': excused_count,
                        'percentage': round(attendance_percentage, 1),
                        'status': status,
                        'status_class': status_class
                    })
    
    context = {
        'class_summaries': class_summaries,
        'student_reports': student_reports,
        'overall_attendance': round(overall_attendance, 1),
        'best_class': best_class,
        'best_class_percentage': round(best_class_percentage, 1),
        'teacher_classes': all_classes,
        'selected_class': selected_class,
        'selected_month': selected_month,
        'current_academic_year': current_academic_year
    }
    
    if request.user.user_type == 'student':
        # Student can see their own attendance
        try:
            enrollment = request.user.student_profile.get_current_enrollment()
            if enrollment:
                # Filter student reports to show only this student's data
                context['student_reports'] = [
                    report for report in student_reports 
                    if report['student'].id == request.user.student_profile.id
                ]
        except (StudentProfile.DoesNotExist, AttributeError):
            pass
    
    return render(request, 'attendance/attendance_reports.html', context)
