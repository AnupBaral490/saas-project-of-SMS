from django.urls import path
from . import views, api_views

app_name = 'academic'

urlpatterns = [
    # API endpoints
    path('api/courses/', api_views.get_courses_by_department, name='api_courses_by_department'),
    path('api/classes/', api_views.get_classes_by_course, name='api_classes_by_course'),
    
    # Department URLs
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.create_department, name='create_department'),
    path('departments/<int:department_id>/edit/', views.edit_department, name='edit_department'),
    path('departments/<int:department_id>/delete/', views.delete_department, name='delete_department'),
    
    # Course URLs
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/create/', views.create_course, name='create_course'),
    path('courses/create-enhanced/', views.create_course_enhanced, name='create_course_enhanced'),
    path('courses/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    
    # Subject URLs
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.create_subject, name='create_subject'),
    path('subjects/<int:subject_id>/edit/', views.edit_subject, name='edit_subject'),
    
    # Class URLs
    path('classes/', views.class_list, name='class_list'),
    path('classes/create/', views.create_class, name='create_class'),
    path('classes/<int:class_id>/', views.class_detail, name='class_detail'),
    
    # Enrollment URLs
    path('enrollments/', views.enrollment_list, name='enrollment_list'),
    path('enrollments/manage/', views.manage_student_enrollment, name='manage_student_enrollment'),
    path('enrollments/create/', views.create_student_enrollment, name='create_student_enrollment'),
    path('enrollments/<int:enrollment_id>/edit/', views.edit_student_enrollment, name='edit_student_enrollment'),
    path('enrollments/report/', views.student_enrollment_report, name='student_enrollment_report'),
    path('enrollments/semester-report/', views.semester_wise_enrollment_report, name='semester_wise_enrollment_report'),
    path('enrollments/<int:enrollment_id>/toggle-status/', views.toggle_enrollment_status, name='toggle_enrollment_status'),
    
    # Semester-specific enrollment URLs
    path('semester-enrollments/', views.manage_semester_enrollments, name='manage_semester_enrollments'),
    path('semester-enrollments/create/', views.create_semester_enrollment, name='create_semester_enrollment'),
    path('semester-enrollments/<int:enrollment_id>/edit/', views.edit_semester_enrollment, name='edit_semester_enrollment'),
    path('semester-enrollments/<int:enrollment_id>/approve/', views.approve_semester_enrollment, name='approve_semester_enrollment'),
    path('semester-enrollments/<int:enrollment_id>/reject/', views.reject_semester_enrollment, name='reject_semester_enrollment'),
    path('semester-enrollments/bulk/', views.bulk_semester_enrollment, name='bulk_semester_enrollment'),
    path('semester-enrollments/report/', views.semester_enrollment_report, name='semester_enrollment_report'),
    
    # Teacher Assignment URLs
    path('teacher-assignments/', views.teacher_assignments, name='teacher_assignments'),
    path('teacher-assignments/create/', views.assign_teacher, name='assign_teacher'),
    path('teacher-assignments/<int:assignment_id>/edit/', views.edit_teacher_assignment, name='edit_teacher_assignment'),
    path('teacher/class/<int:class_id>/students/', views.teacher_class_students, name='teacher_class_students'),
    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/create/', views.create_assignment, name='create_assignment'),
    path('assignments/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('assignments/<int:assignment_id>/edit/', views.edit_assignment, name='edit_assignment'),
    path('assignments/<int:assignment_id>/submissions/', views.assignment_submissions, name='assignment_submissions'),
    path('assignments/student/', views.student_assignments, name='student_assignments'),
    path('assignments/<int:assignment_id>/submit/', views.submit_assignment, name='submit_assignment'),
]