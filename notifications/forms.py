from django import forms
from .models import Notification
from accounts.models import User

class NotificationForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select users who should receive this notification"
    )
    
    class Meta:
        model = Notification
        fields = ['title', 'message', 'notification_type', 'priority', 'recipients', 'send_email']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter notification title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter your message here...'
            }),
            'notification_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'send_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter recipients based on user role
        if user and user.user_type == 'teacher':
            # Teachers can send to students in their classes
            self.fields['recipients'].queryset = User.objects.filter(
                user_type__in=['student']
            )
        elif user and user.user_type == 'admin':
            # Admins can send to everyone
            self.fields['recipients'].queryset = User.objects.exclude(id=user.id)
        else:
            # Others can't send notifications
            self.fields['recipients'].queryset = User.objects.none()

class QuickNotificationForm(forms.Form):
    RECIPIENT_CHOICES = [
        ('all_students', 'All Students'),
        ('all_teachers', 'All Teachers'),
        ('all_parents', 'All Parents'),
        ('all_users', 'All Users'),
    ]
    
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter notification title'
        })
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter your message here...'
        })
    )
    
    notification_type = forms.ChoiceField(
        choices=Notification.NOTIFICATION_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='medium'
    )
    
    recipient_group = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select which group should receive this notification"
    )
    
    send_email = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Also send notification via email"
    )