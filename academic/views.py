from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from accounts.models import StudentProfile, TeacherProfile
from saas.utils import get_request_organization
from .models import (
    AcademicYear, Department, Course, Subject, Class, 
    StudentEnrollment, TeacherSubjectAssignment, Assignment, AssignmentSubmission
)
from .forms import (
    AcademicYearForm, DepartmentForm, CourseForm, EnhancedCourseForm, SubjectForm, ClassForm,
    StudentEnrollmentForm, TeacherSubjectAssignmentForm, AssignmentForm, 
    AssignmentSubmissionForm, ClassFilterForm
)
from accounts.models import StudentProfile, TeacherProfile


def get_current_organization(request):
    return get_request_organization(request) or getattr(request.user, 'organization', None)


def scope_academic_queryset(queryset, request):
    organization = get_current_organization(request)
    if organization and any(field.name == 'organization' for field in queryset.model._meta.fields):
        return queryset.filter(organization=organization)
    return queryset


def scope_profile_queryset(queryset, request):
    organization = get_current_organization(request)
    if organization:
        return queryset.filter(user__organization=organization)
    return queryset


def assign_organization(instance, request):
    organization = get_current_organization(request)
    if organization and hasattr(instance, 'organization_id') and instance.organization_id is None:
        instance.organization = organization
    return instance

def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

def is_teacher_or_admin(user):
    return user.is_authenticated and user.user_type in ['admin', 'teacher']

@login_required
def department_list(request):
    departments = scope_academic_queryset(Department.objects.all(), request).annotate(
        course_count=Count('course'),
        teacher_count=Count('course__subject__teachersubjectassignment__teacher', distinct=True)
    )
    
    context = {
        'departments': departments,
        'can_manage': request.user.user_type == 'admin'
    }
    return render(request, 'academic/department_list.html', context)

@login_required
@user_passes_test(is_admin)
def create_department(request):
    """Create a new department"""
    if request.method == 'POST':
        form = DepartmentForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            department = form.save(commit=False)
            assign_organization(department, request)
            department.save()
            messages.success(request, f'Department "{department.name}" created successfully!')
            return redirect('academic:department_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DepartmentForm(organization=get_current_organization(request))
    
    context = {
        'form': form,
        'title': 'Create Department',
        'submit_text': 'Create Department'
    }
    return render(request, 'academic/department_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_department(request, department_id):
    """Edit an existing department"""
    department = get_object_or_404(scope_academic_queryset(Department.objects.all(), request), id=department_id)
    
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department, organization=get_current_organization(request))
        if form.is_valid():
            department = form.save()
            messages.success(request, f'Department "{department.name}" updated successfully!')
            return redirect('academic:department_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DepartmentForm(instance=department, organization=get_current_organization(request))
    
    context = {
        'form': form,
        'department': department,
        'title': f'Edit Department - {department.name}',
        'submit_text': 'Update Department'
    }
    return render(request, 'academic/department_form.html', context)

@login_required
@user_passes_test(is_admin)
def delete_department(request, department_id):
    """Delete a department"""
    department = get_object_or_404(scope_academic_queryset(Department.objects.all(), request), id=department_id)
    
    if request.method == 'POST':
        # Check if department has courses
        course_count = department.course_set.count()
        if course_count > 0:
            messages.error(request, f'Cannot delete department "{department.name}" because it has {course_count} course(s) associated with it.')
            return redirect('academic:department_list')
        
        department_name = department.name
        department.delete()
        messages.success(request, f'Department "{department_name}" deleted successfully!')
        return redirect('academic:department_list')
    
    # Get related data for confirmation
    courses = department.course_set.all()
    
    context = {
        'department': department,
        'courses': courses,
        'course_count': courses.count()
    }
    return render(request, 'academic/department_confirm_delete.html', context)

@login_required
def course_list(request):
    courses = scope_academic_queryset(Course.objects.select_related('department'), request).annotate(
        subject_count=Count('subject'),
        student_count=Count('class__studentenrollment', filter=Q(class__studentenrollment__is_active=True), distinct=True)
    )
    
    # Calculate summary statistics
    total_courses = courses.count()
    total_students = sum(course.student_count for course in courses)
    total_subjects = sum(course.subject_count for course in courses)
    avg_students_per_course = round(total_students / total_courses, 1) if total_courses > 0 else 0
    
    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_subjects': total_subjects,
        'avg_students_per_course': avg_students_per_course,
        'can_manage': request.user.user_type == 'admin'
    }
    return render(request, 'academic/course_list.html', context)

@login_required
def subject_list(request):
    subjects = scope_academic_queryset(Subject.objects.select_related('course', 'course__department'), request)
    
    # Filter based on user type
    if request.user.user_type == 'teacher':
        # Show only subjects assigned to this teacher
        teacher_assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
            teacher=request.user.teacher_profile
        )
        subjects = subjects.filter(
            id__in=teacher_assignments.values_list('subject_id', flat=True)
        )
    elif request.user.user_type == 'student':
        # Show only subjects for student's class
        try:
            enrollment = request.user.student_profile.get_current_enrollment()
            if enrollment:
                subjects = subjects.filter(
                    course=enrollment.class_enrolled.course,
                    year=enrollment.class_enrolled.year,
                    semester=enrollment.class_enrolled.semester
                )
            else:
                subjects = subjects.none()
        except (StudentProfile.DoesNotExist, AttributeError):
            subjects = Subject.objects.none()
    
    # Calculate statistics
    total_credits = sum(subject.credits for subject in subjects)
    semester_stats = {}
    for subject in subjects:
        if subject.semester not in semester_stats:
            semester_stats[subject.semester] = {'count': 0, 'credits': 0}
        semester_stats[subject.semester]['count'] += 1
        semester_stats[subject.semester]['credits'] += subject.credits
    
    context = {
        'subjects': subjects.order_by('semester', 'year', 'name'),
        'can_manage': request.user.user_type == 'admin',
        'total_credits': total_credits,
        'semester_stats': semester_stats
    }
    return render(request, 'academic/subject_list.html', context)

@login_required
def class_list(request):
    classes = scope_academic_queryset(Class.objects.select_related(
        'course', 'course__department', 'academic_year', 'class_teacher__user'
    ), request).annotate(
        student_count=Count('studentenrollment', filter=Q(studentenrollment__is_active=True))
    )
    
    # Apply filters
    filter_form = ClassFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data['course']:
            classes = classes.filter(course=filter_form.cleaned_data['course'])
        if filter_form.cleaned_data['year']:
            classes = classes.filter(year=filter_form.cleaned_data['year'])
        if filter_form.cleaned_data['semester']:
            classes = classes.filter(semester=filter_form.cleaned_data['semester'])
        if filter_form.cleaned_data['academic_year']:
            classes = classes.filter(academic_year=filter_form.cleaned_data['academic_year'])
    
    # Filter based on user type
    if request.user.user_type == 'teacher':
        # Show only classes assigned to this teacher
        teacher_assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
            teacher=request.user.teacher_profile
        )
        classes = classes.filter(
            id__in=teacher_assignments.values_list('class_assigned_id', flat=True)
        )
    elif request.user.user_type == 'student':
        # Show only student's class
        try:
            enrollment = request.user.student_profile.get_current_enrollment()
            if enrollment:
                classes = classes.filter(id=enrollment.class_enrolled.id)
            else:
                classes = Class.objects.none()
        except (StudentProfile.DoesNotExist, AttributeError):
            classes = Class.objects.none()
    
    context = {
        'classes': classes,
        'filter_form': filter_form,
        'can_manage': request.user.user_type == 'admin'
    }
    return render(request, 'academic/class_list.html', context)

@login_required
def enrollment_list(request):
    enrollments = scope_academic_queryset(StudentEnrollment.objects.select_related(
        'student__user', 'class_enrolled__course', 'class_enrolled__academic_year'
    ), request)
    
    # Filter based on user type
    if request.user.user_type == 'teacher':
        # Show only enrollments for classes taught by this teacher
        teacher_assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
            teacher=request.user.teacher_profile
        )
        enrollments = enrollments.filter(
            class_enrolled__id__in=teacher_assignments.values_list('class_assigned_id', flat=True)
        )
    elif request.user.user_type == 'student':
        # Show only student's own enrollment
        enrollments = enrollments.filter(student=request.user.student_profile)
    
    context = {
        'enrollments': enrollments,
        'can_manage': request.user.user_type == 'admin'
    }
    return render(request, 'academic/enrollment_list.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def assignment_list(request):
    from django.utils import timezone
    from django.db.models import Q
    
    today = timezone.now()
    
    # Base queryset
    assignments = scope_academic_queryset(Assignment.objects.select_related(
        'subject', 'class_assigned', 'teacher__user'
    ), request).annotate(
        submission_count=Count('assignmentsubmission')
    )
    
    # Filter based on user type
    if request.user.user_type == 'teacher':
        assignments = assignments.filter(teacher=request.user.teacher_profile)
    
    # Apply filters from request
    subject_filter = request.GET.get('subject')
    type_filter = request.GET.get('assignment_type')
    status_filter = request.GET.get('status')
    
    if subject_filter:
        assignments = assignments.filter(subject_id=subject_filter)
    
    if type_filter:
        assignments = assignments.filter(assignment_type=type_filter)
    
    if status_filter:
        if status_filter == 'active':
            assignments = assignments.filter(is_active=True)
        elif status_filter == 'inactive':
            assignments = assignments.filter(is_active=False)
    
    # Order by due date
    assignments = assignments.order_by('-assigned_date', 'due_date')
    
    # Get subjects for filter dropdown
    if request.user.user_type == 'teacher':
        teacher_assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request).filter(teacher=request.user.teacher_profile)
        subjects = scope_academic_queryset(Subject.objects.all(), request).filter(id__in=teacher_assignments.values_list('subject_id', flat=True))
    else:
        subjects = scope_academic_queryset(Subject.objects.all(), request)
    
    # Calculate statistics
    active_count = assignments.filter(is_active=True).count()
    overdue_count = assignments.filter(due_date__lt=today, is_active=True).count()
    total_submissions = sum(assignment.submission_count for assignment in assignments)
    
    context = {
        'assignments': assignments,
        'subjects': subjects,
        'subject_filter': subject_filter,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'active_count': active_count,
        'overdue_count': overdue_count,
        'total_submissions': total_submissions,
        'today': today,
        'can_create': request.user.user_type in ['admin', 'teacher']
    }
    return render(request, 'academic/assignment_list.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def create_assignment(request):
    teacher_profile = getattr(request.user, 'teacher_profile', None) if request.user.user_type == 'teacher' else None
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, teacher=teacher_profile, organization=get_current_organization(request))
        if form.is_valid():
            assignment = form.save(commit=False)
            if teacher_profile:
                assignment.teacher = teacher_profile
            assign_organization(assignment, request)
            assignment.save()
            messages.success(request, 'Assignment created successfully!')
            return redirect('academic:assignment_list')
    else:
        form = AssignmentForm(teacher=teacher_profile, organization=get_current_organization(request))
    
    context = {'form': form}
    return render(request, 'academic/create_assignment.html', context)

@login_required
def student_assignments(request):
    """View for students to see their assignments"""
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    try:
        enrollment = request.user.student_profile.get_current_enrollment()
        
        if enrollment:
            assignments = scope_academic_queryset(Assignment.objects.all(), request).filter(
                class_assigned=enrollment.class_enrolled,
                is_active=True
            ).select_related('subject', 'teacher__user').order_by('-assigned_date')
        else:
            assignments = Assignment.objects.none()
        
        # Get submission status for each assignment
        assignment_data = []
        submitted_count = 0
        pending_count = 0
        overdue_count = 0
        
        for assignment in assignments:
            try:
                submission = AssignmentSubmission.objects.get(
                    assignment=assignment,
                    student=request.user.student_profile
                )
            except AssignmentSubmission.DoesNotExist:
                submission = None
            
            is_overdue = assignment.due_date < timezone.now() if not submission else False
            
            assignment_data.append({
                'assignment': assignment,
                'submission': submission,
                'is_overdue': is_overdue
            })
            
            # Count statistics
            if submission:
                submitted_count += 1
            elif is_overdue:
                overdue_count += 1
            else:
                pending_count += 1
        
        context = {
            'assignment_data': assignment_data,
            'enrollment': enrollment,
            'submitted_count': submitted_count,
            'pending_count': pending_count,
            'overdue_count': overdue_count
        }
        
    except StudentEnrollment.DoesNotExist:
        messages.error(request, 'You are not enrolled in any class.')
        context = {'assignment_data': []}
    
    return render(request, 'academic/student_assignments.html', context)

@login_required
def course_detail(request, course_id):
    """Detailed view of a course with students and teachers"""
    course = get_object_or_404(scope_academic_queryset(Course.objects.all(), request), id=course_id)
    
    # Get classes for this course
    classes = scope_academic_queryset(Class.objects.all(), request).filter(course=course).annotate(
        student_count=Count('studentenrollment', filter=Q(studentenrollment__is_active=True))
    )
    
    # Get subjects for this course
    subjects = scope_academic_queryset(Subject.objects.all(), request).filter(course=course).prefetch_related('teachersubjectassignment_set__teacher__user')
    
    # Get teacher assignments for this course
    teacher_assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
        subject__course=course
    ).select_related('teacher__user', 'subject', 'class_assigned')
    
    # Calculate statistics
    total_students = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
        class_enrolled__course=course,
        is_active=True
    ).count()
    
    total_teachers = teacher_assignments.values('teacher').distinct().count()
    
    context = {
        'course': course,
        'classes': classes,
        'subjects': subjects,
        'teacher_assignments': teacher_assignments,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'can_manage': request.user.user_type == 'admin'
    }
    
    return render(request, 'academic/course_detail.html', context)

@login_required
@user_passes_test(is_admin)
def create_course(request):
    """Create a new course"""
    if request.method == 'POST':
        form = CourseForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            course = form.save(commit=False)
            assign_organization(course, request)
            course.save()
            messages.success(request, f'Course "{course.name}" created successfully!')
            return redirect('academic:course_detail', course_id=course.id)
    else:
        form = CourseForm(organization=get_current_organization(request))
    
    context = {'form': form, 'title': 'Create New Course'}
    return render(request, 'academic/course_form.html', context)

@login_required
@user_passes_test(is_admin)
def create_course_enhanced(request):
    """Enhanced course creation with subjects, classes, and student enrollment"""
    if request.method == 'POST':
        # Handle course creation
        course_form = EnhancedCourseForm(request.POST, organization=get_current_organization(request))
        
        if course_form.is_valid():
            course = course_form.save(commit=False)
            assign_organization(course, request)
            course.save()
            
            # Process subjects
            subjects_data = []
            subject_count = 0
            
            # Count how many subjects were submitted
            for key in request.POST.keys():
                if key.startswith('subject_name_'):
                    subject_count += 1
            
            # Process each subject
            for i in range(subject_count):
                subject_name = request.POST.get(f'subject_name_{i}')
                subject_code = request.POST.get(f'subject_code_{i}')
                subject_year = request.POST.get(f'subject_year_{i}')
                subject_semester = request.POST.get(f'subject_semester_{i}')
                subject_credits = request.POST.get(f'subject_credits_{i}')
                
                if subject_name and subject_code and subject_year and subject_semester:
                    try:
                        subject = Subject.objects.create(
                            organization=get_current_organization(request),
                            name=subject_name,
                            code=subject_code,
                            course=course,
                            year=int(subject_year),
                            semester=int(subject_semester),
                            credits=int(subject_credits) if subject_credits else 3
                        )
                        subjects_data.append(subject)
                    except Exception as e:
                        messages.error(request, f'Error creating subject {subject_name}: {str(e)}')
            
            # Process classes and store them for student enrollment
            classes_data = []
            class_count = 0
            
            # Count how many classes were submitted
            for key in request.POST.keys():
                if key.startswith('class_name_'):
                    class_count += 1
            
            # Process each class
            for i in range(class_count):
                class_name = request.POST.get(f'class_name_{i}')
                class_year = request.POST.get(f'class_year_{i}')
                class_semester = request.POST.get(f'class_semester_{i}')
                class_section = request.POST.get(f'class_section_{i}')
                class_academic_year = request.POST.get(f'class_academic_year_{i}')
                class_teacher = request.POST.get(f'class_teacher_{i}')
                
                if class_name and class_year and class_semester and class_section and class_academic_year:
                    try:
                        academic_year = get_object_or_404(scope_academic_queryset(AcademicYear.objects.all(), request), id=class_academic_year)
                        teacher = get_object_or_404(scope_profile_queryset(TeacherProfile.objects.all(), request), id=class_teacher) if class_teacher else None
                        
                        class_obj = Class.objects.create(
                            organization=get_current_organization(request),
                            name=class_name,
                            course=course,
                            year=int(class_year),
                            semester=int(class_semester),
                            section=class_section,
                            academic_year=academic_year,
                            class_teacher=teacher
                        )
                        classes_data.append((i, class_obj))  # Store index and class object
                    except Exception as e:
                        messages.error(request, f'Error creating class {class_name}: {str(e)}')
            
            # Process student enrollments
            enrollment_count = 0
            enrolled_students = 0
            
            # Count how many students were submitted
            for key in request.POST.keys():
                if key.startswith('student_') and not key.startswith('student_class_'):
                    enrollment_count += 1
            
            # Process each student enrollment
            for i in range(enrollment_count):
                student_id = request.POST.get(f'student_{i}')
                student_class_index = request.POST.get(f'student_class_{i}')
                
                if student_id and student_class_index:
                    try:
                        student = get_object_or_404(scope_profile_queryset(StudentProfile.objects.all(), request), id=student_id)
                        
                        # Find the class object by index
                        class_obj = None
                        for class_index, class_instance in classes_data:
                            if str(class_index) == str(student_class_index):
                                class_obj = class_instance
                                break
                        
                        if class_obj:
                            # Check if enrollment already exists
                            existing_enrollment = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
                                student=student,
                                class_enrolled=class_obj
                            ).first()
                            
                            if not existing_enrollment:
                                StudentEnrollment.objects.create(
                                    organization=get_current_organization(request),
                                    student=student,
                                    class_enrolled=class_obj,
                                    is_active=True
                                )
                                enrolled_students += 1
                            else:
                                existing_enrollment.is_active = True
                                existing_enrollment.save()
                                enrolled_students += 1
                        else:
                            messages.error(request, f'Could not find class for student enrollment')
                            
                    except Exception as e:
                        messages.error(request, f'Error enrolling student: {str(e)}')
            
            success_message = f'Course "{course.name}" created successfully!'
            if subjects_data:
                success_message += f' Added {len(subjects_data)} subjects.'
            if classes_data:
                success_message += f' Created {len(classes_data)} classes.'
            if enrolled_students:
                success_message += f' Enrolled {enrolled_students} students.'
                
            messages.success(request, success_message)
            return redirect('academic:course_detail', course_id=course.id)
        else:
            messages.error(request, 'Please correct the errors in the course information.')
    else:
        course_form = EnhancedCourseForm(organization=get_current_organization(request))
    
    # Get data for dropdowns
    academic_years = scope_academic_queryset(AcademicYear.objects.all(), request).order_by('-year')
    teachers = scope_profile_queryset(TeacherProfile.objects.select_related('user'), request)
    students = scope_profile_queryset(StudentProfile.objects.select_related('user'), request)
    
    # Convert to JSON for JavaScript
    import json
    academic_years_json = json.dumps([
        {'id': year.id, 'year': year.year} for year in academic_years
    ])
    teachers_json = json.dumps([
        {'id': teacher.id, 'name': teacher.user.get_full_name()} for teacher in teachers
    ])
    students_json = json.dumps([
        {'id': student.id, 'name': student.user.get_full_name(), 'student_id': student.student_id} 
        for student in students
    ])
    
    context = {
        'form': course_form,
        'academic_years': academic_years_json,
        'teachers': teachers_json,
        'students': students_json,
        'title': 'Create New Course'
    }
    return render(request, 'academic/course_form_enhanced.html', context)

@login_required
@user_passes_test(is_admin)
def edit_course(request, course_id):
    """Edit an existing course"""
    course = get_object_or_404(scope_academic_queryset(Course.objects.all(), request), id=course_id)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course, organization=get_current_organization(request))
        if form.is_valid():
            course = form.save()
            messages.success(request, f'Course "{course.name}" updated successfully!')
            return redirect('academic:course_detail', course_id=course.id)
    else:
        form = CourseForm(instance=course, organization=get_current_organization(request))
    
    context = {'form': form, 'course': course, 'title': 'Edit Course'}
    return render(request, 'academic/course_form.html', context)

@login_required
def teacher_assignments(request):
    """View for managing teacher subject assignments"""
    assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.select_related(
        'teacher__user', 'subject', 'class_assigned__course', 'academic_year'
    ), request)
    
    # Filter based on user type
    if request.user.user_type == 'teacher':
        assignments = assignments.filter(teacher=request.user.teacher_profile)
    
    context = {
        'assignments': assignments,
        'can_manage': request.user.user_type == 'admin'
    }
    
    return render(request, 'academic/teacher_assignments.html', context)
@login_required
def submit_assignment(request, assignment_id):
    """View for students to submit assignments"""
    if request.user.user_type != 'student':
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    assignment = get_object_or_404(scope_academic_queryset(Assignment.objects.all(), request), id=assignment_id, is_active=True)
    
    # Check if student is enrolled in the class
    try:
        enrollment = StudentEnrollment.objects.filter(
            student=request.user.student_profile,
            class_enrolled=assignment.class_assigned,
            is_active=True
        ).first()
        
        if not enrollment:
            messages.error(request, 'You are not enrolled in this class.')
            return redirect('academic:student_assignments')
    except (StudentProfile.DoesNotExist, AttributeError):
        messages.error(request, 'You are not enrolled in this class.')
        return redirect('academic:student_assignments')
    
    # Check if already submitted
    try:
        submission = AssignmentSubmission.objects.get(
            assignment=assignment,
            student=request.user.student_profile
        )
        is_resubmission = True
    except AssignmentSubmission.DoesNotExist:
        submission = None
        is_resubmission = False
    
    if request.method == 'POST':
        form = AssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user.student_profile
            submission.save()
            
            action = 'resubmitted' if is_resubmission else 'submitted'
            messages.success(request, f'Assignment {action} successfully!')
            return redirect('academic:student_assignments')
    else:
        form = AssignmentSubmissionForm(instance=submission)
    
    context = {
        'assignment': assignment,
        'form': form,
        'submission': submission,
        'is_resubmission': is_resubmission,
        'is_overdue': assignment.due_date < timezone.now()
    }
    
    return render(request, 'academic/submit_assignment.html', context)

@login_required
def teacher_class_students(request, class_id):
    """View for teachers to see students in their classes"""
    class_obj = get_object_or_404(scope_academic_queryset(Class.objects.all(), request), id=class_id)
    
    # Check if teacher has access to this class
    if request.user.user_type == 'teacher':
        teacher_assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
            teacher=request.user.teacher_profile,
            class_assigned=class_obj
        )
        if not teacher_assignments.exists():
            messages.error(request, 'You do not have access to this class.')
            return redirect('accounts:dashboard')
    elif request.user.user_type != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    # Get students enrolled in this class
    enrollments = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
        class_enrolled=class_obj,
        is_active=True
    ).select_related('student__user').order_by('student__user__first_name', 'student__user__last_name')
    
    # Get attendance summary for each student
    from attendance.models import AttendanceRecord
    student_data = []
    
    for enrollment in enrollments:
        student = enrollment.student
        
        # Calculate attendance statistics
        attendance_records = AttendanceRecord.objects.filter(student=student)
        total_sessions = attendance_records.count()
        present_sessions = attendance_records.filter(status__in=['present', 'late']).count()
        attendance_percentage = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        student_data.append({
            'enrollment': enrollment,
            'student': student,
            'total_sessions': total_sessions,
            'present_sessions': present_sessions,
            'attendance_percentage': round(attendance_percentage, 2)
        })
    
    context = {
        'class_obj': class_obj,
        'student_data': student_data,
        'can_manage': request.user.user_type in ['admin', 'teacher']
    }
    
    return render(request, 'academic/teacher_class_students.html', context)
@login_required
def student_enrollment_report(request):
    """Detailed report of student enrollments per course"""
    if request.user.user_type not in ['admin', 'teacher']:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    # Get course-wise enrollment data
    course_enrollments = []
    courses = scope_academic_queryset(Course.objects.all(), request)
    
    for course in courses:
        classes = scope_academic_queryset(Class.objects.all(), request).filter(course=course)
        student_count = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
            class_enrolled__course=course,
            is_active=True
        ).count()
        
        course_enrollments.append({
            'course': course,
            'class_count': classes.count(),
            'student_count': student_count
        })
    
    # Get class-wise enrollment data
    class_enrollments = []
    classes = scope_academic_queryset(Class.objects.select_related('course', 'class_teacher__user'), request)
    
    for class_obj in classes:
        student_count = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
            class_enrolled=class_obj,
            is_active=True
        ).count()
        
        class_enrollments.append({
            'class': class_obj,
            'student_count': student_count
        })
    
    # Calculate summary statistics
    total_students = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(is_active=True).count()
    active_enrollments = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(is_active=True).count()
    total_courses = scope_academic_queryset(Course.objects.all(), request).count()
    total_classes = scope_academic_queryset(Class.objects.all(), request).count()
    
    context = {
        'course_enrollments': course_enrollments,
        'class_enrollments': class_enrollments,
        'total_students': total_students,
        'active_enrollments': active_enrollments,
        'total_courses': total_courses,
        'total_classes': total_classes
    }
    
    return render(request, 'academic/student_enrollment_report.html', context)
@login_required
@user_passes_test(is_admin)
def create_class(request):
    """Create a new class"""
    course_id = request.GET.get('course')
    course = None
    if course_id:
        course = get_object_or_404(scope_academic_queryset(Course.objects.all(), request), id=course_id)
    
    if request.method == 'POST':
        form = ClassForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            class_obj = form.save(commit=False)
            assign_organization(class_obj, request)
            class_obj.save()
            messages.success(request, f'Class "{class_obj.name}" created successfully!')
            if course:
                return redirect('academic:course_detail', course_id=course.id)
            return redirect('academic:class_list')
    else:
        form = ClassForm(organization=get_current_organization(request))
        if course:
            form.fields['course'].initial = course
    
    context = {
        'form': form,
        'course': course,
        'title': 'Create New Class'
    }
    return render(request, 'academic/class_form.html', context)

@login_required
def class_detail(request, class_id):
    """Detailed view of a class"""
    class_obj = get_object_or_404(scope_academic_queryset(Class.objects.all(), request), id=class_id)
    
    # Get students enrolled in this class
    enrollments = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
        class_enrolled=class_obj,
        is_active=True
    ).select_related('student__user')
    
    # Get teacher assignments for this class
    teacher_assignments = scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request).filter(
        class_assigned=class_obj
    ).select_related('teacher__user', 'subject')
    
    context = {
        'class_obj': class_obj,
        'enrollments': enrollments,
        'teacher_assignments': teacher_assignments,
        'can_manage': request.user.user_type == 'admin'
    }
    
    return render(request, 'academic/class_detail.html', context)

@login_required
@user_passes_test(is_admin)
def create_subject(request):
    """Create a new subject"""
    course_id = request.GET.get('course')
    course = None
    if course_id:
        course = get_object_or_404(scope_academic_queryset(Course.objects.all(), request), id=course_id)
    
    if request.method == 'POST':
        form = SubjectForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            subject = form.save(commit=False)
            assign_organization(subject, request)
            subject.save()
            messages.success(request, f'Subject "{subject.name}" created successfully!')
            if course:
                return redirect('academic:course_detail', course_id=course.id)
            return redirect('academic:subject_list')
    else:
        form = SubjectForm(organization=get_current_organization(request))
        if course:
            form.fields['course'].initial = course
    
    context = {
        'form': form,
        'course': course,
        'title': 'Create New Subject'
    }
    return render(request, 'academic/subject_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_subject(request, subject_id):
    """Edit an existing subject"""
    subject = get_object_or_404(scope_academic_queryset(Subject.objects.all(), request), id=subject_id)
    
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject, organization=get_current_organization(request))
        if form.is_valid():
            subject = form.save()
            messages.success(request, f'Subject "{subject.name}" updated successfully!')
            return redirect('academic:course_detail', course_id=subject.course.id)
    else:
        form = SubjectForm(instance=subject, organization=get_current_organization(request))
    
    context = {
        'form': form,
        'subject': subject,
        'title': 'Edit Subject'
    }
    return render(request, 'academic/subject_form.html', context)

@login_required
@user_passes_test(is_admin)
def assign_teacher(request):
    """Assign a teacher to a subject and class"""
    course_id = request.GET.get('course')
    course = None
    if course_id:
        course = get_object_or_404(scope_academic_queryset(Course.objects.all(), request), id=course_id)
    
    if request.method == 'POST':
        form = TeacherSubjectAssignmentForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            assignment = form.save(commit=False)
            assign_organization(assignment, request)
            assignment.save()
            messages.success(request, f'Teacher "{assignment.teacher.user.get_full_name()}" assigned to "{assignment.subject.name}" successfully!')
            if course:
                return redirect('academic:course_detail', course_id=course.id)
            return redirect('academic:teacher_assignments')
    else:
        form = TeacherSubjectAssignmentForm(organization=get_current_organization(request))
        if course:
            # Filter subjects and classes for this course
            form.fields['subject'].queryset = scope_academic_queryset(Subject.objects.all(), request).filter(course=course)
            form.fields['class_assigned'].queryset = scope_academic_queryset(Class.objects.all(), request).filter(course=course)
    
    context = {
        'form': form,
        'course': course,
        'title': 'Assign Teacher'
    }
    return render(request, 'academic/teacher_assignment_form.html', context)

@login_required
@user_passes_test(is_admin)
def edit_teacher_assignment(request, assignment_id):
    """Edit a teacher assignment"""
    assignment = get_object_or_404(scope_academic_queryset(TeacherSubjectAssignment.objects.all(), request), id=assignment_id)
    
    if request.method == 'POST':
        form = TeacherSubjectAssignmentForm(request.POST, instance=assignment, organization=get_current_organization(request))
        if form.is_valid():
            assignment = form.save()
            messages.success(request, f'Teacher assignment updated successfully!')
            return redirect('academic:teacher_assignments')
    else:
        form = TeacherSubjectAssignmentForm(instance=assignment, organization=get_current_organization(request))
    
    context = {
        'form': form,
        'assignment': assignment,
        'title': 'Edit Teacher Assignment'
    }
    return render(request, 'academic/teacher_assignment_form.html', context)
@login_required
@user_passes_test(is_teacher_or_admin)
def assignment_detail(request, assignment_id):
    """View assignment details"""
    assignment = get_object_or_404(scope_academic_queryset(Assignment.objects.all(), request), id=assignment_id)
    
    # Check if user has permission to view this assignment
    if request.user.user_type == 'teacher' and assignment.teacher != request.user.teacher_profile:
        messages.error(request, 'You do not have permission to view this assignment.')
        return redirect('academic:assignment_list')
    
    # Get submissions for this assignment
    submissions = scope_academic_queryset(AssignmentSubmission.objects.all(), request).filter(
        assignment=assignment
    ).select_related('student__user').order_by('-submitted_at')
    
    # Calculate statistics
    total_students = assignment.class_assigned.studentenrollment_set.filter(is_active=True).count()
    submitted_count = submissions.count()
    pending_count = total_students - submitted_count
    submission_percentage = (submitted_count / total_students * 100) if total_students > 0 else 0
    
    context = {
        'assignment': assignment,
        'submissions': submissions,
        'total_students': total_students,
        'submitted_count': submitted_count,
        'pending_count': pending_count,
        'submission_percentage': round(submission_percentage, 1),
    }
    
    return render(request, 'academic/assignment_detail.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def edit_assignment(request, assignment_id):
    """Edit an existing assignment"""
    assignment = get_object_or_404(scope_academic_queryset(Assignment.objects.all(), request), id=assignment_id)
    
    # Check if user has permission to edit this assignment
    if request.user.user_type == 'teacher' and assignment.teacher != request.user.teacher_profile:
        messages.error(request, 'You do not have permission to edit this assignment.')
        return redirect('academic:assignment_list')
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, instance=assignment, teacher=getattr(request.user, 'teacher_profile', None), organization=get_current_organization(request))
        if form.is_valid():
            form.save()
            messages.success(request, f'Assignment "{assignment.title}" updated successfully!')
            return redirect('academic:assignment_detail', assignment_id=assignment.id)
    else:
        form = AssignmentForm(instance=assignment, teacher=getattr(request.user, 'teacher_profile', None), organization=get_current_organization(request))
    
    context = {'form': form, 'assignment': assignment}
    return render(request, 'academic/edit_assignment.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
@login_required
@user_passes_test(is_admin)
def manage_student_enrollment(request):
    """Admin view to manage student enrollments with department, course, and semester filtering"""
    enrollments = scope_academic_queryset(StudentEnrollment.objects.select_related(
        'student__user', 
        'class_enrolled__course__department',
        'class_enrolled__course',
        'class_enrolled__academic_year'
    ), request).order_by('-enrollment_date')
    
    # Apply filters
    department_filter = request.GET.get('department')
    course_filter = request.GET.get('course')
    semester_filter = request.GET.get('semester')
    year_filter = request.GET.get('year')
    status_filter = request.GET.get('status')
    search = request.GET.get('search', '')
    
    if department_filter:
        enrollments = enrollments.filter(class_enrolled__course__department_id=department_filter)
    
    if course_filter:
        enrollments = enrollments.filter(class_enrolled__course_id=course_filter)
    
    if semester_filter:
        enrollments = enrollments.filter(class_enrolled__semester=semester_filter)
    
    if year_filter:
        enrollments = enrollments.filter(class_enrolled__year=year_filter)
    
    if status_filter:
        if status_filter == 'active':
            enrollments = enrollments.filter(is_active=True)
        elif status_filter == 'inactive':
            enrollments = enrollments.filter(is_active=False)
    
    if search:
        enrollments = enrollments.filter(
            Q(student__user__first_name__icontains=search) |
            Q(student__user__last_name__icontains=search) |
            Q(student__user__username__icontains=search) |
            Q(student__student_id__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(enrollments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    departments = scope_academic_queryset(Department.objects.all(), request)
    courses = scope_academic_queryset(Course.objects.all(), request)
    if department_filter:
        courses = courses.filter(department_id=department_filter)
    
    # Get available semesters and years from existing enrollments
    available_semesters = enrollments.values_list('class_enrolled__semester', flat=True).distinct().order_by('class_enrolled__semester')
    available_years = enrollments.values_list('class_enrolled__year', flat=True).distinct().order_by('class_enrolled__year')
    
    # Calculate statistics
    total_enrollments = enrollments.count()
    active_enrollments = enrollments.filter(is_active=True).count()
    inactive_enrollments = total_enrollments - active_enrollments
    
    # Get enrollment statistics by department
    dept_stats = []
    for dept in departments:
        dept_enrollment_count = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
            class_enrolled__course__department=dept,
            is_active=True
        ).count()
        dept_stats.append({
            'department': dept,
            'enrollment_count': dept_enrollment_count
        })
    
    # Get semester-wise enrollment statistics
    semester_stats = []
    for semester in range(1, 9):  # Assuming max 8 semesters
        semester_enrollment_count = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
            class_enrolled__semester=semester,
            is_active=True
        ).count()
        if semester_enrollment_count > 0:
            semester_stats.append({
                'semester': semester,
                'enrollment_count': semester_enrollment_count
            })
    
    # Get year-wise enrollment statistics
    year_stats = []
    for year in range(1, 5):  # Assuming max 4 years
        year_enrollment_count = scope_academic_queryset(StudentEnrollment.objects.all(), request).filter(
            class_enrolled__year=year,
            is_active=True
        ).count()
        if year_enrollment_count > 0:
            year_stats.append({
                'year': year,
                'enrollment_count': year_enrollment_count
            })
    
    context = {
        'page_obj': page_obj,
        'departments': departments,
        'courses': courses,
        'available_semesters': available_semesters,
        'available_years': available_years,
        'department_filter': department_filter,
        'course_filter': course_filter,
        'semester_filter': semester_filter,
        'year_filter': year_filter,
        'status_filter': status_filter,
        'search': search,
        'total_enrollments': total_enrollments,
        'active_enrollments': active_enrollments,
        'inactive_enrollments': inactive_enrollments,
        'dept_stats': dept_stats,
        'semester_stats': semester_stats,
        'year_stats': year_stats,
    }
    
    return render(request, 'academic/manage_student_enrollment.html', context)

@login_required
@user_passes_test(is_admin)
def create_student_enrollment(request):
    """Create a new student enrollment with department and course selection"""
    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            enrollment = form.save(commit=False)
            assign_organization(enrollment, request)
            enrollment.save()
            messages.success(request, f'Student "{enrollment.student.user.get_full_name()}" enrolled in "{enrollment.class_enrolled}" successfully!')
            return redirect('academic:manage_student_enrollment')
    else:
        form = StudentEnrollmentForm(organization=get_current_organization(request))
    
    # Get data for AJAX filtering
    departments = scope_academic_queryset(Department.objects.all(), request)
    courses = scope_academic_queryset(Course.objects.all(), request)
    classes = scope_academic_queryset(Class.objects.all(), request)
    
    context = {
        'form': form,
        'departments': departments,
        'courses': courses,
        'classes': classes,
        'title': 'Enroll Student'
    }
    
    return render(request, 'academic/create_student_enrollment.html', context)

@login_required
@user_passes_test(is_admin)
def edit_student_enrollment(request, enrollment_id):
    """Edit an existing student enrollment"""
    enrollment = get_object_or_404(scope_academic_queryset(StudentEnrollment.objects.all(), request), id=enrollment_id)
    
    if request.method == 'POST':
        form = StudentEnrollmentForm(request.POST, instance=enrollment, organization=get_current_organization(request))
        if form.is_valid():
            enrollment = form.save()
            messages.success(request, f'Enrollment for "{enrollment.student.user.get_full_name()}" updated successfully!')
            return redirect('academic:manage_student_enrollment')
    else:
        form = StudentEnrollmentForm(instance=enrollment, organization=get_current_organization(request))
    
    # Get data for AJAX filtering
    departments = scope_academic_queryset(Department.objects.all(), request)
    courses = scope_academic_queryset(Course.objects.all(), request)
    classes = scope_academic_queryset(Class.objects.all(), request)
    
    context = {
        'form': form,
        'enrollment': enrollment,
        'departments': departments,
        'courses': courses,
        'classes': classes,
        'title': 'Edit Student Enrollment'
    }
    
    return render(request, 'academic/edit_student_enrollment.html', context)

@login_required
@user_passes_test(is_admin)
def semester_wise_enrollment_report(request):
    """Generate semester-wise enrollment report"""
    # Get filter parameters
    department_filter = request.GET.get('department')
    course_filter = request.GET.get('course')
    academic_year_filter = request.GET.get('academic_year')
    
    # Base queryset
    enrollments = scope_academic_queryset(StudentEnrollment.objects.select_related(
        'student__user', 
        'class_enrolled__course__department',
        'class_enrolled__course',
        'class_enrolled__academic_year'
    ), request).filter(is_active=True)
    
    # Apply filters
    if department_filter:
        enrollments = enrollments.filter(class_enrolled__course__department_id=department_filter)
    
    if course_filter:
        enrollments = enrollments.filter(class_enrolled__course_id=course_filter)
    
    if academic_year_filter:
        enrollments = enrollments.filter(class_enrolled__academic_year_id=academic_year_filter)
    
    # Group enrollments by semester and year
    semester_data = {}
    for enrollment in enrollments:
        year = enrollment.class_enrolled.year
        semester = enrollment.class_enrolled.semester
        course_name = enrollment.class_enrolled.course.name
        department_name = enrollment.class_enrolled.course.department.name
        
        key = f"Year {year} - Semester {semester}"
        if key not in semester_data:
            semester_data[key] = {
                'year': year,
                'semester': semester,
                'courses': {},
                'total_students': 0,
                'departments': set()
            }
        
        if course_name not in semester_data[key]['courses']:
            semester_data[key]['courses'][course_name] = {
                'students': [],
                'department': department_name,
                'count': 0
            }
        
        semester_data[key]['courses'][course_name]['students'].append(enrollment)
        semester_data[key]['courses'][course_name]['count'] += 1
        semester_data[key]['total_students'] += 1
        semester_data[key]['departments'].add(department_name)
    
    # Convert departments set to list for template
    for key in semester_data:
        semester_data[key]['departments'] = list(semester_data[key]['departments'])
    
    # Sort semester data by year and semester
    sorted_semester_data = dict(sorted(semester_data.items(), key=lambda x: (x[1]['year'], x[1]['semester'])))
    
    # Get filter options
    departments = scope_academic_queryset(Department.objects.all(), request)
    courses = scope_academic_queryset(Course.objects.all(), request)
    academic_years = scope_academic_queryset(AcademicYear.objects.all(), request).order_by('-year')
    
    if department_filter:
        courses = courses.filter(department_id=department_filter)
    
    context = {
        'semester_data': sorted_semester_data,
        'departments': departments,
        'courses': courses,
        'academic_years': academic_years,
        'department_filter': department_filter,
        'course_filter': course_filter,
        'academic_year_filter': academic_year_filter,
        'total_semesters': len(semester_data),
        'total_enrollments': sum(data['total_students'] for data in semester_data.values())
    }
    
    return render(request, 'academic/semester_wise_enrollment_report.html', context)

@login_required
@user_passes_test(is_admin)
def toggle_enrollment_status(request, enrollment_id):
    """Toggle enrollment status (active/inactive)"""
    if request.method == 'POST':
        enrollment = get_object_or_404(scope_academic_queryset(StudentEnrollment.objects.all(), request), id=enrollment_id)
        new_status = request.POST.get('is_active') == 'true'
        
        enrollment.is_active = new_status
        enrollment.save()
        
        status_text = 'activated' if new_status else 'deactivated'
        messages.success(request, f'Enrollment for "{enrollment.student.user.get_full_name()}" has been {status_text}.')
    
    return redirect('academic:manage_student_enrollment')


# Semester-specific enrollment views
@login_required
@user_passes_test(is_admin)
def manage_semester_enrollments(request):
    """Manage semester-specific enrollments"""
    from .models import SemesterEnrollment
    from .forms import SemesterEnrollmentFilterForm
    
    # Get filter form
    filter_form = SemesterEnrollmentFilterForm(request.GET)
    
    # Base queryset
    enrollments = scope_academic_queryset(SemesterEnrollment.objects.select_related(
        'student__user', 'course__department', 'academic_year', 'approved_by__user'
    ), request).order_by('-created_at')
    
    # Apply filters
    if filter_form.is_valid():
        if filter_form.cleaned_data['department']:
            enrollments = enrollments.filter(course__department=filter_form.cleaned_data['department'])
        
        if filter_form.cleaned_data['course']:
            enrollments = enrollments.filter(course=filter_form.cleaned_data['course'])
        
        if filter_form.cleaned_data['year']:
            enrollments = enrollments.filter(year=filter_form.cleaned_data['year'])
        
        if filter_form.cleaned_data['semester']:
            enrollments = enrollments.filter(semester=filter_form.cleaned_data['semester'])
        
        if filter_form.cleaned_data['academic_year']:
            enrollments = enrollments.filter(academic_year=filter_form.cleaned_data['academic_year'])
        
        if filter_form.cleaned_data['status']:
            enrollments = enrollments.filter(enrollment_status=filter_form.cleaned_data['status'])
        
        if filter_form.cleaned_data['search']:
            search_term = filter_form.cleaned_data['search']
            enrollments = enrollments.filter(
                Q(student__user__first_name__icontains=search_term) |
                Q(student__user__last_name__icontains=search_term) |
                Q(student__user__username__icontains=search_term) |
                Q(student__student_id__icontains=search_term)
            )
    
    # Pagination
    paginator = Paginator(enrollments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    total_enrollments = enrollments.count()
    status_stats = {}
    for status_code, status_name in SemesterEnrollment.ENROLLMENT_STATUS_CHOICES:
        count = enrollments.filter(enrollment_status=status_code).count()
        if count > 0:
            status_stats[status_name] = count
    
    # Semester-wise statistics
    semester_stats = {}
    for semester in range(1, 9):
        count = enrollments.filter(semester=semester).count()
        if count > 0:
            semester_stats[f'Semester {semester}'] = count
    
    # Year-wise statistics
    year_stats = {}
    for year in range(1, 7):
        count = enrollments.filter(year=year).count()
        if count > 0:
            year_stats[f'Year {year}'] = count
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_enrollments': total_enrollments,
        'status_stats': status_stats,
        'semester_stats': semester_stats,
        'year_stats': year_stats,
    }
    
    return render(request, 'academic/manage_semester_enrollments.html', context)

@login_required
@user_passes_test(is_admin)
def create_semester_enrollment(request):
    """Create a new semester enrollment"""
    from .models import SemesterEnrollment
    from .forms import SemesterEnrollmentForm
    
    if request.method == 'POST':
        form = SemesterEnrollmentForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            enrollment = form.save(commit=False)
            assign_organization(enrollment, request)
            enrollment.save()
            messages.success(request, f'Semester enrollment created for "{enrollment.student.user.get_full_name()}" in {enrollment.semester_display}!')
            return redirect('academic:manage_semester_enrollments')
    else:
        form = SemesterEnrollmentForm(organization=get_current_organization(request))
    
    context = {
        'form': form,
        'title': 'Create Semester Enrollment'
    }
    
    return render(request, 'academic/create_semester_enrollment.html', context)

@login_required
@user_passes_test(is_admin)
def edit_semester_enrollment(request, enrollment_id):
    """Edit a semester enrollment"""
    from .models import SemesterEnrollment
    from .forms import SemesterEnrollmentForm
    
    enrollment = get_object_or_404(scope_academic_queryset(SemesterEnrollment.objects.all(), request), id=enrollment_id)
    
    if request.method == 'POST':
        form = SemesterEnrollmentForm(request.POST, instance=enrollment, organization=get_current_organization(request))
        if form.is_valid():
            enrollment = form.save()
            messages.success(request, f'Semester enrollment updated for "{enrollment.student.user.get_full_name()}"!')
            return redirect('academic:manage_semester_enrollments')
    else:
        form = SemesterEnrollmentForm(instance=enrollment, organization=get_current_organization(request))
    
    context = {
        'form': form,
        'enrollment': enrollment,
        'title': 'Edit Semester Enrollment'
    }
    
    return render(request, 'academic/edit_semester_enrollment.html', context)

@login_required
@user_passes_test(is_admin)
def approve_semester_enrollment(request, enrollment_id):
    """Approve a semester enrollment"""
    from .models import SemesterEnrollment
    
    if request.method == 'POST':
        enrollment = get_object_or_404(scope_academic_queryset(SemesterEnrollment.objects.all(), request), id=enrollment_id)
        enrollment.approve_enrollment(request.user)
        messages.success(request, f'Enrollment approved for "{enrollment.student.user.get_full_name()}"!')
    
    return redirect('academic:manage_semester_enrollments')

@login_required
@user_passes_test(is_admin)
def reject_semester_enrollment(request, enrollment_id):
    """Reject a semester enrollment"""
    from .models import SemesterEnrollment
    
    if request.method == 'POST':
        enrollment = get_object_or_404(scope_academic_queryset(SemesterEnrollment.objects.all(), request), id=enrollment_id)
        reason = request.POST.get('reason', '')
        enrollment.reject_enrollment(reason)
        messages.success(request, f'Enrollment rejected for "{enrollment.student.user.get_full_name()}"!')
    
    return redirect('academic:manage_semester_enrollments')

@login_required
@user_passes_test(is_admin)
def bulk_semester_enrollment(request):
    """Bulk semester enrollment"""
    from .models import SemesterEnrollment
    from .forms import BulkSemesterEnrollmentForm
    
    if request.method == 'POST':
        form = BulkSemesterEnrollmentForm(request.POST, organization=get_current_organization(request))
        if form.is_valid():
            course = form.cleaned_data['course']
            year = form.cleaned_data['year']
            semester = form.cleaned_data['semester']
            academic_year = form.cleaned_data['academic_year']
            students = form.cleaned_data['students']
            section = form.cleaned_data['section']
            enrollment_fee_amount = form.cleaned_data.get('enrollment_fee_amount')
            enrollment_deadline = form.cleaned_data.get('enrollment_deadline')
            
            created_count = 0
            for student in students:
                # Check if enrollment already exists
                existing = scope_academic_queryset(SemesterEnrollment.objects.all(), request).filter(
                    student=student,
                    course=course,
                    year=year,
                    semester=semester,
                    academic_year=academic_year
                ).first()
                
                if not existing:
                    SemesterEnrollment.objects.create(
                        organization=get_current_organization(request),
                        student=student,
                        course=course,
                        year=year,
                        semester=semester,
                        academic_year=academic_year,
                        section=section,
                        enrollment_fee_amount=enrollment_fee_amount,
                        enrollment_deadline=enrollment_deadline,
                        enrollment_status='approved'  # Auto-approve bulk enrollments
                    )
                    created_count += 1
            
            messages.success(request, f'Successfully created {created_count} semester enrollments!')
            return redirect('academic:manage_semester_enrollments')
    else:
        form = BulkSemesterEnrollmentForm(organization=get_current_organization(request))
    
    context = {
        'form': form,
        'title': 'Bulk Semester Enrollment'
    }
    
    return render(request, 'academic/bulk_semester_enrollment.html', context)

@login_required
def semester_enrollment_report(request):
    """Generate semester enrollment report"""
    from .models import SemesterEnrollment
    from .forms import SemesterEnrollmentFilterForm
    
    # Get filter form
    filter_form = SemesterEnrollmentFilterForm(request.GET)
    
    # Base queryset
    enrollments = scope_academic_queryset(SemesterEnrollment.objects.select_related(
        'student__user', 'course__department', 'academic_year'
    ), request).filter(enrollment_status__in=['approved', 'completed'])
    
    # Apply filters
    if filter_form.is_valid():
        if filter_form.cleaned_data['department']:
            enrollments = enrollments.filter(course__department=filter_form.cleaned_data['department'])
        
        if filter_form.cleaned_data['course']:
            enrollments = enrollments.filter(course=filter_form.cleaned_data['course'])
        
        if filter_form.cleaned_data['year']:
            enrollments = enrollments.filter(year=filter_form.cleaned_data['year'])
        
        if filter_form.cleaned_data['semester']:
            enrollments = enrollments.filter(semester=filter_form.cleaned_data['semester'])
        
        if filter_form.cleaned_data['academic_year']:
            enrollments = enrollments.filter(academic_year=filter_form.cleaned_data['academic_year'])
    
    # Group by semester
    semester_data = {}
    for enrollment in enrollments:
        key = f"Year {enrollment.year} - Semester {enrollment.semester}"
        if key not in semester_data:
            semester_data[key] = {
                'year': enrollment.year,
                'semester': enrollment.semester,
                'courses': {},
                'total_students': 0,
                'departments': set()
            }
        
        course_name = enrollment.course.name
        if course_name not in semester_data[key]['courses']:
            semester_data[key]['courses'][course_name] = {
                'students': [],
                'department': enrollment.course.department.name,
                'count': 0
            }
        
        semester_data[key]['courses'][course_name]['students'].append(enrollment)
        semester_data[key]['courses'][course_name]['count'] += 1
        semester_data[key]['total_students'] += 1
        semester_data[key]['departments'].add(enrollment.course.department.name)
    
    # Convert departments set to list
    for key in semester_data:
        semester_data[key]['departments'] = list(semester_data[key]['departments'])
    
    # Sort semester data
    sorted_semester_data = dict(sorted(semester_data.items(), key=lambda x: (x[1]['year'], x[1]['semester'])))
    
    context = {
        'semester_data': sorted_semester_data,
        'filter_form': filter_form,
        'total_semesters': len(semester_data),
        'total_enrollments': sum(data['total_students'] for data in semester_data.values())
    }
    
    return render(request, 'academic/semester_enrollment_report.html', context)

@login_required
@user_passes_test(is_teacher_or_admin)
def assignment_submissions(request, assignment_id):
    """View all submissions for an assignment"""
    assignment = get_object_or_404(scope_academic_queryset(Assignment.objects.all(), request), id=assignment_id)
    
    # Check if user has permission to view submissions
    if request.user.user_type == 'teacher' and assignment.teacher != request.user.teacher_profile:
        messages.error(request, 'You do not have permission to view these submissions.')
        return redirect('academic:assignment_list')
    
    # Get all submissions
    submissions = scope_academic_queryset(AssignmentSubmission.objects.all(), request).filter(
        assignment=assignment
    ).select_related('student__user').order_by('-submitted_at')
    
    # Get students who haven't submitted
    enrolled_students = assignment.class_assigned.studentenrollment_set.filter(
        is_active=True
    ).select_related('student__user')
    
    submitted_student_ids = submissions.values_list('student_id', flat=True)
    pending_students = enrolled_students.exclude(student_id__in=submitted_student_ids)
    
    context = {
        'assignment': assignment,
        'submissions': submissions,
        'pending_students': pending_students,
        'total_students': enrolled_students.count(),
        'submitted_count': submissions.count(),
    }
    
    return render(request, 'academic/assignment_submissions.html', context)


