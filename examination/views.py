from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.utils import timezone
from .models import Examination, ExamResult, ExamType
from .forms import ExaminationForm, ExamResultForm
from accounts.models import StudentProfile, TeacherProfile
from academic.models import StudentEnrollment

def is_teacher_or_admin(user):
    return user.is_authenticated and user.user_type in ['admin', 'teacher']

@login_required
def exam_list(request):
    """List all exams based on user type"""
    if request.user.user_type == 'student':
        # Show exams for student's enrolled class
        try:
            enrollment = request.user.student_profile.get_current_enrollment()
            if enrollment:
                exams = Examination.objects.filter(
                    class_for=enrollment.class_enrolled
                ).select_related('subject', 'exam_type', 'created_by__user')
            else:
                exams = Examination.objects.none()
        except (StudentProfile.DoesNotExist, AttributeError):
            exams = Examination.objects.none()
    elif request.user.user_type == 'teacher':
        # Show exams created by this teacher
        if hasattr(request.user, 'teacher_profile'):
            exams = Examination.objects.filter(
                created_by=request.user.teacher_profile
            ).select_related('subject', 'exam_type', 'class_for')
        else:
            exams = Examination.objects.none()
    else:  # admin
        # Show all exams
        exams = Examination.objects.all().select_related('subject', 'exam_type', 'created_by__user', 'class_for')
    
    context = {
        'exams': exams.order_by('-exam_date'),
        'can_create': request.user.user_type in ['admin', 'teacher'],
        'today': timezone.now().date()
    }
    return render(request, 'examination/exam_list.html', context)

@login_required
def result_list(request):
    """List exam results based on user type"""
    if request.user.user_type == 'student':
        # Check fee payment status first
        from fees.models import StudentFee
        unpaid_fees = StudentFee.objects.filter(
            student=request.user.student_profile,
            payment_status__in=['pending', 'partial', 'overdue']
        ).select_related('fee_structure')
        
        has_unpaid_fees = unpaid_fees.exists()
        total_unpaid_amount = sum(fee.balance_amount for fee in unpaid_fees)
        
        # If fees are unpaid, show warning and restrict access
        if has_unpaid_fees:
            context = {
                'has_unpaid_fees': True,
                'unpaid_fees': unpaid_fees,
                'total_unpaid_amount': total_unpaid_amount,
                'results': [],
                'student_stats': {
                    'total_exams': 0,
                    'average_percentage': 0,
                    'gpa': 0.0,
                    'overall_grade': 'N/A'
                }
            }
            return render(request, 'examination/result_list.html', context)
        
        # Show only student's own results
        results = ExamResult.objects.filter(
            student=request.user.student_profile
        ).select_related('examination__subject', 'examination__exam_type')
        
        # Add percentage calculation to each result
        results_with_percentage = []
        for result in results:
            percentage = (float(result.marks_obtained) / result.examination.total_marks) * 100
            result.percentage = round(percentage, 1)
            results_with_percentage.append(result)
        
        # Calculate student statistics
        if results.exists():
            total_exams = results.count()
            
            # Calculate average percentage
            total_marks_sum = sum(result.examination.total_marks for result in results)
            obtained_marks_sum = sum(float(result.marks_obtained) for result in results)
            overall_percentage = (obtained_marks_sum / total_marks_sum * 100) if total_marks_sum > 0 else 0
            
            # Calculate GPA using weighted average based on exam total marks
            # This gives more weight to exams with higher total marks
            grade_points = {
                'A+': 4.0, 'A': 3.7, 'B+': 3.3, 'B': 3.0,
                'C+': 2.3, 'C': 2.0, 'D': 1.0, 'F': 0.0
            }
            
            # Weighted GPA calculation
            weighted_points_sum = 0
            total_credits = 0
            
            for result in results:
                grade_point = grade_points.get(result.grade, 0.0)
                # Use total marks as credit/weight
                credit = result.examination.total_marks
                weighted_points_sum += grade_point * credit
                total_credits += credit
            
            gpa = (weighted_points_sum / total_credits) if total_credits > 0 else 0.0
            
            # Alternative: Simple average GPA (uncomment to use this instead)
            # total_points = sum(grade_points.get(result.grade, 0.0) for result in results)
            # gpa = total_points / total_exams if total_exams > 0 else 0.0
            
            # Determine overall grade based on overall percentage
            if overall_percentage >= 90:
                overall_grade = 'A+'
            elif overall_percentage >= 80:
                overall_grade = 'A'
            elif overall_percentage >= 70:
                overall_grade = 'B+'
            elif overall_percentage >= 60:
                overall_grade = 'B'
            elif overall_percentage >= 50:
                overall_grade = 'C+'
            elif overall_percentage >= 40:
                overall_grade = 'C'
            elif overall_percentage >= 30:
                overall_grade = 'D'
            else:
                overall_grade = 'F'
            
            student_stats = {
                'total_exams': total_exams,
                'average_percentage': round(overall_percentage, 1),
                'gpa': round(gpa, 2),
                'overall_grade': overall_grade
            }
        else:
            student_stats = {
                'total_exams': 0,
                'average_percentage': 0,
                'gpa': 0.0,
                'overall_grade': 'N/A'
            }
        
        context = {
            'results': results_with_percentage,
            'student_stats': student_stats
        }
        
    elif request.user.user_type == 'teacher':
        # Show results for exams created by this teacher
        if hasattr(request.user, 'teacher_profile'):
            results = ExamResult.objects.filter(
                examination__created_by=request.user.teacher_profile
            ).select_related('student__user', 'examination__subject', 'examination__exam_type')
        else:
            results = ExamResult.objects.none()
        
        # Add percentage calculation to each result
        results_with_percentage = []
        for result in results:
            percentage = (float(result.marks_obtained) / result.examination.total_marks) * 100
            result.percentage = round(percentage, 1)
            results_with_percentage.append(result)
        
        context = {
            'results': results_with_percentage,
            'can_manage': True
        }
        
    else:  # admin
        # Show all results
        results = ExamResult.objects.all().select_related(
            'student__user', 'examination__subject', 'examination__exam_type', 'examination__created_by__user'
        )
        
        # Add percentage calculation to each result
        results_with_percentage = []
        for result in results:
            percentage = (float(result.marks_obtained) / result.examination.total_marks) * 100
            result.percentage = round(percentage, 1)
            results_with_percentage.append(result)
        
        context = {
            'results': results_with_percentage,
            'can_manage': True
        }
    
    return render(request, 'examination/result_list.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def create_exam(request):
    """Create a new examination"""
    # Check if user is authorized
    if not is_teacher_or_admin(request.user):
        messages.error(request, 'You do not have permission to create exams.')
        return redirect('accounts:dashboard')
    
    # Get teacher profile if user is a teacher, otherwise None for admin
    teacher_profile = None
    if request.user.user_type == 'teacher':
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, 'Teacher profile not found. Please contact the administrator.')
            return redirect('accounts:dashboard')
        teacher_profile = request.user.teacher_profile
    
    if request.method == 'POST':
        form = ExaminationForm(request.POST, teacher=teacher_profile)
        if form.is_valid():
            exam = form.save(commit=False)
            # Set created_by based on user type
            if teacher_profile:
                exam.created_by = teacher_profile
            else:
                # For admin users, try to assign to first available teacher or leave None
                from accounts.models import TeacherProfile
                first_teacher = TeacherProfile.objects.first()
                if first_teacher:
                    exam.created_by = first_teacher
            exam.save()
            messages.success(request, f'Exam "{exam.name}" created successfully!')
            return redirect('examination:exam_list')
    else:
        form = ExaminationForm(teacher=teacher_profile)
    
    context = {'form': form}
    return render(request, 'examination/create_exam.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def enter_results(request, exam_id):
    """Enter results for an examination"""
    exam = get_object_or_404(Examination, id=exam_id)
    
    # Check if user has permission to enter results for this exam
    if request.user.user_type == 'teacher':
        if not hasattr(request.user, 'teacher_profile'):
            messages.error(request, 'Teacher profile not found. Please contact the administrator.')
            return redirect('examination:exam_list')
        if exam.created_by != request.user.teacher_profile:
            messages.error(request, 'You do not have permission to enter results for this exam.')
            return redirect('examination:exam_list')
    elif request.user.user_type != 'admin':
        messages.error(request, 'You do not have permission to enter results.')
        return redirect('examination:exam_list')
    
    # Get students enrolled in the exam's class
    enrollments = StudentEnrollment.objects.filter(
        class_enrolled=exam.class_for,
        is_active=True
    ).select_related('student__user')
    
    # Get existing results
    existing_results = {}
    for result in ExamResult.objects.filter(examination=exam):
        existing_results[result.student.id] = result
    
    if request.method == 'POST':
        results_saved = 0
        for enrollment in enrollments:
            student = enrollment.student
            marks_key = f'marks_{student.id}'
            remarks_key = f'remarks_{student.id}'
            
            if marks_key in request.POST:
                try:
                    marks = float(request.POST[marks_key])
                    remarks = request.POST.get(remarks_key, '')
                    
                    # Determine who entered the result
                    entered_by = None
                    if request.user.user_type == 'teacher' and hasattr(request.user, 'teacher_profile'):
                        entered_by = request.user.teacher_profile
                    elif request.user.user_type == 'admin':
                        # For admin, use the exam creator or first available teacher
                        entered_by = exam.created_by
                        if not entered_by:
                            from accounts.models import TeacherProfile
                            entered_by = TeacherProfile.objects.first()
                    
                    # Create or update result
                    result, created = ExamResult.objects.get_or_create(
                        examination=exam,
                        student=student,
                        defaults={
                            'marks_obtained': marks,
                            'remarks': remarks,
                            'entered_by': entered_by
                        }
                    )
                    
                    if not created:
                        result.marks_obtained = marks
                        result.remarks = remarks
                        result.entered_by = entered_by
                        result.save()
                    
                    results_saved += 1
                    
                except ValueError:
                    continue
        
        messages.success(request, f'Results saved for {results_saved} students!')
        return redirect('examination:result_list')
    
    # Prepare student data with existing results
    students_data = []
    for enrollment in enrollments:
        existing_result = existing_results.get(enrollment.student.id)
        students_data.append({
            'student': enrollment.student,
            'existing_marks': existing_result.marks_obtained if existing_result else '',
            'existing_remarks': existing_result.remarks if existing_result else ''
        })
    
    context = {
        'exam': exam,
        'students_data': students_data
    }
    
    return render(request, 'examination/enter_results.html', context)