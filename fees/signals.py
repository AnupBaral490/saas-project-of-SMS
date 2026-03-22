from django.db.models.signals import post_save
from django.dispatch import receiver
from academic.models import StudentEnrollment
from .models import FeeStructure, StudentFee


@receiver(post_save, sender=StudentEnrollment)
def create_student_fee_records(sender, instance, created, **kwargs):
    """
    Automatically create fee records when a student is enrolled in a class
    """
    if created and instance.is_active:
        # Get all active fee structures for the enrolled class
        fee_structures = FeeStructure.objects.filter(
            class_assigned=instance.class_enrolled,
            academic_year=instance.class_enrolled.academic_year,
            is_active=True
        )
        
        # Create student fee record for each fee structure
        for fee_structure in fee_structures:
            StudentFee.objects.get_or_create(
                student=instance.student,
                fee_structure=fee_structure,
                defaults={
                    'amount_due': fee_structure.total_fee,
                    'payment_status': 'pending'
                }
            )


@receiver(post_save, sender=StudentEnrollment)
def update_student_fee_on_enrollment_change(sender, instance, created, **kwargs):
    """
    Update fee records when enrollment status changes
    """
    if not created:
        # If enrollment is deactivated, mark fees as inactive or handle accordingly
        if not instance.is_active:
            # You can add logic here to handle fee records when enrollment is deactivated
            pass
