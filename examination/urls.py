from django.urls import path
from . import views

app_name = 'examination'

urlpatterns = [
    path('exams/', views.exam_list, name='exam_list'),
    path('results/', views.result_list, name='result_list'),
    path('create-exam/', views.create_exam, name='create_exam'),
    path('enter-results/<int:exam_id>/', views.enter_results, name='enter_results'),
]