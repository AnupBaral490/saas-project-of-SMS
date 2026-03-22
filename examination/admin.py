from django.contrib import admin
from .models import ExamType, Examination, ExamResult

@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'weightage')
    search_fields = ('name',)

@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'class_for', 'exam_date', 'total_marks', 'created_by')
    search_fields = ('name', 'subject__name', 'class_for__name')
    list_filter = ('exam_date', 'exam_type', 'subject', 'class_for')
    date_hierarchy = 'exam_date'

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'examination', 'marks_obtained', 'grade', 'is_passed')
    search_fields = ('student__user__username', 'student__student_id', 'examination__name')
    list_filter = ('grade', 'is_passed', 'examination__exam_type', 'examination__subject')
    readonly_fields = ('grade', 'is_passed')

