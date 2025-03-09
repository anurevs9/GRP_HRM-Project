from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

from django.db import models

class Role(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('TEAM_LEADER', 'Team Leader'),
        ('EMPLOYEE', 'Employee'),
    )
    name = models.CharField(max_length=100, choices=ROLE_CHOICES)
    description = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)  # Add status field, default to True (active)

    def __str__(self):
        return self.name

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    employee_id = models.CharField(max_length=10, unique=True)
    phone = models.CharField(max_length=15)  # Maps to 'mobile'
    address = models.TextField()
    date_joined = models.DateField()  # Maps to 'date_of_joining'
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    reporting_manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_employees')  # New field
    created_at = models.DateTimeField(auto_now_add=True)  # New field
    updated_at = models.DateTimeField(auto_now=True)  # New field

    def __str__(self):
        return self.user.get_full_name()

class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    task_title = models.CharField(max_length=100)
    task_description = models.CharField(max_length=200)
    task_priority = models.CharField(max_length=200, choices=(('HIGH', 'High'), ('MEDIUM', 'Medium'), ('LOW', 'Low')), default='MEDIUM')
    start_date = models.DateField()
    end_date = models.DateField()
    task_type = models.CharField(max_length=50, choices=(('INDIVIDUAL', 'Individual'), ('TEAM', 'Team')), default='INDIVIDUAL')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.task_title

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date.")
        super().save(*args, **kwargs)

class TaskAssignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)  # Unique identification of task assignment
    task = models.ForeignKey(Task, on_delete=models.CASCADE)  # Reference of id column in task table
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)  # Reference of id column in employee table
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE)  # Reference of the id column in employee table who assigns
    assigned_date = models.DateTimeField(auto_now_add=True)  # Timestamp at which task is assigned
    status = models.CharField(max_length=200, choices=(
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ), default='PENDING')  # Status of the task
    completed_at = models.DateTimeField(null=True, blank=True)  # Timestamp at which the task is marked completed

    def __str__(self):
        return f"Assignment {self.assignment_id} for {self.task.task_title}"

    def save(self, *args, **kwargs):
        if self.status == 'COMPLETED' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class Leave(models.Model):
    leaveid = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='employeeid', related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=[
        ('SL', 'Sick Leave'),
        ('CL', 'Casual Leave'),
        ('PL', 'Privileged Leave'),
        ('LWP', 'Leave Without Pay'),
    ], default='SL')
    reason = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ], default='PENDING')
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    created_at = models.DateTimeField(auto_now_add=True)  # New field to track when leave was applied

    def __str__(self):
        return f"Leave {self.leaveid} - {self.employee}"

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            self.total_days = delta.days + 1
        super().save(*args, **kwargs)

# core/models.py
class LeaveQuota(models.Model):
    quotaid = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='employeeid', related_name='leave_quotas')
    leave_type = models.CharField(max_length=20, choices=[
        ('SL', 'Sick Leave'),
        ('CL', 'Casual Leave'),
        ('PL', 'Privileged Leave'),
        ('LWP', 'Leave Without Pay'),
    ], default='SL')
    total_quota = models.IntegerField(default=0)
    used_quota = models.IntegerField(default=0)
    remain_quota = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ], default='PENDING')  # New field

    def __str__(self):
        return f"Quota {self.quotaid} - {self.employee}"

    def save(self, *args, **kwargs):
        self.remain_quota = self.total_quota - self.used_quota
        if self.remain_quota < 0:
            raise ValueError("Used quota cannot exceed total quota.")
        super().save(*args, **kwargs)


# Define a default function for review_date
def get_default_review_date():
    return timezone.now().date()

class Performance(models.Model):
    RATING_CHOICES = (
        (1, '1 - Poor'),
        (2, '2'),
        (3, '3'),
        (4, '4'),
        (5, '5'),
        (6, '6'),
        (7, '7'),
        (8, '8'),
        (9, '9'),
        (10, '10 - Excellent'),
    )
    REVIEW_PERIOD_CHOICES = (
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('ANNUAL', 'Annual'),
    )
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='performance_reviews')
    review_title = models.CharField(max_length=100)
    review_period = models.CharField(max_length=50, choices=REVIEW_PERIOD_CHOICES)
    rating = models.IntegerField(choices=RATING_CHOICES)
    feedback = models.TextField(max_length=300)  # Changed to TextField for multi-line input
    reviewed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviewed_performances')
    review_date = models.DateField(default=get_default_review_date)  # Use the callable function
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.review_period} - {self.review_title}"

    class Meta:
        verbose_name = "Performance Review"
        verbose_name_plural = "Performance Reviews"
        ordering = ['-review_date']


class Recruitment(models.Model):
    POSITION_STATUS = [
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('CLOSED', 'Closed')
    ]

    title = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    description = models.TextField()
    requirements = models.TextField()
    positions = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=POSITION_STATUS, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField()

    def __str__(self):
        return self.title


class Candidate(models.Model):
    STAGE_CHOICES = [
        ('APPLIED', 'Applied'),
        ('SCREENING', 'Screening'),
        ('INTERVIEW', 'Interview'),
        ('OFFER', 'Offer'),
        ('HIRED', 'Hired'),
        ('REJECTED', 'Rejected')
    ]

    position = models.ForeignKey(Recruitment, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    resume = models.FileField(upload_to='resumes/')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='APPLIED')
    applied_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.position.title}"


class Training(models.Model):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    trainer = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='trainer_sessions')
    participants = models.ManyToManyField(Employee, related_name='participated_sessions')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')
    materials = models.FileField(upload_to='training_materials/', blank=True)

    def __str__(self):
        return self.title


class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period_start = models.DateField()
    period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.period_start} to {self.period_end}"

    def calculate_net_salary(self):
        overtime_pay = self.overtime_hours * self.overtime_rate
        total = self.basic_salary + overtime_pay + self.bonuses - self.deductions
        self.net_salary = total
        return total


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    check_in = models.TimeField()
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('PRESENT', 'Present'),
        ('LATE', 'Late'),
        ('HALF_DAY', 'Half Day'),
        ('ABSENT', 'Absent')
    ])
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['employee', 'date']

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.date}"