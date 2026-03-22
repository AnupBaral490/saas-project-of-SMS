from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import User, StudentProfile, TeacherProfile, ParentProfile, AdminProfile
from saas.utils import get_request_organization, organization_allows_access, user_belongs_to_organization

class CustomLoginForm(AuthenticationForm):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'user-type-radio'
        }),
        required=True,
        label='I am a'
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user_type = self.cleaned_data.get('user_type')

        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Invalid username or password.",
                    code='invalid_login',
                )
            
            # Verify user type matches
            if self.user_cache.user_type != user_type:
                raise forms.ValidationError(
                    f"Invalid credentials for {user_type}. Please select the correct user type.",
                    code='invalid_user_type',
                )
            
            if not self.user_cache.is_active:
                raise forms.ValidationError(
                    "This account is inactive.",
                    code='inactive',
                )

            organization = get_request_organization(self.request)
            if organization and not user_belongs_to_organization(self.user_cache, organization):
                raise forms.ValidationError(
                    "This account does not belong to the current organization.",
                    code='invalid_organization',
                )

            if organization and not organization_allows_access(organization):
                raise forms.ValidationError(
                    "This organization's subscription is not active.",
                    code='inactive_subscription',
                )

        return self.cleaned_data

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=17, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 
                 'address', 'date_of_birth', 'password1', 'password2', 'user_type', 'profile_picture')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        
        # If this is an edit form (instance exists), make passwords optional
        if self.instance and self.instance.pk:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = 'Leave blank if you don\'t want to change the password.'
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        # If this is an edit and no password is provided, skip validation
        if self.instance and self.instance.pk and not password1 and not password2:
            return password2
        
        # Otherwise, use the default validation
        return super().clean_password2()
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Only set password if it's provided (for edit forms)
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data["password1"])
        elif not self.instance.pk:  # New user must have password
            user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
        return user

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['student_id', 'admission_date', 'guardian_name', 'guardian_phone', 
                 'guardian_email', 'emergency_contact', 'blood_group']
        widgets = {
            'admission_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class TeacherProfileForm(forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ['employee_id', 'qualification', 'experience_years', 
                 'specialization', 'joining_date']
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = ParentProfile
        fields = ['occupation']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class AdminPasswordResetForm(forms.Form):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Enter a new password for the user."
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Enter the same password as before, for verification."
    )
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn't match.")
        return password2
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            # You can add custom password validation here
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
        return password