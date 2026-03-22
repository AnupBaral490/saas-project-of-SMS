from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Course, Class
from saas.utils import get_request_organization


def get_current_organization(request):
    return get_request_organization(request) or getattr(request.user, 'organization', None)

def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

@login_required
@user_passes_test(is_admin)
def get_courses_by_department(request):
    """API endpoint to get courses filtered by department"""
    department_id = request.GET.get('department')
    
    if not department_id:
        return JsonResponse({'error': 'Department ID is required'}, status=400)
    
    try:
        courses = Course.objects.filter(department_id=department_id)
        organization = get_current_organization(request)
        if organization:
            courses = courses.filter(organization=organization)
        courses = courses.values(
            'id', 'name', 'code'
        )
        return JsonResponse(list(courses), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@user_passes_test(is_admin)
def get_classes_by_course(request):
    """API endpoint to get classes filtered by course"""
    course_id = request.GET.get('course')
    
    if not course_id:
        return JsonResponse({'error': 'Course ID is required'}, status=400)
    
    try:
        classes = Class.objects.filter(course_id=course_id)
        organization = get_current_organization(request)
        if organization:
            classes = classes.filter(organization=organization)
        classes = classes.select_related(
            'academic_year'
        ).values(
            'id', 'name', 'year', 'semester', 'section', 'academic_year__year'
        )
        
        # Format the data for better display
        formatted_classes = []
        for class_obj in classes:
            formatted_classes.append({
                'id': class_obj['id'],
                'name': class_obj['name'],
                'year': class_obj['year'],
                'semester': class_obj['semester'],
                'section': class_obj['section'],
                'academic_year': class_obj['academic_year__year'],
                'display_name': f"Year {class_obj['year']}, Sem {class_obj['semester']} - {class_obj['section']} ({class_obj['academic_year__year']})"
            })
        
        return JsonResponse(formatted_classes, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)