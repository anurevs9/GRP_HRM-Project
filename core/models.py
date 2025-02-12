from django.db import models
from django.contrib.auth.models import User

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

class Role(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('TEAM_LEADER', 'Team Leader'),
        ('EMPLOYEE', 'Employee'),
    )
    name = models.CharField(max_length=20, choices=ROLE_CHOICES)
    description = models.TextField()

    def __str__(self):
        return self.name

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)
    employee_id = models.CharField(max_length=10, unique=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    date_joined = models.DateField()
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name()

class Task(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_to = models.ForeignKey(Employee, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Leave(models.Model):
    LEAVE_TYPES = (
        ('SICK', 'Sick Leave'),
        ('CASUAL', 'Casual Leave'),
        ('EMERGENCY', 'Emergency Leave'),
        ('VACATION', 'Vacation'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    applied_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"

class Performance(models.Model):
    RATING_CHOICES = (
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    review_period = models.CharField(max_length=50)  # e.g., "Q1 2024"
    rating = models.IntegerField(choices=RATING_CHOICES)
    feedback = models.TextField()
    goals = models.TextField()
    reviewed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    review_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.review_period}"


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