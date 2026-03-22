from django.urls import path
from . import views, teacher_admin_views

app_name = 'attendance'

urlpatterns = [
    # Student Attendance
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('mark/<int:session_id>/', views.mark_attendance_session, name='mark_attendance_session'),
    path('view/', views.view_attendance, name='view_attendance'),
    path('reports/', views.attendance_reports, name='attendance_reports'),
    
    # Real Teacher Attendance Tracking
    path('real-teacher-attendance/', views.real_teacher_attendance, name='real_teacher_attendance'),
    
    # Teacher Attendance (Admin)
    path('teacher-dashboard/', teacher_admin_views.teacher_attendance_dashboard, name='teacher_attendance_dashboard'),
    path('teacher-activities/', teacher_admin_views.teacher_detailed_activities, name='teacher_detailed_activities'),
    path('teacher-timeline/', teacher_admin_views.teacher_activity_timeline, name='teacher_activity_timeline'),
    path('teacher-reports/', teacher_admin_views.teacher_attendance_reports, name='teacher_attendance_reports'),
    path('teacher-export/', teacher_admin_views.export_teacher_attendance, name='export_teacher_attendance'),
    path('teacher-activity/', teacher_admin_views.teacher_activity_logs, name='teacher_activity_logs'),
    path('manual-teacher/', teacher_admin_views.manual_teacher_attendance, name='manual_teacher_attendance'),
    
    # AJAX endpoints
    path('ajax/get-students/', views.get_students_for_assignment, name='get_students_ajax'),
    path('ajax/save-attendance/', views.save_attendance_ajax, name='save_attendance_ajax'),
]