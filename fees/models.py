from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from academic.models import Class, AcademicYear
from accounts.models import StudentProfile


class FeeStructure(models.Model):
    """Class-wise fee structure definition"""
    FREQUENCY_CHOICES = (
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semester', 'Semester'),
        ('annual', 'Annual'),
    )
    
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='fee_structures')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    
    # Fee components
    tuition_fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    library_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    lab_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    sports_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    transport_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    other_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='semester')
    due_date = models.DateField()
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    late_fee_applicable_after_days = models.PositiveIntegerField(default=7)
    
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['class_assigned', 'academic_year', 'frequency']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.class_assigned.name} - {self.academic_year.year} - {self.get_frequency_display()}"
    
    @property
    def total_fee(self):
        """Calculate total fee amount"""
        return (
            (self.tuition_fee or 0) + 
            (self.library_fee or 0) + 
            (self.lab_fee or 0) + 
            (self.sports_fee or 0) + 
            (self.transport_fee or 0) + 
            (self.other_fee or 0)
        )
    
    def is_overdue(self):
        """Check if fee is overdue"""
        return timezone.now().date() > self.due_date


class StudentFee(models.Model):
    """Individual student fee payment tracking"""
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('cheque', 'Cheque'),
        ('card', 'Card'),
    )
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='fees')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='student_fees')
    
    # Payment details
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    late_fee_charged = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    remarks = models.TextField(blank=True)
    is_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'fee_structure']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.fee_structure} - {self.payment_status}"
    
    @property
    def balance_amount(self):
        """Calculate remaining balance"""
        return (
            (self.amount_due or 0) + 
            (self.late_fee_charged or 0) - 
            (self.amount_paid or 0) - 
            (self.discount_amount or 0)
        )
    
    @property
    def is_paid(self):
        """Check if fee is fully paid"""
        return self.balance_amount <= 0
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        if self.payment_status == 'paid':
            return False
        if not self.fee_structure_id:  # Check if fee_structure exists
            return False
        return timezone.now().date() > self.fee_structure.due_date
    
    def calculate_late_fee(self):
        """Calculate late fee if applicable"""
        if self.is_overdue and self.payment_status not in ['paid', 'waived']:
            days_overdue = (timezone.now().date() - self.fee_structure.due_date).days
            if days_overdue > self.fee_structure.late_fee_applicable_after_days:
                return self.fee_structure.late_fee_amount
        return 0
    
    def update_payment_status(self):
        """Update payment status based on amount paid"""
        if self.is_paid:
            self.payment_status = 'paid'
        elif self.amount_paid > 0:
            self.payment_status = 'partial'
        elif self.is_overdue:
            self.payment_status = 'overdue'
        else:
            self.payment_status = 'pending'
        self.save()
    
    def save(self, *args, **kwargs):
        # Auto-calculate late fee
        if not self.is_paid:
            self.late_fee_charged = self.calculate_late_fee()
        
        # Auto-update payment status
        if self.amount_paid >= (self.amount_due + self.late_fee_charged - self.discount_amount):
            self.payment_status = 'paid'
            if not self.payment_date:
                self.payment_date = timezone.now().date()
        elif self.amount_paid > 0:
            self.payment_status = 'partial'
        elif self.is_overdue:
            self.payment_status = 'overdue'
        
        super().save(*args, **kwargs)


class FeePayment(models.Model):
    """Track individual payment transactions"""
    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = models.CharField(max_length=20, choices=StudentFee.PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField(default=timezone.now)
    transaction_id = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=50, unique=True)
    
    collected_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-payment_date', '-created_at']
    
    def __str__(self):
        return f"Payment {self.receipt_number} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Generate receipt number if not provided
        if not self.receipt_number:
            from django.utils.crypto import get_random_string
            self.receipt_number = f"RCP-{timezone.now().strftime('%Y%m%d')}-{get_random_string(6).upper()}"
        
        super().save(*args, **kwargs)
        
        # Update student fee record
        self.student_fee.amount_paid += self.amount
        self.student_fee.payment_method = self.payment_method
        self.student_fee.transaction_id = self.transaction_id
        self.student_fee.update_payment_status()


class FeeWaiver(models.Model):
    """Track fee waivers/scholarships"""
    WAIVER_TYPE_CHOICES = (
        ('scholarship', 'Scholarship'),
        ('financial_aid', 'Financial Aid'),
        ('merit', 'Merit Based'),
        ('sibling', 'Sibling Discount'),
        ('other', 'Other'),
    )
    
    student_fee = models.ForeignKey(StudentFee, on_delete=models.CASCADE, related_name='waivers')
    waiver_type = models.CharField(max_length=20, choices=WAIVER_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    
    reason = models.TextField()
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    approved_date = models.DateField(default=timezone.now)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_waiver_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update student fee discount
        total_waiver = FeeWaiver.objects.filter(
            student_fee=self.student_fee,
            is_active=True
        ).aggregate(models.Sum('amount'))['amount__sum'] or 0
        
        self.student_fee.discount_amount = total_waiver
        self.student_fee.update_payment_status()
