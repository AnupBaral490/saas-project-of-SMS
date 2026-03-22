from django import forms
from django.forms import formset_factory
from .models import AttendanceSession, AttendanceRecord
from academic.models import TeacherSubjectAssignment, StudentEnrollment, Subject, Class
from accounts.models import StudentProfile

class AttendanceSessionForm(forms.ModelForm):
    class Meta:
        model = AttendanceSession
        fields = ['teacher_assignment', 'date', 'start_time', 'end_time', 'topic_covered', 'notes']
        widgets = {
            'teacher_assignment': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'topic_covered': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Topic covered in this session'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes (optional)'}),
        }
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            # Filter assignments for the current teacher
            self.fields['teacher_assignment'].queryset = TeacherSubjectAssignment.objects.filter(
                teacher=teacher
            )
        elif organization is not None:
            self.fields['teacher_assignment'].queryset = TeacherSubjectAssignment.objects.filter(organization=organization)

class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['student', 'status', 'remarks']
        widgets = {
            'student': forms.HiddenInput(),
            'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Optional remarks'}),
        }

class QuickAttendanceForm(forms.Form):
    """Form for quickly marking attendance for a class"""
    teacher_assignment = forms.ModelChoiceField(
        queryset=TeacherSubjectAssignment.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Subject & Class"
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date"
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="Start Time"
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label="End Time"
    )
    topic_covered = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Topic covered'}),
        label="Topic Covered"
    )
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            self.fields['teacher_assignment'].queryset = TeacherSubjectAssignment.objects.filter(
                teacher=teacher
            )
        elif organization is not None:
            self.fields['teacher_assignment'].queryset = TeacherSubjectAssignment.objects.filter(organization=organization)

class AttendanceFilterForm(forms.Form):
    subject = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Subjects",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class_filter = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Classes",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + list(AttendanceRecord.ATTENDANCE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        if user:
            if user.user_type == 'teacher':
                # Filter based on teacher's assignments
                teacher_assignments = TeacherSubjectAssignment.objects.filter(teacher=user.teacher_profile)
                self.fields['subject'].queryset = Subject.objects.filter(
                    id__in=teacher_assignments.values_list('subject_id', flat=True)
                )
                self.fields['class_filter'].queryset = Class.objects.filter(
                    id__in=teacher_assignments.values_list('class_assigned_id', flat=True)
                )
            elif user.user_type == 'student':
                # Filter based on student's enrollment
                enrollment = StudentEnrollment.objects.filter(student=user.student_profile, is_active=True).first()
                if enrollment:
                    self.fields['subject'].queryset = Subject.objects.filter(
                        course=enrollment.class_enrolled.course,
                        year=enrollment.class_enrolled.year,
                        semester=enrollment.class_enrolled.semester
                    )
                    self.fields['class_filter'].queryset = Class.objects.filter(id=enrollment.class_enrolled.id)
                else:
                    # Student not enrolled - set empty querysets
                    self.fields['subject'].queryset = Subject.objects.none()
                    self.fields['class_filter'].queryset = Class.objects.none()
            elif user.user_type == 'parent':
                # Filter based on parent's children
                try:
                    parent_profile = user.parent_profile
                    children = parent_profile.children.all()
                    
                    if children.exists():
                        # Get all subjects and classes for all children
                        child_enrollments = StudentEnrollment.objects.filter(
                            student__in=children,
                            is_active=True
                        )
                        
                        if child_enrollments.exists():
                            # Get unique subjects from all children's enrollments
                            subject_ids = set()
                            class_ids = set()
                            
                            for enrollment in child_enrollments:
                                subjects = Subject.objects.filter(
                                    course=enrollment.class_enrolled.course,
                                    year=enrollment.class_enrolled.year,
                                    semester=enrollment.class_enrolled.semester
                                )
                                subject_ids.update(subjects.values_list('id', flat=True))
                                class_ids.add(enrollment.class_enrolled.id)
                            
                            self.fields['subject'].queryset = Subject.objects.filter(id__in=subject_ids)
                            self.fields['class_filter'].queryset = Class.objects.filter(id__in=class_ids)
                        else:
                            # Children not enrolled - set empty querysets
                            self.fields['subject'].queryset = Subject.objects.none()
                            self.fields['class_filter'].queryset = Class.objects.none()
                    else:
                        # No children - set empty querysets
                        self.fields['subject'].queryset = Subject.objects.none()
                        self.fields['class_filter'].queryset = Class.objects.none()
                except Exception as e:
                    print(f"Error in AttendanceFilterForm for parent: {e}")
                    self.fields['subject'].queryset = Subject.objects.none()
                    self.fields['class_filter'].queryset = Class.objects.none()
            elif user.user_type == 'admin':
                # Admin can see all subjects and classes
                self.fields['subject'].queryset = Subject.objects.filter(organization=organization) if organization else Subject.objects.all()
                self.fields['class_filter'].queryset = Class.objects.filter(organization=organization) if organization else Class.objects.all()
            else:
                # Unknown user type - set empty querysets
                self.fields['subject'].queryset = Subject.objects.none()
                self.fields['class_filter'].queryset = Class.objects.none()
        else:
            # If no user provided, set empty querysets
            self.fields['subject'].queryset = Subject.objects.none()
            self.fields['class_filter'].queryset = Class.objects.none()

# Create a formset for bulk attendance marking
AttendanceRecordFormSet = formset_factory(
    AttendanceRecordForm,
    extra=0,
    can_delete=False
)