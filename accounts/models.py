from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('parent', 'Parent'),
    )
    
    organization = models.ForeignKey('saas.Organization', on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.organization:
            return f"{self.username} ({self.get_user_type_display()} - {self.organization.slug})"
        return f"{self.username} ({self.get_user_type_display()})"

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True, default=None)
    department = models.CharField(max_length=100, blank=True, default='')
    
    def __str__(self):
        return f"Admin: {self.user.get_full_name()}"

    
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    admission_date = models.DateField()
    guardian_name = models.CharField(max_length=100)
    guardian_phone = models.CharField(max_length=17)
    guardian_email = models.EmailField()
    emergency_contact = models.CharField(max_length=17)
    blood_group = models.CharField(max_length=5, blank=True)
    
    def __str__(self):
        full_name = self.user.get_full_name() or self.user.username
        return f"{full_name} ({self.student_id})"
    
    def get_current_enrollment(self):
        """Get the current active enrollment for this student."""
        from academic.models import StudentEnrollment, AcademicYear

        organization = self.user.organization
        
        # Try to get enrollment for current academic year first
        current_academic_year = AcademicYear.objects.filter(is_current=True, organization=organization).first()
        
        if current_academic_year:
            enrollment = StudentEnrollment.objects.filter(
                student=self,
                organization=organization,
                is_active=True,
                class_enrolled__academic_year=current_academic_year
            ).first()
            if enrollment:
                return enrollment
        
        # If no enrollment in current academic year, get the most recent active enrollment
        return StudentEnrollment.objects.filter(
            student=self,
            organization=organization,
            is_active=True
        ).order_by('-enrollment_date').first()

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True, default=None)
    qualification = models.CharField(max_length=200, blank=True, default='')
    experience_years = models.PositiveIntegerField(default=0)
    specialization = models.CharField(max_length=100, blank=True, default='')
    joining_date = models.DateField(blank=True, null=True, default=None)
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username

class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    occupation = models.CharField(max_length=100)
    children = models.ManyToManyField(StudentProfile, related_name='parents')
    
    def __str__(self):
        return f"Parent: {self.user.get_full_name()}"


class ParentTeacherMessage(models.Model):
    """Messages between parents and teachers"""
    
    MESSAGE_STATUS = (
        ('sent', 'Sent'),
        ('read', 'Read'),
        ('replied', 'Replied'),
    )
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='related_messages', null=True, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=MESSAGE_STATUS, default='sent')
    parent_read = models.BooleanField(default=False)
    teacher_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    replied_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.sender.get_full_name()} to {self.recipient.get_full_name()}: {self.subject}"
    
    def mark_as_read(self, user):
        """Mark message as read by the user"""
        from django.utils import timezone
        if not self.read_at:
            self.read_at = timezone.now()
        
        if user.user_type == 'parent':
            self.parent_read = True
        elif user.user_type == 'teacher':
            self.teacher_read = True
            
        if self.status == 'sent':
            self.status = 'read'
        
        self.save()