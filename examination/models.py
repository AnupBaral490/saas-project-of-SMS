from django.db import models
from accounts.models import StudentProfile, TeacherProfile
from academic.models import Subject, Class

class ExamType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    
    def __str__(self):
        return self.name

class Examination(models.Model):
    name = models.CharField(max_length=100)
    exam_type = models.ForeignKey(ExamType, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_for = models.ForeignKey(Class, on_delete=models.CASCADE)
    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_marks = models.PositiveIntegerField()
    passing_marks = models.PositiveIntegerField()
    instructions = models.TextField(blank=True)
    created_by = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.subject.name} - {self.class_for}"

class ExamResult(models.Model):
    GRADE_CHOICES = (
        ('A+', 'A+ (90-100)'),
        ('A', 'A (80-89)'),
        ('B+', 'B+ (70-79)'),
        ('B', 'B (60-69)'),
        ('C+', 'C+ (50-59)'),
        ('C', 'C (40-49)'),
        ('D', 'D (30-39)'),
        ('F', 'F (0-29)'),
    )
    
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2)
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES)
    remarks = models.TextField(blank=True)
    is_passed = models.BooleanField(default=False)
    entered_by = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['examination', 'student']
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.examination.name} - {self.marks_obtained}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate grade and pass status
        percentage = (self.marks_obtained / self.examination.total_marks) * 100
        
        if percentage >= 90:
            self.grade = 'A+'
        elif percentage >= 80:
            self.grade = 'A'
        elif percentage >= 70:
            self.grade = 'B+'
        elif percentage >= 60:
            self.grade = 'B'
        elif percentage >= 50:
            self.grade = 'C+'
        elif percentage >= 40:
            self.grade = 'C'
        elif percentage >= 30:
            self.grade = 'D'
        else:
            self.grade = 'F'
        
        self.is_passed = self.marks_obtained >= self.examination.passing_marks
        super().save(*args, **kwargs)