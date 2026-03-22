from django.db import models
from django.utils import timezone
from accounts.models import StudentProfile, TeacherProfile

class AcademicYear(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='academic_years', null=True, blank=True)
    year = models.CharField(max_length=20)  # e.g., "2023-2024"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'year'], name='unique_academic_year_per_org'),
        ]
    
    def __str__(self):
        return self.year
    
    def save(self, *args, **kwargs):
        if self.is_current:
            # Ensure only one academic year is current
            AcademicYear.objects.filter(organization=self.organization, is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

class Department(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='departments', null=True, blank=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'name'], name='unique_department_name_per_org'),
            models.UniqueConstraint(fields=['organization', 'code'], name='unique_department_code_per_org'),
        ]
    
    def __str__(self):
        return self.name

class Course(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='courses', null=True, blank=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    duration_years = models.PositiveIntegerField(default=4)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'code'], name='unique_course_code_per_org'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class Subject(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='subjects', null=True, blank=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.PositiveIntegerField()
    year = models.PositiveIntegerField()  # 1st year, 2nd year, etc.
    credits = models.PositiveIntegerField(default=3)
    description = models.TextField(blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'code', 'course'], name='unique_subject_code_course_per_org'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code}) - Year {self.year}, Sem {self.semester}"

class Class(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='classes', null=True, blank=True)
    name = models.CharField(max_length=50)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()  # 1st year, 2nd year, etc.
    semester = models.PositiveIntegerField()
    section = models.CharField(max_length=10)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    class_teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='class_teacher_for')
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'course', 'year', 'semester', 'section', 'academic_year'], name='unique_class_per_org'),
        ]
    
    def __str__(self):
        return f"{self.course.name} - Year {self.year}, Sem {self.semester} - {self.section}"

class StudentEnrollment(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='student_enrollments', null=True, blank=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE)
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'student', 'class_enrolled'], name='unique_student_class_enrollment_per_org'),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.class_enrolled}"


class SemesterEnrollment(models.Model):
    """
    Separate enrollment model for each semester.
    Allows students to enroll in specific semesters independently.
    """
    ENROLLMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ]
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='semester_enrollments', null=True, blank=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='semester_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()  # Academic year (1st, 2nd, 3rd, 4th)
    semester = models.PositiveIntegerField()  # Semester number (1-8)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    section = models.CharField(max_length=10, default='A')
    
    # Enrollment details
    enrollment_date = models.DateField(auto_now_add=True)
    enrollment_status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    
    # Additional fields for semester-specific enrollment
    enrollment_fee_paid = models.BooleanField(default=False)
    enrollment_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    enrollment_deadline = models.DateField(null=True, blank=True)
    
    # Approval workflow
    approved_by = models.ForeignKey('accounts.TeacherProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_enrollments')
    approved_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'student', 'course', 'year', 'semester', 'academic_year'], name='unique_semester_enrollment_per_org'),
        ]
        ordering = ['-academic_year__year', 'year', 'semester', 'student__user__first_name']
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.course.name} - Year {self.year}, Sem {self.semester}"
    
    @property
    def semester_display(self):
        return f"Year {self.year} - Semester {self.semester}"
    
    @property
    def can_enroll(self):
        """Check if student can enroll in this semester"""
        if self.enrollment_deadline and timezone.now().date() > self.enrollment_deadline:
            return False
        return self.enrollment_status in ['pending', 'approved']
    
    def approve_enrollment(self, approved_by_user):
        """Approve the semester enrollment"""
        self.enrollment_status = 'approved'
        self.approved_by = approved_by_user.teacher_profile if hasattr(approved_by_user, 'teacher_profile') else None
        self.approved_date = timezone.now()
        self.save()
    
    def reject_enrollment(self, reason=""):
        """Reject the semester enrollment"""
        self.enrollment_status = 'rejected'
        self.rejection_reason = reason
        self.save()


class TeacherSubjectAssignment(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='teacher_subject_assignments', null=True, blank=True)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'teacher', 'subject', 'class_assigned', 'academic_year'], name='unique_teacher_subject_assignment_per_org'),
        ]
    
    def __str__(self):
        return f"{self.teacher.user.get_full_name()} - {self.subject.name} - {self.class_assigned}"

class Assignment(models.Model):
    ASSIGNMENT_TYPES = (
        ('homework', 'Homework'),
        ('project', 'Project'),
        ('lab', 'Lab Work'),
        ('presentation', 'Presentation'),
        ('quiz', 'Quiz'),
    )
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPES, default='homework')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    assigned_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    max_marks = models.PositiveIntegerField(default=100)
    instructions = models.TextField(blank=True)
    attachment = models.FileField(upload_to='assignments/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.title} - {self.subject.name} - {self.class_assigned}"

class AssignmentSubmission(models.Model):
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='assignment_submissions', null=True, blank=True)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    submission_text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_late = models.BooleanField(default=False)
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'assignment', 'student'], name='unique_assignment_submission_per_org'),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.assignment.title}"
    
    def save(self, *args, **kwargs):
        # Check if submission is late
        if self.assignment_id and self.organization_id is None:
            self.organization = self.assignment.organization
        if self.submitted_at and self.assignment.due_date:
            self.is_late = self.submitted_at > self.assignment.due_date
        super().save(*args, **kwargs)