from django import forms
from django.core.exceptions import ValidationError
from .models import Examination, ExamResult, ExamType
from academic.models import Subject, Class, TeacherSubjectAssignment

class ExaminationForm(forms.ModelForm):
    class Meta:
        model = Examination
        fields = ['name', 'exam_type', 'subject', 'class_for', 'exam_date', 
                 'start_time', 'end_time', 'total_marks', 'passing_marks', 'instructions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter exam name'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'passing_marks': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter exam instructions (optional)'}),
            'exam_type': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'class_for': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            # Filter subjects based on teacher's assignments
            assigned_subjects = TeacherSubjectAssignment.objects.filter(
                teacher=teacher
            ).values_list('subject', flat=True)
            self.fields['subject'].queryset = Subject.objects.filter(id__in=assigned_subjects)
            
            # Filter classes based on teacher's assignments
            assigned_classes = TeacherSubjectAssignment.objects.filter(
                teacher=teacher
            ).values_list('class_assigned', flat=True)
            self.fields['class_for'].queryset = Class.objects.filter(id__in=assigned_classes)
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        total_marks = cleaned_data.get('total_marks')
        passing_marks = cleaned_data.get('passing_marks')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError('End time must be after start time.')
        
        if total_marks and passing_marks and passing_marks > total_marks:
            raise ValidationError('Passing marks cannot be greater than total marks.')
        
        return cleaned_data

class ExamResultForm(forms.ModelForm):
    class Meta:
        model = ExamResult
        fields = ['marks_obtained', 'remarks']
        widgets = {
            'marks_obtained': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Enter remarks (optional)'}),
        }
    
    def __init__(self, *args, **kwargs):
        examination = kwargs.pop('examination', None)
        super().__init__(*args, **kwargs)
        
        if examination:
            self.fields['marks_obtained'].widget.attrs['max'] = str(examination.total_marks)
            self.fields['marks_obtained'].help_text = f'Maximum marks: {examination.total_marks}'
    
    def clean_marks_obtained(self):
        marks = self.cleaned_data.get('marks_obtained')
        if marks is not None and marks < 0:
            raise ValidationError('Marks cannot be negative.')
        return marks

