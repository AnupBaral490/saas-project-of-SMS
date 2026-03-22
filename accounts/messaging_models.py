"""
Parent-Teacher Messaging Models
"""
from django.db import models
from django.utils import timezone
from accounts.models import User, ParentProfile, TeacherProfile, StudentProfile


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
        if not self.read_at:
            self.read_at = timezone.now()
        
        if user.user_type == 'parent':
            self.parent_read = True
        elif user.user_type == 'teacher':
            self.teacher_read = True
            
        if self.status == 'sent':
            self.status = 'read'
        
        self.save()
