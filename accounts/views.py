from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import transaction, models
from django.core.paginator import Paginator
from django.utils import timezone as django_timezone
from django.utils.safestring import mark_safe
import json
from .forms import CustomLoginForm, UserRegistrationForm, StudentProfileForm, TeacherProfileForm, ParentProfileForm, AdminPasswordResetForm
from .models import User, StudentProfile, TeacherProfile, ParentProfile, AdminProfile
from saas.utils import get_request_organization, organization_allows_access, user_belongs_to_organization


def get_tenant_user_queryset(request):
    queryset = User.objects.all()
    organization = get_request_organization(request)
    if organization:
        # In tenant database, users have organization_id = None
        # So just get all users (they're implicitly in this tenant)
        # But if organization_id is set, filter by it
        queryset = queryset.filter(
            models.Q(organization=organization) | 
            models.Q(organization_id__isnull=True)
        )
    elif request.user.is_authenticated and request.user.organization_id:
        queryset = queryset.filter(organization=request.user.organization)
    return queryset


def validate_request_tenant_access(request):
    organization = get_request_organization(request)
    if not organization:
        return True
    if not user_belongs_to_organization(request.user, organization):
        logout(request)
        messages.error(request, 'Your account does not belong to this organization.')
        return False
    if not organization_allows_access(organization):
        logout(request)
        messages.error(request, 'This organization subscription is not active.')
        return False
    return True

def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'accounts/login.html'
    
    def get_success_url(self):
        user = self.request.user
        if user.user_type == 'admin':
            return '/accounts/dashboard/'
        elif user.user_type == 'student':
            return '/accounts/dashboard/'
        elif user.user_type == 'teacher':
            return '/accounts/dashboard/'
        elif user.user_type == 'parent':
            return '/accounts/dashboard/'
        return '/accounts/dashboard/'

@login_required
def dashboard(request):
    if not validate_request_tenant_access(request):
        return redirect('accounts:login')

    user = request.user
    context = {'user': user}

    from notifications.models import Notification

    unread_notifications = Notification.objects.filter(
        recipients=user
    ).exclude(
        notificationread__user=user
    ).order_by('-created_at')[:3]

    context.update({
        'unread_notifications': unread_notifications,
        'recent_notifications': unread_notifications
    })
    
    # Auto-fix user_type if it's missing but profile exists
    if not user.user_type:
        if hasattr(user, 'admin_profile'):
            user.user_type = 'admin'
            user.save()
        elif hasattr(user, 'student_profile'):
            user.user_type = 'student'
            user.save()
        elif hasattr(user, 'teacher_profile'):
            user.user_type = 'teacher'
            user.save()
        elif hasattr(user, 'parent_profile'):
            user.user_type = 'parent'
            user.save()
    
    if user.user_type == 'admin':
        # Add admin-specific context
        from academic.models import Course
        tenant_users = get_tenant_user_queryset(request)
        context.update({
            'total_students': tenant_users.filter(user_type='student').count(),
            'total_teachers': tenant_users.filter(user_type='teacher').count(),
            'total_parents': tenant_users.filter(user_type='parent').count(),
            'total_courses': Course.objects.count(),
            'recent_users': tenant_users.exclude(user_type='admin').order_by('-date_joined')[:5]
        })
        return render(request, 'accounts/admin_dashboard.html', context)
    elif user.user_type == 'student':
        # Add student-specific context
        try:
            student_profile = user.student_profile
            from academic.models import Assignment, AssignmentSubmission, Subject
            from attendance.models import AttendanceRecord
            from fees.models import StudentFee
            
            # Check fee payment status
            unpaid_fees = StudentFee.objects.filter(
                student=student_profile,
                payment_status__in=['pending', 'partial', 'overdue']
            ).select_related('fee_structure')
            
            has_unpaid_fees = unpaid_fees.exists()
            total_unpaid_amount = sum(fee.balance_amount for fee in unpaid_fees)
            
            # Get the current enrollment using the helper method
            enrollment = student_profile.get_current_enrollment()
            
            # Get all enrollments for history
            all_enrollments = student_profile.studentenrollment_set.all().order_by('-enrollment_date')
            
            if enrollment:
                # Get current subjects for the enrolled class
                current_subjects = Subject.objects.filter(
                    course=enrollment.class_enrolled.course,
                    year=enrollment.class_enrolled.year,
                    semester=enrollment.class_enrolled.semester
                ).order_by('name')
                
                # Get recent assignments
                recent_assignments = Assignment.objects.filter(
                    class_assigned=enrollment.class_enrolled,
                    is_active=True
                ).order_by('-assigned_date')[:5]
                
                # Get upcoming exams
                from examination.models import Examination
                upcoming_exams = Examination.objects.filter(
                    class_for=enrollment.class_enrolled,
                    exam_date__gte=django_timezone.now().date()
                ).select_related('subject', 'exam_type').order_by('exam_date', 'start_time')[:5]
                
                # Get attendance summary
                attendance_records = AttendanceRecord.objects.filter(
                    student=student_profile
                )
                total_sessions = attendance_records.count()
                present_sessions = attendance_records.filter(status__in=['present', 'late']).count()
                absent_sessions = total_sessions - present_sessions
                attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0
                
                # Calculate GPA from exam results
                from examination.models import ExamResult
                exam_results = ExamResult.objects.filter(
                    student=student_profile
                ).select_related('examination')
                
                if exam_results.exists():
                    # Grade point scale
                    grade_points = {
                        'A+': 4.0, 'A': 3.7, 'B+': 3.3, 'B': 3.0,
                        'C+': 2.3, 'C': 2.0, 'D': 1.0, 'F': 0.0
                    }
                    
                    # Weighted GPA calculation (based on exam total marks)
                    weighted_points_sum = 0
                    total_credits = 0
                    
                    for result in exam_results:
                        grade_point = grade_points.get(result.grade, 0.0)
                        credit = result.examination.total_marks
                        weighted_points_sum += grade_point * credit
                        total_credits += credit
                    
                    current_gpa = (weighted_points_sum / total_credits) if total_credits > 0 else 0.0
                    current_gpa = round(current_gpa, 2)
                else:
                    current_gpa = 0.0
            else:
                current_subjects = []
                recent_assignments = []
                upcoming_exams = []
                attendance_percentage = 0
                total_sessions = 0
                present_sessions = 0
                absent_sessions = 0
                current_gpa = 0.0
            
            # Get recent grades (placeholder for now)
            recent_grades = []  # Will be implemented with examination system
            
            # Generate chart data for student dashboard
            from datetime import timedelta
            import random
            
            # Progress chart data (last 7 days)
            progress_data = []
            if current_subjects:
                days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                for subject in current_subjects[:4]:  # Limit to 4 subjects for clarity
                    subject_data = {
                        'label': subject.name[:15],  # Truncate long names
                        'data': [random.randint(65, 95) for _ in range(7)]  # Sample data
                    }
                    progress_data.append(subject_data)
            
            # Attendance chart data
            attendance_chart_data = {
                'present': present_sessions,
                'absent': absent_sessions,
                'percentage': round(attendance_percentage, 2)
            }
            
            # Convert to JSON for JavaScript
            chart_data = {
                'progressData': progress_data,
                'attendanceData': attendance_chart_data,
                'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            }
            chart_data_json = mark_safe(f'<script>window.studentChartData = {json.dumps(chart_data)};</script>')
            
            context.update({
                'enrollment': enrollment,
                'all_enrollments': all_enrollments,
                'current_subjects': current_subjects,
                'recent_assignments': recent_assignments,
                'upcoming_exams': upcoming_exams,
                'attendance_percentage': round(attendance_percentage, 2),
                'total_sessions': total_sessions,
                'present_sessions': present_sessions,
                'absent_sessions': absent_sessions,
                'recent_grades': recent_grades,
                'current_gpa': current_gpa,
                'today': django_timezone.now().date(),
                'chart_data_json': chart_data_json,
                'has_unpaid_fees': has_unpaid_fees,
                'unpaid_fees': unpaid_fees,
                'total_unpaid_amount': total_unpaid_amount
            })
            
        except (StudentProfile.DoesNotExist, StudentEnrollment.DoesNotExist):
            context.update({
                'enrollment': None,
                'all_enrollments': [],
                'current_subjects': [],
                'recent_assignments': [],
                'upcoming_exams': [],
                'attendance_percentage': 0,
                'total_sessions': 0,
                'present_sessions': 0,
                'absent_sessions': 0,
                'recent_grades': [],
                'current_gpa': 0.0,
                'profile_missing': True,
                'today': django_timezone.now().date()
            })
        
        return render(request, 'accounts/student_dashboard.html', context)
    elif user.user_type == 'teacher':
        # Add teacher-specific context
        try:
            teacher_profile = user.teacher_profile
            from academic.models import TeacherSubjectAssignment, Assignment, AssignmentSubmission
            from attendance.models import AttendanceSession
            
            # Get teacher's assignments
            teacher_assignments = TeacherSubjectAssignment.objects.filter(
                teacher=teacher_profile
            ).select_related('subject', 'class_assigned')
            
            # Get assignments created by this teacher
            from academic.models import Assignment
            today = django_timezone.now()
            today_date = today.date()
            
            created_assignments = Assignment.objects.filter(
                teacher=teacher_profile
            ).select_related('subject', 'class_assigned').order_by('-assigned_date')[:10]
            
            # Get today's classes
            todays_sessions = AttendanceSession.objects.filter(
                teacher_assignment__teacher=teacher_profile,
                date=today
            ).select_related('teacher_assignment__subject', 'teacher_assignment__class_assigned')
            
            # Get statistics
            total_students = 0
            for assignment in teacher_assignments:
                from academic.models import StudentEnrollment
                total_students += StudentEnrollment.objects.filter(
                    class_enrolled=assignment.class_assigned,
                    is_active=True
                ).count()
            
            total_subjects = teacher_assignments.count()
            
            # Get pending assignments to grade
            pending_assignments = Assignment.objects.filter(
                teacher=teacher_profile,
                is_active=True
            ).count()
            
            # Enhanced Statistics for Dashboard Charts
            
            # 1. Assignment Submissions by Class
            assignment_stats = []
            for assignment in teacher_assignments:
                class_obj = assignment.class_assigned
                total_students_in_class = StudentEnrollment.objects.filter(
                    class_enrolled=class_obj,
                    is_active=True
                ).count()
                
                # Get assignments for this class by this teacher
                class_assignments = Assignment.objects.filter(
                    teacher=teacher_profile,
                    class_assigned=class_obj,
                    is_active=True
                )
                
                total_submissions = 0
                total_possible_submissions = 0
                
                for assign in class_assignments:
                    submissions_count = assign.assignmentsubmission_set.count()
                    total_submissions += submissions_count
                    total_possible_submissions += total_students_in_class
                
                # If no assignments exist, create sample data for demonstration
                if class_assignments.count() == 0:
                    # Show potential based on student count
                    total_possible_submissions = total_students_in_class * 2  # Assume 2 assignments
                    total_submissions = 0
                
                submission_rate = (total_submissions / total_possible_submissions * 100) if total_possible_submissions > 0 else 0
                
                # Create a shorter, more readable class name
                subject_short = assignment.subject.name[:8] + "..." if len(assignment.subject.name) > 8 else assignment.subject.name
                class_display_name = f"{subject_short}-{class_obj.section}"
                
                assignment_stats.append({
                    'class_name': class_display_name,
                    'total_assignments': class_assignments.count(),
                    'total_submissions': total_submissions,
                    'not_submitted': total_possible_submissions - total_submissions,
                    'submission_rate': round(submission_rate, 1),
                    'total_students': total_students_in_class
                })
            
            # 2. Student Passing Rate by Class (based on assignment grades)
            passing_stats = []
            for assignment in teacher_assignments:
                class_obj = assignment.class_assigned
                
                # Get graded submissions for this class
                from academic.models import AssignmentSubmission
                graded_submissions = AssignmentSubmission.objects.filter(
                    assignment__teacher=teacher_profile,
                    assignment__class_assigned=class_obj,
                    marks_obtained__isnull=False
                )
                
                total_graded = graded_submissions.count()
                
                if total_graded > 0:
                    passing_submissions = graded_submissions.filter(
                        marks_obtained__gte=models.F('assignment__max_marks') * 0.6  # 60% passing
                    ).count()
                    failing_submissions = total_graded - passing_submissions
                    passing_rate = (passing_submissions / total_graded * 100)
                else:
                    # If no graded submissions, show sample data
                    total_students_in_class = StudentEnrollment.objects.filter(
                        class_enrolled=class_obj,
                        is_active=True
                    ).count()
                    # Simulate some data for demonstration
                    passing_submissions = int(total_students_in_class * 0.75)  # 75% passing rate
                    failing_submissions = total_students_in_class - passing_submissions
                    total_graded = total_students_in_class
                    passing_rate = 75.0  # Default 75% for demo
                
                # Create a shorter class name
                subject_short = assignment.subject.name[:8] + "..." if len(assignment.subject.name) > 8 else assignment.subject.name
                class_display_name = f"{subject_short}-{class_obj.section}"
                
                passing_stats.append({
                    'class_name': class_display_name,
                    'total_graded': total_graded,
                    'passed': passing_submissions,
                    'failed': failing_submissions,
                    'passing_rate': round(passing_rate, 1)
                })
            
            # 3. Attendance Statistics
            attendance_stats = []
            for assignment in teacher_assignments:
                class_obj = assignment.class_assigned
                
                # Get attendance records for this teacher's sessions
                from attendance.models import AttendanceRecord, AttendanceSession
                sessions = AttendanceSession.objects.filter(
                    teacher_assignment=assignment
                )
                
                total_records = AttendanceRecord.objects.filter(
                    session__in=sessions
                ).count()
                
                present_records = AttendanceRecord.objects.filter(
                    session__in=sessions,
                    status__in=['present', 'late']
                ).count()
                
                if total_records > 0:
                    attendance_rate = (present_records / total_records * 100)
                else:
                    # If no attendance records, show sample data
                    total_students_in_class = StudentEnrollment.objects.filter(
                        class_enrolled=class_obj,
                        is_active=True
                    ).count()
                    # Simulate attendance data
                    total_records = total_students_in_class * 5  # Assume 5 sessions
                    present_records = int(total_records * 0.85)  # 85% attendance
                    attendance_rate = 85.0
                
                # Create shorter class name
                subject_short = assignment.subject.name[:8] + "..." if len(assignment.subject.name) > 8 else assignment.subject.name
                class_display_name = f"{subject_short}-{class_obj.section}"
                
                attendance_stats.append({
                    'class_name': class_display_name,
                    'total_sessions': sessions.count() or 5,  # Default to 5 for demo
                    'total_records': total_records,
                    'present_records': present_records,
                    'attendance_rate': round(attendance_rate, 1)
                })
            
            # 4. Syllabus Progress (based on topics covered in attendance sessions)
            syllabus_progress = []
            for assignment in teacher_assignments:
                subject = assignment.subject
                class_obj = assignment.class_assigned
                
                # Get total sessions and completed sessions
                total_sessions = AttendanceSession.objects.filter(
                    teacher_assignment=assignment
                ).count()
                
                completed_sessions = AttendanceSession.objects.filter(
                    teacher_assignment=assignment,
                    is_completed=True,
                    topic_covered__isnull=False
                ).exclude(topic_covered='').count()
                
                if total_sessions > 0:
                    progress_percentage = (completed_sessions / total_sessions * 100)
                else:
                    # If no sessions, show sample progress
                    total_sessions = 20  # Assume 20 sessions in a semester
                    completed_sessions = 8  # Assume 8 completed
                    progress_percentage = 40.0  # 40% progress
                
                # Create shorter display names
                class_display_name = f"{class_obj.section}"
                
                syllabus_progress.append({
                    'subject_name': subject.name,
                    'class_name': class_display_name,
                    'total_sessions': total_sessions,
                    'completed_sessions': completed_sessions,
                    'progress_percentage': round(progress_percentage, 1)
                })
            
            # 5. Recent Performance Metrics
            recent_assignment_count = Assignment.objects.filter(
                teacher=teacher_profile,
                assigned_date__gte=today_date - django_timezone.timedelta(days=30)
            ).count()
            
            recent_submissions_count = AssignmentSubmission.objects.filter(
                assignment__teacher=teacher_profile,
                submitted_at__gte=today - django_timezone.timedelta(days=30)
            ).count()
            
            # Get upcoming exams (from examination app if available)
            try:
                from examination.models import Examination
                upcoming_exams = Examination.objects.filter(
                    created_by=teacher_profile,
                    exam_date__gte=today_date
                ).count()
            except (ImportError, AttributeError):
                upcoming_exams = 0
            
            # Overall statistics
            total_assignments_created = Assignment.objects.filter(teacher=teacher_profile).count()
            total_submissions_received = AssignmentSubmission.objects.filter(
                assignment__teacher=teacher_profile
            ).count()
            
            # Average grades
            avg_grade = AssignmentSubmission.objects.filter(
                assignment__teacher=teacher_profile,
                marks_obtained__isnull=False
            ).aggregate(
                avg_marks=models.Avg('marks_obtained')
            )['avg_marks'] or 0
            
            # Recent activities
            recent_sessions = AttendanceSession.objects.filter(
                teacher_assignment__teacher=teacher_profile
            ).order_by('-date', '-start_time')[:5]
            
            # Get parent messages
            from accounts.models import ParentTeacherMessage
            parent_messages = ParentTeacherMessage.objects.filter(
                recipient=request.user
            ).select_related('sender', 'student__user').order_by('-created_at')[:5]
            
            # Generate chart data as JSON for JavaScript
            chart_data = {
                'assignmentStats': [
                    {
                        'className': stat['class_name'],
                        'submissionRate': stat['submission_rate']
                    } for stat in assignment_stats
                ],
                'passingStats': [
                    {
                        'className': stat['class_name'],
                        'passingRate': stat['passing_rate']
                    } for stat in passing_stats
                ],
                'syllabusProgress': [
                    {
                        'subjectName': progress['subject_name'],
                        'progressPercentage': progress['progress_percentage']
                    } for progress in syllabus_progress
                ]
            }
            
            # Convert to JSON and mark as safe for template
            chart_data_json = mark_safe(f'<script>window.chartData = {json.dumps(chart_data)};</script>')
            
            # Get students with unpaid fees from teacher's classes
            from fees.models import StudentFee
            from academic.models import StudentEnrollment
            
            students_with_unpaid_fees = []
            for assignment in teacher_assignments:
                class_obj = assignment.class_assigned
                enrollments = StudentEnrollment.objects.filter(
                    class_enrolled=class_obj,
                    is_active=True
                ).select_related('student__user')
                
                for enrollment in enrollments:
                    unpaid_fees = StudentFee.objects.filter(
                        student=enrollment.student,
                        payment_status__in=['pending', 'partial', 'overdue']
                    ).select_related('fee_structure')
                    
                    if unpaid_fees.exists():
                        total_unpaid = sum(fee.balance_amount for fee in unpaid_fees)
                        students_with_unpaid_fees.append({
                            'student': enrollment.student,
                            'class': class_obj,
                            'total_unpaid': total_unpaid,
                            'fee_count': unpaid_fees.count()
                        })
            
            context.update({
                'teacher_assignments': teacher_assignments,
                'created_assignments': created_assignments,
                'today': today,
                'today_date': today_date,
                'todays_sessions': todays_sessions,
                'total_students': total_students,
                'total_subjects': total_subjects,
                'pending_assignments': pending_assignments,
                'upcoming_exams': upcoming_exams,
                'recent_sessions': recent_sessions,
                'parent_messages': parent_messages,
                # Enhanced statistics for charts
                'assignment_stats': assignment_stats,
                'passing_stats': passing_stats,
                'attendance_stats': attendance_stats,
                'syllabus_progress': syllabus_progress,
                'recent_assignment_count': recent_assignment_count,
                'recent_submissions_count': recent_submissions_count,
                'total_assignments_created': total_assignments_created,
                'total_submissions_received': total_submissions_received,
                'avg_grade': round(avg_grade, 1) if avg_grade else 0,
                # Chart data as JSON
                'chart_data_json': chart_data_json,
                # Fee information
                'students_with_unpaid_fees': students_with_unpaid_fees[:10],  # Limit to 10 for display
            })
            
        except TeacherProfile.DoesNotExist:
            # Handle case where teacher profile doesn't exist
            context.update({
                'teacher_assignments': [],
                'todays_sessions': [],
                'total_students': 0,
                'total_subjects': 0,
                'pending_assignments': 0,
                'upcoming_exams': 0,
                'recent_sessions': [],
                'profile_missing': True
            })
        
        return render(request, 'accounts/teacher_dashboard.html', context)
    elif user.user_type == 'parent':
        # Add parent-specific context
        try:
            parent_profile = user.parent_profile
            from academic.models import StudentEnrollment, Subject, Assignment
            from attendance.models import AttendanceRecord
            from notifications.models import Notification
            from examination.models import Examination, ExamResult
            from fees.models import StudentFee
            from datetime import timedelta
            
            # Get parent's children
            children_profiles = parent_profile.children.all()
            
            # DEBUG: Print to console
            print(f"[DEBUG] Parent: {user.username}, Children count: {children_profiles.count()}")
            
            # Prepare children data with their academic information
            children_data = []
            upcoming_events = []
            
            for child in children_profiles:
                # Get current enrollment
                enrollment = None
                try:
                    enrollment = child.get_current_enrollment()
                except Exception as e:
                    print(f"Error getting enrollment for {child}: {e}")
                
                # Get attendance data
                attendance_percentage = 0
                total_sessions = 0
                present_sessions = 0
                try:
                    attendance_records = AttendanceRecord.objects.filter(student=child)
                    total_sessions = attendance_records.count()
                    present_sessions = attendance_records.filter(status__in=['present', 'late']).count()
                    attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0
                except Exception as e:
                    print(f"Error getting attendance for {child}: {e}")
                
                # Check fee payment status
                has_unpaid_fees = False
                total_unpaid_amount = 0
                unpaid_fees = []
                
                try:
                    unpaid_fees = StudentFee.objects.filter(
                        student=child,
                        payment_status__in=['pending', 'partial', 'overdue']
                    ).select_related('fee_structure')
                    
                    has_unpaid_fees = unpaid_fees.exists()
                    total_unpaid_amount = sum(fee.balance_amount for fee in unpaid_fees) if has_unpaid_fees else 0
                except Exception as fee_error:
                    print(f"Error getting fees for {child}: {fee_error}")
                    # Continue without fee data if there's an error
                
                # Get subjects and grades for this child
                subjects_with_grades = []
                gpa = 0.0
                
                if enrollment:
                    try:
                        # Get subjects for the enrolled class
                        subjects = Subject.objects.filter(
                            course=enrollment.class_enrolled.course,
                            year=enrollment.class_enrolled.year,
                            semester=enrollment.class_enrolled.semester
                        )
                        
                        # Get results for each subject
                        for subject in subjects:
                            try:
                                # Get the latest result for this subject
                                result = ExamResult.objects.filter(
                                    student=child,
                                    examination__subject=subject
                                ).order_by('-examination__exam_date').first()
                                
                                if result:
                                    percentage = (float(result.marks_obtained) / result.examination.total_marks * 100) if result.examination.total_marks > 0 else 0
                                    
                                    subjects_with_grades.append({
                                        'name': subject.name,
                                        'grade': result.grade,
                                        'percentage': round(percentage, 1)
                                    })
                                else:
                                    subjects_with_grades.append({
                                        'name': subject.name,
                                        'grade': None,
                                        'percentage': 0
                                    })
                            except Exception as subject_error:
                                print(f"Error processing subject {subject}: {subject_error}")
                                subjects_with_grades.append({
                                    'name': subject.name,
                                    'grade': None,
                                    'percentage': 0
                                })
                        
                        # Calculate GPA from results (using same method as student dashboard)
                        try:
                            all_results = ExamResult.objects.filter(
                                student=child,
                                examination__subject__in=subjects
                            )
                            if all_results.exists():
                                # Grade point scale (same as student dashboard)
                                grade_points = {
                                    'A+': 4.0, 'A': 3.7, 'B+': 3.3, 'B': 3.0,
                                    'C+': 2.3, 'C': 2.0, 'D': 1.0, 'F': 0.0
                                }
                                
                                # Weighted GPA calculation (based on exam total marks)
                                weighted_points_sum = 0
                                total_credits = 0
                                
                                for result in all_results:
                                    grade_point = grade_points.get(result.grade, 0.0)
                                    credit = result.examination.total_marks
                                    weighted_points_sum += grade_point * credit
                                    total_credits += credit
                                
                                gpa = (weighted_points_sum / total_credits) if total_credits > 0 else 0.0
                                gpa = round(gpa, 2)
                        except Exception as e:
                            print(f"Error calculating GPA for {child}: {e}")
                        
                        # Get upcoming exams for this child
                        try:
                            today = django_timezone.now().date()
                            upcoming_exams = Examination.objects.filter(
                                subject__in=subjects,
                                exam_date__gte=today,
                                exam_date__lte=today + timedelta(days=30)
                            ).order_by('exam_date')[:5]
                            
                            for exam in upcoming_exams:
                                days_until = (exam.exam_date - today).days
                                if days_until <= 3:
                                    color_class = 'danger'
                                elif days_until <= 7:
                                    color_class = 'warning'
                                else:
                                    color_class = 'info'
                                
                                upcoming_events.append({
                                    'title': f"{exam.exam_type.name} - {exam.subject.name}",
                                    'description': f"{child.user.get_full_name()}'s exam",
                                    'date': exam.exam_date,
                                    'child_name': child.user.get_full_name(),
                                    'color_class': color_class
                                })
                        except Exception as e:
                            print(f"Error getting upcoming exams for {child}: {e}")
                        
                        # Get upcoming assignments
                        try:
                            today = django_timezone.now().date()
                            upcoming_assignments = Assignment.objects.filter(
                                class_assigned=enrollment.class_enrolled,
                                due_date__gte=today,
                                due_date__lte=today + timedelta(days=30),
                                is_active=True
                            ).order_by('due_date')[:5]
                            
                            for assignment in upcoming_assignments:
                                days_until = (assignment.due_date - today).days
                                if days_until <= 2:
                                    color_class = 'danger'
                                elif days_until <= 5:
                                    color_class = 'warning'
                                else:
                                    color_class = 'primary'
                                
                                upcoming_events.append({
                                    'title': f"Assignment: {assignment.title}",
                                    'description': f"{child.user.get_full_name()} - {assignment.subject.name}",
                                    'date': assignment.due_date,
                                    'child_name': child.user.get_full_name(),
                                    'color_class': color_class
                                })
                        except Exception as e:
                            print(f"Error getting upcoming assignments for {child}: {e}")
                    except Exception as e:
                        print(f"Error processing subjects for {child}: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Always add child info, even if some data is missing
                absent_sessions = total_sessions - present_sessions
                child_info = {
                    'profile': child,
                    'user': child.user,
                    'enrollment': enrollment,
                    'attendance_percentage': round(attendance_percentage, 2),
                    'gpa': round(gpa, 2),
                    'total_sessions': total_sessions,
                    'present_sessions': present_sessions,
                    'absent_sessions': absent_sessions,
                    'subjects': subjects_with_grades,
                    'has_unpaid_fees': has_unpaid_fees,
                    'unpaid_fees': unpaid_fees,
                    'total_unpaid_amount': total_unpaid_amount
                }
                children_data.append(child_info)
                print(f"[DEBUG] Added child: {child.user.get_full_name()}, Enrollment: {enrollment}, Subjects: {len(subjects_with_grades)}")
            
            # Sort upcoming events by date
            upcoming_events.sort(key=lambda x: x['date'])
            
            # Check if any child has unpaid fees
            any_child_has_unpaid_fees = any(child_info['has_unpaid_fees'] for child_info in children_data)
            
            # Get recent notifications for parent's children
            child_user_ids = [child.user.id for child in children_profiles]
            recent_notifications = Notification.objects.filter(
                recipients__in=child_user_ids
            ).order_by('-created_at').distinct()[:5] if child_user_ids else []
            
            context.update({
                'children_profiles': children_profiles,
                'children_data': children_data,
                'recent_notifications': recent_notifications,
                'upcoming_events': upcoming_events[:10],  # Limit to 10 events
                'today': django_timezone.now().date(),
                'any_child_has_unpaid_fees': any_child_has_unpaid_fees
            })
            
            print(f"[DEBUG] Context updated - children_data count: {len(children_data)}")
            
        except ParentProfile.DoesNotExist:
            print(f"[DEBUG] ParentProfile.DoesNotExist for user: {user.username}")
            context.update({
                'children_profiles': [],
                'children_data': [],
                'recent_notifications': [],
                'upcoming_events': [],
                'profile_missing': True,
                'today': django_timezone.now().date()
            })
        except Exception as e:
            # Log the error for debugging
            print(f"[DEBUG] Error in parent dashboard: {e}")
            import traceback
            traceback.print_exc()
            context.update({
                'children_profiles': [],
                'children_data': [],
                'recent_notifications': [],
                'upcoming_events': [],
                'error_message': str(e),
                'today': django_timezone.now().date()
            })
        
        return render(request, 'accounts/parent_dashboard.html', context)
    
    # Fallback for any edge cases
    return render(request, 'accounts/dashboard.html', context)

@login_required
def profile(request):
    if not validate_request_tenant_access(request):
        return redirect('accounts:login')

    user = request.user
    profile_obj = None
    
    try:
        if user.user_type == 'student':
            profile_obj = user.student_profile
        elif user.user_type == 'teacher':
            profile_obj = user.teacher_profile
        elif user.user_type == 'parent':
            profile_obj = user.parent_profile
        elif user.user_type == 'admin':
            profile_obj = user.admin_profile
    except (StudentProfile.DoesNotExist, TeacherProfile.DoesNotExist, 
            ParentProfile.DoesNotExist, AdminProfile.DoesNotExist):
        profile_obj = None
    
    context = {
        'user': user,
        'profile': profile_obj,
        'profile_missing': profile_obj is None
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
@user_passes_test(is_admin)
def admin_create_user(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST, request.FILES)
        
        if user_form.is_valid():
            # Make sure we're using the correct tenant database
            organization = get_request_organization(request)
            if organization:
                from saas.db_router import set_tenant_db
                set_tenant_db(organization.id)
            
            with transaction.atomic():
                user = user_form.save(commit=False)
                # Don't assign organization_id in tenant database
                user.organization_id = None
                user.save()
                
                # Create profile based on user type
                if user.user_type == 'student':
                    StudentProfile.objects.create(
                        user=user,
                        student_id=f"STU{user.id:06d}",
                        admission_date=user.date_joined.date(),
                        guardian_name="",
                        guardian_phone="",
                        guardian_email="",
                        emergency_contact=""
                    )
                elif user.user_type == 'teacher':
                    TeacherProfile.objects.create(
                        user=user,
                        employee_id=f"EMP{user.id:06d}",
                        qualification="",
                        specialization="",
                        joining_date=user.date_joined.date()
                    )
                elif user.user_type == 'parent':
                    ParentProfile.objects.create(
                        user=user,
                        occupation=""
                    )
                elif user.user_type == 'admin':
                    AdminProfile.objects.create(
                        user=user,
                        employee_id=f"ADM{user.id:06d}",
                        department=""
                    )
                
                messages.success(request, f'{user.get_user_type_display()} account created successfully!')
                return redirect('accounts:admin_user_list')
    else:
        user_form = UserRegistrationForm()
    
    return render(request, 'accounts/admin_create_user.html', {'form': user_form})

@login_required
@user_passes_test(is_admin)
def admin_user_list(request):
    search = request.GET.get('search', '')
    
    # Base queryset excluding admin users
    base_users = get_tenant_user_queryset(request).exclude(user_type='admin')
    
    if search:
        base_users = base_users.filter(
            models.Q(username__icontains=search) |
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(email__icontains=search)
        )
    
    # Group users by type
    grouped_users = {
        'parents': base_users.filter(user_type='parent').order_by('-date_joined'),
        'teachers': base_users.filter(user_type='teacher').order_by('-date_joined'),
        'students': base_users.filter(user_type='student').order_by('-date_joined'),
    }
    
    # Get counts for each type
    user_counts = {
        'parents': grouped_users['parents'].count(),
        'teachers': grouped_users['teachers'].count(),
        'students': grouped_users['students'].count(),
        'total': sum([grouped_users['parents'].count(), grouped_users['teachers'].count(), grouped_users['students'].count()])
    }
    
    context = {
        'grouped_users': grouped_users,
        'user_counts': user_counts,
        'search': search,
    }
    
    return render(request, 'accounts/admin_user_list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_edit_user(request, user_id):
    user = get_object_or_404(get_tenant_user_queryset(request), id=user_id)
    
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST, request.FILES, instance=user)
        
        if user_form.is_valid():
            updated_user = user_form.save(commit=False)
            if user.organization_id:
                updated_user.organization = user.organization
            updated_user.save()
            messages.success(request, f'{user.get_user_type_display()} account updated successfully!')
            return redirect('accounts:admin_user_list')
    else:
        user_form = UserRegistrationForm(instance=user)
    
    context = {
        'form': user_form,
        'user_obj': user
    }
    
    return render(request, 'accounts/admin_edit_user.html', context)

@login_required
@user_passes_test(is_admin)
def admin_delete_user(request, user_id):
    user = get_object_or_404(get_tenant_user_queryset(request), id=user_id)
    
    if request.method == 'POST':
        user_name = user.get_full_name() or user.username
        user.delete()
        messages.success(request, f'User "{user_name}" deleted successfully!')
        return redirect('accounts:admin_user_list')
    
    context = {'user_obj': user}
    return render(request, 'accounts/admin_delete_user.html', context)

@login_required
@user_passes_test(is_admin)
def admin_reset_password(request, user_id):
    user_obj = get_object_or_404(get_tenant_user_queryset(request), id=user_id)
    
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            user_obj.set_password(new_password)
            user_obj.save()
            
            messages.success(
                request, 
                f'Password for "{user_obj.get_full_name() or user_obj.username}" has been reset successfully!'
            )
            return redirect('accounts:admin_user_list')
    else:
        form = AdminPasswordResetForm()
    
    context = {
        'form': form,
        'user_obj': user_obj
    }
    return render(request, 'accounts/admin_reset_password.html', context)

