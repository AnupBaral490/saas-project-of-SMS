from django.contrib import admin
from django.forms import ModelForm, ModelMultipleChoiceField, CheckboxSelectMultiple
from .models import (
    AcademicYear, Department, Course, Subject, Class, 
    StudentEnrollment, SemesterEnrollment, TeacherSubjectAssignment, Assignment, AssignmentSubmission
)
from accounts.models import StudentProfile, TeacherProfile

# Inline admin classes for Course management
class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1
    fields = ('name', 'code', 'year', 'semester', 'credits')

class ClassInline(admin.TabularInline):
    model = Class
    extra = 1
    fields = ('name', 'year', 'semester', 'section', 'academic_year', 'class_teacher')
    autocomplete_fields = ['class_teacher']

# Inline admin classes for Class management
class StudentEnrollmentInline(admin.TabularInline):
    model = StudentEnrollment
    extra = 0
    fields = ('student', 'enrollment_date', 'is_active')
    readonly_fields = ('enrollment_date',)
    autocomplete_fields = ['student']
    verbose_name = "Enrolled Student"
    verbose_name_plural = "Enrolled Students"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student__user')

class TeacherSubjectAssignmentInline(admin.TabularInline):
    model = TeacherSubjectAssignment
    extra = 0
    fields = ('teacher', 'subject', 'academic_year')
    readonly_fields = ('academic_year',)
    autocomplete_fields = ['teacher', 'subject']
    verbose_name = "Teacher Assignment"
    verbose_name_plural = "Teacher Assignments"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('teacher__user', 'subject', 'academic_year')

# Custom form for Course admin with multiple student selection
class CourseAdminForm(ModelForm):
    students = ModelMultipleChoiceField(
        queryset=StudentProfile.objects.all(),
        widget=CheckboxSelectMultiple,
        required=False,
        help_text="Select students to enroll in this course"
    )
    
    teachers = ModelMultipleChoiceField(
        queryset=TeacherProfile.objects.all(),
        widget=CheckboxSelectMultiple,
        required=False,
        help_text="Select teachers to assign to this course"
    )
    
    class Meta:
        model = Course
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Pre-populate with currently enrolled students
            enrolled_students = StudentProfile.objects.filter(
                studentenrollment__class_enrolled__course=self.instance,
                studentenrollment__is_active=True
            )
            self.fields['students'].initial = enrolled_students
            
            # Pre-populate with currently assigned teachers
            assigned_teachers = TeacherProfile.objects.filter(
                teachersubjectassignment__subject__course=self.instance
            ).distinct()
            self.fields['teachers'].initial = assigned_teachers

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('year', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('year',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'head_of_department')
    search_fields = ('name', 'code')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ('name', 'code', 'department', 'duration_years', 'get_total_students', 'get_total_classes', 'get_total_teachers')
    search_fields = ('name', 'code')
    list_filter = ('department', 'duration_years')
    inlines = [SubjectInline, ClassInline]
    actions = ['create_default_structure']
    
    fieldsets = (
        ('Course Information', {
            'fields': ('name', 'code', 'department', 'duration_years', 'description')
        }),
        ('Student Management', {
            'fields': ('students',),
            'description': 'Select students to enroll in this course. They will be automatically enrolled in the appropriate class.',
            'classes': ('collapse',)
        }),
        ('Teacher Management', {
            'fields': ('teachers',),
            'description': 'Select teachers to assign to this course. They will be assigned to teach subjects in this course.',
            'classes': ('collapse',)
        }),
    )
    
    def get_total_students(self, obj):
        from django.db.models import Count
        return StudentEnrollment.objects.filter(
            class_enrolled__course=obj, 
            is_active=True
        ).count()
    get_total_students.short_description = 'Total Students'
    
    def get_total_classes(self, obj):
        return obj.class_set.count()
    get_total_classes.short_description = 'Total Classes'
    
    def get_total_teachers(self, obj):
        return TeacherSubjectAssignment.objects.filter(
            subject__course=obj
        ).values('teacher').distinct().count()
    get_total_teachers.short_description = 'Total Teachers'
    
    def create_default_structure(self, request, queryset):
        """Create default class and subject structure for selected courses"""
        for course in queryset:
            # Create default academic year if not exists
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_year:
                from datetime import date
                current_year = AcademicYear.objects.create(
                    year="2025-2026",
                    start_date=date(2025, 8, 1),
                    end_date=date(2026, 7, 31),
                    is_current=True
                )
                self.message_user(request, f"Created default academic year: {current_year.year}")
            
            # Create default class if not exists
            default_class, created = Class.objects.get_or_create(
                course=course,
                year=1,
                semester=1,
                section='A',
                defaults={
                    'name': f"{course.name} - Year 1, Sem 1 - A",
                    'academic_year': current_year
                }
            )
            
            if created:
                self.message_user(request, f"Created default class for {course.name}")
        
        self.message_user(request, f"Processed {queryset.count()} courses")
    create_default_structure.short_description = "Create default class structure for selected courses"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Handle student enrollments
        if 'students' in form.cleaned_data:
            selected_students = form.cleaned_data['students']
            
            # Get or create current academic year
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_year:
                # Create a default academic year if none exists
                from datetime import date
                current_year = AcademicYear.objects.create(
                    year="2025-2026",
                    start_date=date(2025, 8, 1),
                    end_date=date(2026, 7, 31),
                    is_current=True
                )
            
            # Get or create a default class for this course
            default_class, created = Class.objects.get_or_create(
                course=obj,
                year=1,
                semester=1,
                section='A',
                defaults={
                    'name': f"{obj.name} - Year 1, Sem 1 - A",
                    'academic_year': current_year
                }
            )
            
            # Deactivate all current enrollments for this course
            StudentEnrollment.objects.filter(
                class_enrolled__course=obj
            ).update(is_active=False)
            
            # Create new enrollments for selected students
            for student in selected_students:
                StudentEnrollment.objects.update_or_create(
                    student=student,
                    class_enrolled=default_class,
                    defaults={'is_active': True}
                )
        
        # Handle teacher assignments
        if 'teachers' in form.cleaned_data:
            selected_teachers = form.cleaned_data['teachers']
            
            # Get current academic year
            current_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_year:
                # Create a default academic year if none exists
                from datetime import date
                current_year = AcademicYear.objects.create(
                    year="2025-2026",
                    start_date=date(2025, 8, 1),
                    end_date=date(2026, 7, 31),
                    is_current=True
                )
            
            # Remove existing assignments for this course
            TeacherSubjectAssignment.objects.filter(
                subject__course=obj
            ).delete()
            
            # Create new assignments for selected teachers
            subjects = Subject.objects.filter(course=obj)
            classes = Class.objects.filter(course=obj)
            
            for teacher in selected_teachers:
                for subject in subjects:
                    for class_obj in classes:
                        TeacherSubjectAssignment.objects.get_or_create(
                            teacher=teacher,
                            subject=subject,
                            class_assigned=class_obj,
                            academic_year=current_year
                        )

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'course', 'year', 'semester', 'credits')
    search_fields = ('name', 'code')
    list_filter = ('course', 'year', 'semester', 'credits')

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'year', 'semester', 'section', 'academic_year', 'class_teacher', 'get_student_count', 'get_teacher_count')
    search_fields = ('name', 'section')
    list_filter = ('course', 'year', 'semester', 'academic_year')
    autocomplete_fields = ['class_teacher']
    inlines = [StudentEnrollmentInline, TeacherSubjectAssignmentInline]
    
    fieldsets = (
        ('Class Information', {
            'fields': ('name', 'course', 'year', 'semester', 'section', 'academic_year', 'class_teacher')
        }),
    )
    
    def get_student_count(self, obj):
        return obj.studentenrollment_set.filter(is_active=True).count()
    get_student_count.short_description = 'Students Enrolled'
    
    def get_teacher_count(self, obj):
        return TeacherSubjectAssignment.objects.filter(class_assigned=obj).values('teacher').distinct().count()
    get_teacher_count.short_description = 'Teachers Assigned'

    def save_formset(self, request, form, formset, change):
        if formset.model is TeacherSubjectAssignment:
            instances = formset.save(commit=False)
            for instance in instances:
                if instance.academic_year_id is None:
                    instance.academic_year = form.instance.academic_year
                instance.save()
            formset.save_m2m()
            return
        super().save_formset(request, form, formset, change)

@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('get_student_name', 'get_student_id', 'enrollment_date', 'is_active')
    search_fields = ('student__user__username', 'student__student_id', 'student__user__first_name', 'student__user__last_name', 'class_enrolled__course__name', 'class_enrolled__course__department__name')
    list_filter = (
        'is_active',
        ('class_enrolled__course', admin.RelatedOnlyFieldListFilter),
        ('class_enrolled', admin.RelatedOnlyFieldListFilter),
        ('class_enrolled__course__department', admin.RelatedOnlyFieldListFilter),
        'class_enrolled__year',
        'class_enrolled__semester',
        'enrollment_date',
    )
    actions = ['activate_enrollment', 'deactivate_enrollment', 'bulk_enroll_students']
    autocomplete_fields = ['student']
    ordering = ('class_enrolled__course__name', 'class_enrolled__year', 'class_enrolled__semester', 'class_enrolled__section', 'student__user__first_name')
    list_per_page = 100
    
    change_list_template = 'admin/academic/studentenrollment_change_list.html'
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Enrollment Details', {
            'fields': ('class_enrolled', 'is_active'),
            'description': 'Select the class to enroll the student in. The course and department will be automatically determined from the class.'
        }),
    )
    
    def changelist_view(self, request, extra_context=None):
        """Override to add grouped data"""
        from collections import defaultdict
        
        # Get the filtered queryset
        response = super().changelist_view(request, extra_context=extra_context)
        
        # If it's not a TemplateResponse, return as is
        if not hasattr(response, 'context_data'):
            return response
        
        # Get all enrollments with optimized query
        enrollments = self.get_queryset(request).select_related(
            'student__user',
            'class_enrolled__course__department',
            'class_enrolled__course',
            'class_enrolled__academic_year'
        )
        
        # Apply filters from the changelist
        cl = response.context_data['cl']
        enrollments = cl.get_queryset(request)
        
        # Group enrollments by class
        grouped_enrollments = defaultdict(list)
        for enrollment in enrollments:
            class_key = enrollment.class_enrolled
            grouped_enrollments[class_key].append(enrollment)
        
        # Sort groups by course name, year, semester
        sorted_groups = sorted(
            grouped_enrollments.items(),
            key=lambda x: (
                x[0].course.name,
                x[0].year,
                x[0].semester,
                x[0].section
            )
        )
        
        # Add to context
        extra_context = extra_context or {}
        extra_context['grouped_enrollments'] = sorted_groups
        extra_context['total_classes'] = len(sorted_groups)
        
        response.context_data.update(extra_context)
        return response
    
    def get_queryset(self, request):
        """Optimize queryset with select_related to reduce database queries"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'student__user',
            'class_enrolled__course__department',
            'class_enrolled__course',
            'class_enrolled__academic_year'
        )
    
    def get_student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'student__user__first_name'
    
    def get_student_id(self, obj):
        return obj.student.student_id
    get_student_id.short_description = 'Student ID'
    get_student_id.admin_order_field = 'student__student_id'
    
    def activate_enrollment(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"✅ {queryset.count()} enrollments activated.")
    activate_enrollment.short_description = "✅ Activate selected enrollments"
    
    def deactivate_enrollment(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"❌ {queryset.count()} enrollments deactivated.")
    deactivate_enrollment.short_description = "❌ Deactivate selected enrollments"
    
    def bulk_enroll_students(self, request, queryset):
        """Bulk enroll multiple students in the same class"""
        if queryset.count() > 1:
            # Get the first enrollment's class as template
            template_enrollment = queryset.first()
            class_enrolled = template_enrollment.class_enrolled
            
            # Update all selected enrollments to use the same class
            updated_count = 0
            for enrollment in queryset:
                if enrollment.class_enrolled != class_enrolled:
                    enrollment.class_enrolled = class_enrolled
                    enrollment.is_active = True
                    enrollment.save()
                    updated_count += 1
            
            self.message_user(request, f"📝 {updated_count} students enrolled in {class_enrolled}")
        else:
            self.message_user(request, "⚠️ Please select multiple enrollments for bulk operation.")
    bulk_enroll_students.short_description = "📝 Enroll selected students in same class as first selected"

@admin.register(TeacherSubjectAssignment)
class TeacherSubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ('get_teacher_name', 'subject', 'class_assigned', 'academic_year', 'get_student_count')
    search_fields = ('teacher__user__username', 'teacher__user__first_name', 'teacher__user__last_name', 'subject__name')
    list_filter = ('academic_year', 'subject', 'class_assigned__course')
    autocomplete_fields = ['teacher']
    
    def get_teacher_name(self, obj):
        return obj.teacher.user.get_full_name() or obj.teacher.user.username
    get_teacher_name.short_description = 'Teacher Name'
    
    def get_student_count(self, obj):
        return obj.class_assigned.studentenrollment_set.filter(is_active=True).count()
    get_student_count.short_description = 'Students in Class'

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'class_assigned', 'teacher', 'assigned_date', 'due_date', 'is_active')
    search_fields = ('title', 'subject__name', 'teacher__user__username')
    list_filter = ('assignment_type', 'assigned_date', 'due_date', 'is_active', 'subject')
    date_hierarchy = 'assigned_date'
    autocomplete_fields = ['teacher', 'subject', 'class_assigned']

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'submitted_at', 'is_late', 'marks_obtained', 'graded_by')
    search_fields = ('student__user__username', 'assignment__title')
    list_filter = ('submitted_at', 'is_late', 'graded_at', 'assignment__subject')
    date_hierarchy = 'submitted_at'
    autocomplete_fields = ['student', 'assignment', 'graded_by']

@admin.register(SemesterEnrollment)
class SemesterEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        'get_student_name', 'get_student_id', 'course', 'get_semester_display', 
        'enrollment_status', 'enrollment_date', 'enrollment_fee_paid', 'approved_by'
    )
    search_fields = (
        'student__user__username', 'student__student_id', 'student__user__first_name', 
        'student__user__last_name', 'course__name', 'course__department__name'
    )
    list_filter = (
        'enrollment_status',
        'enrollment_fee_paid',
        'is_active',
        ('course', admin.RelatedOnlyFieldListFilter),
        ('course__department', admin.RelatedOnlyFieldListFilter),
        'year',
        'semester',
        ('academic_year', admin.RelatedOnlyFieldListFilter),
        'enrollment_date',
        'approved_date',
    )
    actions = ['approve_enrollments', 'reject_enrollments', 'mark_fee_paid', 'mark_fee_unpaid']
    autocomplete_fields = ['student', 'approved_by']
    ordering = ('course__name', 'year', 'semester', 'student__user__first_name')
    list_per_page = 100
    date_hierarchy = 'enrollment_date'
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Course Information', {
            'fields': ('course', 'year', 'semester', 'academic_year', 'section')
        }),
        ('Enrollment Details', {
            'fields': ('enrollment_status', 'enrollment_fee_amount', 'enrollment_fee_paid', 'enrollment_deadline')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_date', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    readonly_fields = ('enrollment_date', 'created_at', 'updated_at', 'approved_date')
    
    def get_student_name(self, obj):
        return obj.student.user.get_full_name() or obj.student.user.username
    get_student_name.short_description = 'Student Name'
    get_student_name.admin_order_field = 'student__user__first_name'
    
    def get_student_id(self, obj):
        return obj.student.student_id
    get_student_id.short_description = 'Student ID'
    get_student_id.admin_order_field = 'student__student_id'
    
    def get_semester_display(self, obj):
        return f"Year {obj.year}, Sem {obj.semester}"
    get_semester_display.short_description = 'Year/Semester'
    get_semester_display.admin_order_field = 'year'
    
    def approve_enrollments(self, request, queryset):
        updated = 0
        for enrollment in queryset.filter(enrollment_status='pending'):
            enrollment.approve_enrollment(request.user)
            updated += 1
        
        self.message_user(request, f'{updated} enrollments were approved.')
    approve_enrollments.short_description = "Approve selected enrollments"
    
    def reject_enrollments(self, request, queryset):
        updated = queryset.filter(enrollment_status='pending').update(
            enrollment_status='rejected',
            rejection_reason='Bulk rejection by admin'
        )
        self.message_user(request, f'{updated} enrollments were rejected.')
    reject_enrollments.short_description = "Reject selected enrollments"
    
    def mark_fee_paid(self, request, queryset):
        updated = queryset.update(enrollment_fee_paid=True)
        self.message_user(request, f'{updated} enrollments marked as fee paid.')
    mark_fee_paid.short_description = "Mark fee as paid"
    
    def mark_fee_unpaid(self, request, queryset):
        updated = queryset.update(enrollment_fee_paid=False)
        self.message_user(request, f'{updated} enrollments marked as fee unpaid.')
    mark_fee_unpaid.short_description = "Mark fee as unpaid"