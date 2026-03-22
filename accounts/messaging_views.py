"""
Parent-Teacher Messaging Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from accounts.models import ParentTeacherMessage, User, StudentProfile, TeacherProfile
from academic.models import TeacherSubjectAssignment


@login_required
def contact_teachers(request):
    """Parent view to contact their children's teachers"""
    if request.user.user_type != 'parent':
        messages.error(request, 'Only parents can access this page.')
        return redirect('accounts:dashboard')
    
    parent_profile = request.user.parent_profile
    children = parent_profile.children.all()
    
    # Get all teachers for the children
    teachers_data = []
    for child in children:
        enrollment = child.get_current_enrollment()
        if enrollment:
            # Get teachers assigned to this child's class
            teacher_assignments = TeacherSubjectAssignment.objects.filter(
                class_assigned=enrollment.class_enrolled
            ).select_related('teacher__user', 'subject')
            
            for assignment in teacher_assignments:
                teachers_data.append({
                    'teacher': assignment.teacher,
                    'subject': assignment.subject,
                    'child': child,
                    'class': enrollment.class_enrolled
                })
    
    # Remove duplicates
    unique_teachers = {}
    for data in teachers_data:
        teacher_id = data['teacher'].id
        if teacher_id not in unique_teachers:
            unique_teachers[teacher_id] = {
                'teacher': data['teacher'],
                'subjects': [data['subject']],
                'children': [data['child']],
                'classes': [data['class']]
            }
        else:
            if data['subject'] not in unique_teachers[teacher_id]['subjects']:
                unique_teachers[teacher_id]['subjects'].append(data['subject'])
            if data['child'] not in unique_teachers[teacher_id]['children']:
                unique_teachers[teacher_id]['children'].append(data['child'])
            if data['class'] not in unique_teachers[teacher_id]['classes']:
                unique_teachers[teacher_id]['classes'].append(data['class'])
    
    context = {
        'children': children,
        'teachers_data': unique_teachers.values()
    }
    
    return render(request, 'accounts/contact_teachers.html', context)


@login_required
def send_message(request, teacher_id=None, student_id=None):
    """Send a message to a teacher"""
    if request.user.user_type != 'parent':
        messages.error(request, 'Only parents can send messages to teachers.')
        return redirect('accounts:dashboard')
    
    teacher = None
    student = None
    teachers = []
    
    # Get parent's children for the form
    children = request.user.parent_profile.children.all()
    
    # Handle GET parameters
    if not student_id:
        student_id = request.GET.get('student_id')
    
    if student_id:
        student = get_object_or_404(StudentProfile, id=student_id)
        # Verify this student is the parent's child
        if student not in children:
            messages.error(request, 'You can only send messages about your own children.')
            return redirect('accounts:contact_teachers')
        
        # Get teachers for this student
        enrollment = student.get_current_enrollment()
        if enrollment:
            teacher_assignments = TeacherSubjectAssignment.objects.filter(
                class_assigned=enrollment.class_enrolled
            ).select_related('teacher__user', 'subject')
            
            teachers_dict = {}
            for ta in teacher_assignments:
                if ta.teacher.id not in teachers_dict:
                    teachers_dict[ta.teacher.id] = {
                        'teacher': ta.teacher,
                        'subjects': []
                    }
                teachers_dict[ta.teacher.id]['subjects'].append(ta.subject)
            
            teachers = list(teachers_dict.values())
    
    if teacher_id:
        teacher = get_object_or_404(TeacherProfile, id=teacher_id)
    
    if request.method == 'POST':
        subject_text = request.POST.get('subject')
        message_text = request.POST.get('message')
        teacher_id = request.POST.get('teacher_id')
        student_id = request.POST.get('student_id')
        
        if not all([subject_text, message_text, teacher_id, student_id]):
            messages.error(request, 'Please fill in all required fields.')
        else:
            teacher = get_object_or_404(TeacherProfile, id=teacher_id)
            student = get_object_or_404(StudentProfile, id=student_id)
            
            # Verify student is parent's child
            if student not in children:
                messages.error(request, 'You can only send messages about your own children.')
                return redirect('accounts:contact_teachers')
            
            # Create message
            ParentTeacherMessage.objects.create(
                sender=request.user,
                recipient=teacher.user,
                student=student,
                subject=subject_text,
                message=message_text
            )
            
            messages.success(request, f'Message sent to {teacher.user.get_full_name()} successfully!')
            return redirect('accounts:message_inbox')
    
    context = {
        'teacher': teacher,
        'student': student,
        'children': children,
        'teachers': teachers
    }
    
    return render(request, 'accounts/send_message.html', context)


@login_required
def message_inbox(request):
    """View inbox for both parents and teachers"""
    if request.user.user_type == 'parent':
        # Parent's inbox
        messages_list = ParentTeacherMessage.objects.filter(
            Q(sender=request.user) | Q(recipient=request.user)
        ).select_related('sender', 'recipient', 'student__user').order_by('-created_at')
        
        # Mark received messages as read
        unread_messages = messages_list.filter(recipient=request.user, parent_read=False)
        for msg in unread_messages:
            msg.mark_as_read(request.user)
        
    elif request.user.user_type == 'teacher':
        # Teacher's inbox
        messages_list = ParentTeacherMessage.objects.filter(
            Q(sender=request.user) | Q(recipient=request.user)
        ).select_related('sender', 'recipient', 'student__user').order_by('-created_at')
        
        # Mark received messages as read
        unread_messages = messages_list.filter(recipient=request.user, teacher_read=False)
        for msg in unread_messages:
            msg.mark_as_read(request.user)
    else:
        messages.error(request, 'Only parents and teachers can access messages.')
        return redirect('accounts:dashboard')
    
    context = {
        'messages_list': messages_list
    }
    
    return render(request, 'accounts/message_inbox.html', context)


@login_required
def message_detail(request, message_id):
    """View a specific message and reply"""
    message = get_object_or_404(ParentTeacherMessage, id=message_id)
    
    # Check permission
    if request.user not in [message.sender, message.recipient]:
        messages.error(request, 'You do not have permission to view this message.')
        return redirect('accounts:message_inbox')
    
    # Mark as read
    message.mark_as_read(request.user)
    
    # Handle reply
    if request.method == 'POST':
        reply_text = request.POST.get('reply')
        if reply_text:
            # Find the root message for threading
            root_message = message
            while root_message.replied_to:
                root_message = root_message.replied_to
            
            # Create reply
            ParentTeacherMessage.objects.create(
                sender=request.user,
                recipient=message.sender if message.recipient == request.user else message.recipient,
                student=message.student,
                subject=f"Re: {root_message.subject}" if not root_message.subject.startswith("Re:") else root_message.subject,
                message=reply_text,
                replied_to=root_message
            )
            
            # Update original message status
            root_message.status = 'replied'
            root_message.save()
            
            messages.success(request, 'Reply sent successfully!')
            return redirect('accounts:message_inbox')
    
    # Get all messages in this thread
    # Find the root message (the one without replied_to)
    root_message = message
    while root_message.replied_to:
        root_message = root_message.replied_to
    
    # Get all messages in the thread (root + all replies)
    thread_messages = ParentTeacherMessage.objects.filter(
        Q(id=root_message.id) | Q(replied_to=root_message)
    ).select_related('sender', 'student__user').order_by('created_at')
    
    context = {
        'message': message,
        'thread_messages': thread_messages
    }
    
    return render(request, 'accounts/message_detail.html', context)
