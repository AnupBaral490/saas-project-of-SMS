from django import forms
from .models import (
    AcademicYear, Department, Course, Subject, Class, 
    StudentEnrollment, SemesterEnrollment, TeacherSubjectAssignment, Assignment, AssignmentSubmission
)
from accounts.models import StudentProfile, TeacherProfile


def apply_organization_queryset(field, queryset, organization):
    if organization is None:
        field.queryset = queryset
    else:
        field.queryset = queryset

class AcademicYearForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = AcademicYear
        fields = ['year', 'start_date', 'end_date', 'is_current']
        widgets = {
            'year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '2023-2024'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DepartmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields['head_of_department'].queryset = TeacherProfile.objects.filter(user__organization=organization)

    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'head_of_department']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'head_of_department': forms.Select(attrs={'class': 'form-select'}),
        }

class CourseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields['department'].queryset = Department.objects.filter(organization=organization)

    class Meta:
        model = Course
        fields = ['name', 'code', 'department', 'duration_years', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class EnhancedCourseForm(forms.ModelForm):
    """Enhanced course form with dynamic subject, class, and student enrollment"""
    
    class Meta:
        model = Course
        fields = ['name', 'code', 'department', 'duration_years', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        # Add required attribute to essential fields
        self.fields['name'].required = True
        self.fields['code'].required = True
        self.fields['department'].required = True
        if organization is not None:
            self.fields['department'].queryset = Department.objects.filter(organization=organization)

class SubjectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields['course'].queryset = Course.objects.filter(organization=organization)

    class Meta:
        model = Subject
        fields = ['name', 'code', 'course', 'year', 'semester', 'credits', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'semester': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'credits': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ClassForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields['course'].queryset = Course.objects.filter(organization=organization)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(organization=organization)
            self.fields['class_teacher'].queryset = TeacherProfile.objects.filter(user__organization=organization)

    class Meta:
        model = Class
        fields = ['name', 'course', 'year', 'semester', 'section', 'academic_year', 'class_teacher']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'semester': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A, B, C, etc.'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'class_teacher': forms.Select(attrs={'class': 'form-select'}),
        }

class StudentEnrollmentForm(forms.ModelForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="Select Department First",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_department'}),
        help_text="Select department to filter courses"
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        required=False,
        empty_label="Select Course",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_course'}),
        help_text="Select course to filter classes"
    )
    
    class Meta:
        model = StudentEnrollment
        fields = ['student', 'class_enrolled', 'is_active']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'class_enrolled': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        if organization is not None:
            self.fields['department'].queryset = Department.objects.filter(organization=organization)
            self.fields['student'].queryset = StudentProfile.objects.filter(user__organization=organization)
            self.fields['class_enrolled'].queryset = Class.objects.filter(organization=organization)
        
        # If we have POST data, populate the department and course fields
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['course'].queryset = Course.objects.filter(department_id=department_id)
                if organization is not None:
                    self.fields['course'].queryset = self.fields['course'].queryset.filter(organization=organization)
            except (ValueError, TypeError):
                pass
        
        if 'course' in self.data:
            try:
                course_id = int(self.data.get('course'))
                self.fields['class_enrolled'].queryset = Class.objects.filter(course_id=course_id)
                if organization is not None:
                    self.fields['class_enrolled'].queryset = self.fields['class_enrolled'].queryset.filter(organization=organization)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.class_enrolled:
            # If editing existing enrollment, populate the fields
            class_enrolled = self.instance.class_enrolled
            course = class_enrolled.course
            department = course.department
            
            self.fields['department'].initial = department
            self.fields['course'].queryset = Course.objects.filter(department=department)
            self.fields['course'].initial = course
            self.fields['class_enrolled'].queryset = Class.objects.filter(course=course)

class SemesterEnrollmentForm(forms.ModelForm):
    """Form for semester-specific enrollment"""
    
    class Meta:
        model = SemesterEnrollment
        fields = [
            'student', 'course', 'year', 'semester', 'academic_year', 'section',
            'enrollment_fee_amount', 'enrollment_deadline', 'enrollment_status'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 6}),
            'semester': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A, B, C, etc.'}),
            'enrollment_fee_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'enrollment_deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'enrollment_status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        # Set default values
        if not self.instance.pk:
            self.fields['enrollment_status'].initial = 'pending'
            self.fields['section'].initial = 'A'
        if organization is not None:
            self.fields['student'].queryset = StudentProfile.objects.filter(user__organization=organization)
            self.fields['course'].queryset = Course.objects.filter(organization=organization)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(organization=organization)

class SemesterEnrollmentFilterForm(forms.Form):
    """Filter form for semester enrollments"""
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="All Departments",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        empty_label="All Courses",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    year = forms.ChoiceField(
        choices=[('', 'All Years')] + [(i, f'Year {i}') for i in range(1, 7)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    semester = forms.ChoiceField(
        choices=[('', 'All Semesters')] + [(i, f'Semester {i}') for i in range(1, 9)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        empty_label="All Academic Years",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + SemesterEnrollment.ENROLLMENT_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by student name or ID...'
        })
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields['department'].queryset = Department.objects.filter(organization=organization)
            self.fields['course'].queryset = Course.objects.filter(organization=organization)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(organization=organization)

class BulkSemesterEnrollmentForm(forms.Form):
    """Form for bulk semester enrollment"""
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select the course for bulk enrollment"
    )
    
    year = forms.ChoiceField(
        choices=[(i, f'Year {i}') for i in range(1, 7)],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select the academic year"
    )
    
    semester = forms.ChoiceField(
        choices=[(i, f'Semester {i}') for i in range(1, 9)],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select the semester"
    )
    
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select the academic year"
    )
    
    students = forms.ModelMultipleChoiceField(
        queryset=StudentProfile.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text="Select students to enroll"
    )
    
    section = forms.CharField(
        max_length=10,
        initial='A',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Section for all selected students"
    )
    
    enrollment_fee_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        help_text="Enrollment fee amount (optional)"
    )
    
    enrollment_deadline = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        help_text="Enrollment deadline (optional)"
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields['course'].queryset = Course.objects.filter(organization=organization)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(organization=organization)
            self.fields['students'].queryset = StudentProfile.objects.filter(user__organization=organization)

class TeacherSubjectAssignmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        if organization is not None:
            self.fields['teacher'].queryset = TeacherProfile.objects.filter(user__organization=organization)
            self.fields['subject'].queryset = Subject.objects.filter(organization=organization)
            self.fields['class_assigned'].queryset = Class.objects.filter(organization=organization)
            self.fields['academic_year'].queryset = AcademicYear.objects.filter(organization=organization)

    class Meta:
        model = TeacherSubjectAssignment
        fields = ['teacher', 'subject', 'class_assigned', 'academic_year']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'class_assigned': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.Select(attrs={'class': 'form-select'}),
        }

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'assignment_type', 'subject', 'class_assigned', 
                 'due_date', 'max_marks', 'instructions', 'attachment', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'assignment_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'class_assigned': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'max_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        if organization is not None and not teacher:
            self.fields['subject'].queryset = Subject.objects.filter(organization=organization)
            self.fields['class_assigned'].queryset = Class.objects.filter(organization=organization)
        
        if teacher:
            # Filter subjects and classes based on teacher's assignments
            teacher_assignments = TeacherSubjectAssignment.objects.filter(teacher=teacher)
            subject_ids = teacher_assignments.values_list('subject_id', flat=True)
            class_ids = teacher_assignments.values_list('class_assigned_id', flat=True)

            if subject_ids.exists() or class_ids.exists():
                self.fields['subject'].queryset = Subject.objects.filter(id__in=subject_ids)
                self.fields['class_assigned'].queryset = Class.objects.filter(id__in=class_ids)
            elif organization is not None:
                # Fallback to organization data when teacher has no assignments yet
                self.fields['subject'].queryset = Subject.objects.filter(organization=organization)
                self.fields['class_assigned'].queryset = Class.objects.filter(organization=organization)

class AssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_text', 'attachment']
        widgets = {
            'submission_text': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6,
                'placeholder': 'Enter your submission text here...'
            }),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ClassFilterForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        empty_label="All Courses",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    year = forms.ChoiceField(
        choices=[('', 'All Years')] + [(i, f'Year {i}') for i in range(1, 7)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    semester = forms.ChoiceField(
        choices=[('', 'All Semesters')] + [(i, f'Semester {i}') for i in range(1, 9)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        empty_label="All Academic Years",
        widget=forms.Select(attrs={'class': 'form-select'})
    )