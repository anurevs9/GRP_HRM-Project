import random

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login

from .models import (
    Employee, Department, Role, Task, Leave, Performance,
    Recruitment, Candidate, Training, Payroll, Attendance, TaskAssignment, LeaveQuota
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email", "first_name", "last_name")


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, label="New Password (leave blank to keep current)")
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False, label="Confirm New Password")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']  # Exclude password from default fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add password fields dynamically
        self.fields['password'] = forms.CharField(widget=forms.PasswordInput, required=False, label="New Password (leave blank to keep current)")
        self.fields['confirm_password'] = forms.CharField(widget=forms.PasswordInput, required=False, label="Confirm New Password")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password or confirm_password:
            if not password:
                self.add_error('password', "Please enter a new password.")
            elif not confirm_password:
                self.add_error('confirm_password', "Please confirm the new password.")
            elif password != confirm_password:
                self.add_error('confirm_password', "Password and confirm password do not match.")
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:  # Only set password if a new one is provided and validated
            user.set_password(password)
        # If no new password is provided, the existing password is retained
        if commit:
            user.save()
        return user


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        exclude = ['user']  # Exclude user field (handled separately)
        widgets = {
            'date_joined': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'reporting_manager': forms.Select(attrs={'class': 'form-control'}),
        }
        error_messages = {
            'department': {'required': 'Please select a department'},
            'role': {'required': 'Please select a role'},
            'employee_id': {'required': 'Employee ID is required'},
            'phone': {'required': 'Phone number is required'},
            'address': {'required': 'Address is required'},
            'date_joined': {'required': 'Date joined is required'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reporting_manager'].queryset = Employee.objects.all()  # Populate with all employees

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        return phone

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        if Employee.objects.filter(employee_id=employee_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This Employee ID is already in use.")
        return employee_id


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['task_title', 'task_description', 'task_priority', 'start_date', 'end_date', 'task_type']
        widgets = {
            'task_title': forms.TextInput(attrs={'class': 'form-control'}),
            'task_description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'task_priority': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'task_type': forms.Select(attrs={'class': 'form-control'}),
        }

class TaskAssignmentForm(forms.ModelForm):
    class Meta:
        model = TaskAssignment
        fields = ['employee', 'status']  # Removed 'task' and 'assigned_by' from fields
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("TaskAssignmentForm __init__ called for user:", user.username if user else "None")  # Debug user
        print("Request user authenticated:", user.is_authenticated)  # Debug authentication

        if user and user.is_authenticated:
            try:
                logged_in_employee = user.employee
                print("Logged-in employee found:", logged_in_employee)  # Debug employee
                print("Logged-in employee role:", logged_in_employee.role.name if logged_in_employee.role else "None")  # Debug role
                if logged_in_employee.role.name == 'ADMIN':
                    print("User is ADMIN - setting all employees")
                    self.fields['employee'].queryset = Employee.objects.all()
                    print("Employee queryset count for ADMIN:", Employee.objects.all().count())  # Debug count
                elif logged_in_employee.role.name in ['MANAGER', 'TEAM_LEADER']:
                    reporting_employees = Employee.objects.filter(reporting_manager=logged_in_employee)
                    print("User is Manager/Team Leader - setting reporting employees")
                    print("Reporting employees queryset:", reporting_employees.query)  # Debug SQL query
                    print("Reporting employees count:", reporting_employees.count())  # Debug count
                    self.fields['employee'].queryset = reporting_employees
                else:
                    print("User is EMPLOYEE or other role - setting empty queryset")
                    self.fields['employee'].queryset = Employee.objects.none()
            except Employee.DoesNotExist:
                print("Employee.DoesNotExist for user:", user.username)  # Debug
                self.fields['employee'].queryset = Employee.objects.none()
        else:
            print("User not authenticated or None - setting empty queryset")
            self.fields['employee'].queryset = Employee.objects.none()

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']  # Removed 'status' from fields
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Department.objects.filter(name=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A department with this name already exists.")
        return name

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Employee
        fields = ['phone', 'address', 'profile_picture', 'first_name', 'last_name', 'email', 'department', 'role', 'employee_id', 'date_joined']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'date_joined': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),

        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        employee = super().save(commit=False)
        # employee.user = self.initial.get('user')
        #
        # user = employee.user  # Get user from employee
        #
        # user.first_name = self.cleaned_data['first_name']
        # user.last_name = self.cleaned_data['last_name']
        # user.email = self.cleaned_data['email']

        if commit:
            # user.save()
            employee.save()
        return employee

class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['name', 'description','status']
        widgets = {
            'name': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }



class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = Performance
        fields = ['review_title', 'review_date', 'review_period', 'rating', 'feedback']
        widgets = {
            'review_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter review title'
            }),
            'review_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'dd/mm/yyyy'
            }),
            'review_period': forms.Select(attrs={
                'class': 'form-control'
            }),
            'rating': forms.Select(attrs={
                'class': 'form-control'
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter review comment (max 300 characters)...'
            }),
        }

    def clean_feedback(self):
        feedback = self.cleaned_data.get('feedback')
        if len(feedback) > 300:
            raise forms.ValidationError("Feedback cannot exceed 300 characters.")
        return feedback


class RecruitmentForm(forms.ModelForm):
    class Meta:
        model = Recruitment
        fields = ['title', 'department', 'description', 'requirements', 'positions', 'deadline', 'status'] #Added status
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'positions': forms.NumberInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['position', 'name', 'email', 'phone', 'resume', 'stage', 'notes']
        widgets = {
            'position': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'resume': forms.FileInput(attrs={'class': 'form-control'}),
            'stage': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class TrainingForm(forms.ModelForm):
    class Meta:
        model = Training
        fields = ['title', 'description', 'trainer', 'participants', 'start_date', 'end_date', 'status', 'materials']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'trainer': forms.Select(attrs={'class': 'form-control'}),
            'participants': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trainer'].queryset = Employee.objects.all()  # Set queryset for trainer field
        self.fields['participants'].queryset = Employee.objects.all()  # Set queryset for participants field

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be earlier than start date.")
        return cleaned_data


class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['employee', 'period_start', 'period_end', 'basic_salary',
                  'overtime_hours', 'overtime_rate', 'deductions', 'bonuses', 'payment_date']
        widgets = {
            'period_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'period_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'overtime_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bonuses': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'employee': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        payment_date = cleaned_data.get('payment_date')

        if period_start and period_end and period_start > period_end:
            raise forms.ValidationError("Period end date must be after start date.")

        if period_end and payment_date and payment_date < period_end:
            raise forms.ValidationError("Payment date must be after period end date.")

        return cleaned_data


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'check_in', 'check_out', 'status', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be earlier than start date.")
        return cleaned_data

class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['employee', 'leave_type', 'reason', 'start_date', 'end_date', 'status', 'approved_by']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'approved_by': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        status = cleaned_data.get('status')
        approved_by = cleaned_data.get('approved_by')

        # Validate date range
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be earlier than start date.")

        # Validate approved_by when status is APPROVED
        if status == 'APPROVED' and not approved_by:
            raise forms.ValidationError("Approved by is required when status is set to 'Approved'.")
        if approved_by and status != 'APPROVED':
            raise forms.ValidationError("Approved by can only be set when status is 'Approved'.")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit approved_by to employees with MANAGER, ADMIN, or HR roles
        self.fields['approved_by'].queryset = Employee.objects.filter(
            role__name__in=['ADMIN', 'MANAGER', 'HR']
        ).distinct()

class LeaveQuotaForm(forms.ModelForm):
    sl_quota = forms.IntegerField(
        label='Enter SL Quota',
        required=False,
        min_value=0,
        help_text='Leave blank to keep existing quota.'
    )
    pl_quota = forms.IntegerField(
        label='Enter PL Quota',
        required=False,
        min_value=0,
        help_text='Leave blank to keep existing quota.'
    )
    cl_quota = forms.IntegerField(
        label='Enter CL Quota',
        required=False,
        min_value=0,
        help_text='Leave blank to keep existing quota.'
    )

    class Meta:
        model = LeaveQuota
        fields = ['employee']

    def __init__(self, *args, **kwargs):
        self.is_edit = kwargs.pop('is_edit', False)
        self.employee_instance = kwargs.pop('employee_instance', None)  # Pass the employee instance for edit
        super().__init__(*args, **kwargs)
        if self.is_edit:
            self.fields['employee'].disabled = True
            # Pre-populate employee field with initial value
            if self.employee_instance:
                self.fields['employee'].initial = self.employee_instance
                self.instance.employee = self.employee_instance  # Set the instance.employee

    def clean_employee(self):
        # Skip validation for the employee field if it's disabled (in edit mode)
        if self.is_edit and self.employee_instance:
            return self.employee_instance
        return self.cleaned_data['employee']

    def clean(self):
        cleaned_data = super().clean()
        for field in ['sl_quota', 'pl_quota', 'cl_quota']:
            if field in cleaned_data and cleaned_data[field] is not None and cleaned_data[field] < 0:
                raise forms.ValidationError(f"{field.replace('_', ' ').title()} cannot be negative.")
        return cleaned_data

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        employee = instance.employee
        for leave_type, quota_field in [('SL', 'sl_quota'), ('PL', 'pl_quota'), ('CL', 'cl_quota')]:
            quota_value = self.cleaned_data.get(quota_field)
            if quota_value is not None:
                LeaveQuota.objects.update_or_create(
                    employee=employee,
                    leave_type=leave_type,
                    defaults={
                        'total_quota': quota_value,
                        'used_quota': 0,
                        'remain_quota': quota_value
                    }
                )
        return instance

class LeaveQuotaStatusForm(forms.ModelForm):
    class Meta:
        model = LeaveQuota
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Restrict to PENDING quotas for approval/rejection
        if 'instance' in kwargs:
            self.fields['status'].queryset = LeaveQuota.objects.filter(status='PENDING')

class LeaveApprovalForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['employee', 'leave_type', 'reason', 'start_date', 'end_date', 'status', 'approved_by']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            'leave_type': forms.Select(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'disabled': 'disabled'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'disabled': 'disabled'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'disabled': 'disabled'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'approved_by': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['employee'].queryset = Employee.objects.filter(id=self.instance.employee_id)
            self.fields['approved_by'].queryset = Employee.objects.filter(role__name__in=['ADMIN', 'MANAGER'])
            self.fields['status'].choices = [('', '---------'), ('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')]
            # Mark disabled fields as not required for updates
            for field_name in ['employee', 'leave_type', 'reason', 'start_date', 'end_date']:
                self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        # Ensure disabled fields retain their original values
        if self.instance.pk:
            for field_name in ['employee', 'leave_type', 'reason', 'start_date', 'end_date']:
                if field_name not in cleaned_data or not cleaned_data[field_name]:
                    cleaned_data[field_name] = getattr(self.instance, field_name)
        return cleaned_data

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Enter your username or email',
            'class': 'form-control'
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Enter your password',
            'class': 'form-control'
        })

    def clean(self):
        # Don’t call super().clean() to avoid default authentication
        username_or_email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not username_or_email:
            raise forms.ValidationError("Username or email is required.")
        if not password:
            raise forms.ValidationError("Password is required.")

        if '@' in username_or_email:
            try:
                user = User.objects.get(email=username_or_email.lower())
                username = user.username
            except User.DoesNotExist:
                raise forms.ValidationError(
                    "No account found with this email. Please check your input or sign up."
                )
        else:
            username = username_or_email

        user = authenticate(request=self.request, username=username, password=password)
        if user is None:
            raise forms.ValidationError(
                "Invalid username/email or password. Please check your credentials and try again."
            )
        if not user.is_active:
            raise forms.ValidationError(
                "This account is inactive. Please contact support."
            )
        self.cleaned_data['user'] = user
        return self.cleaned_data

    def save(self, request):
        user = self.cleaned_data.get('user')
        if user is not None:
            login(request, user)
            return user
        return None


class SignupForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        help_text="Required. Enter your first name (max 30 characters).",
        error_messages={
            'required': 'First name is required.',
            'max_length': 'First name cannot exceed 30 characters.'
        }
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        help_text="Required. Enter your last name (max 30 characters).",
        error_messages={
            'required': 'Last name is required.',
            'max_length': 'Last name cannot exceed 30 characters.'
        }
    )
    email = forms.EmailField(
        required=True,
        help_text="Required. Enter a valid email address.",
        error_messages={
            'required': 'Email is required.',
            'invalid': 'Please enter a valid email address.'
        }
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Enter your username',
            'class': 'form-control'
        })
        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'Enter your first name',
            'class': 'form-control'
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'Enter your last name',
            'class': 'form-control'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Enter your email',
            'class': 'form-control'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Enter your password',
            'class': 'form-control'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirm your password',
            'class': 'form-control'
        })

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 4:
            raise ValidationError("Username must be at least 4 characters long.")
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken. Please choose a different one.")
        if not username.isalnum():
            raise ValidationError("Username must contain only letters and numbers.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered. Please use a different email.")
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not any(char.isdigit() for char in password1):
            raise ValidationError("Password must contain at least one number.")
        if not any(char.isupper() for char in password1):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not any(char in "!@#$%^&*" for char in password1):
            raise ValidationError("Password must contain at least one special character (!@#$%^&*).")
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label="Registered Email", max_length=100)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("No user is registered with this email address.")
        return email

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(label="One-Time Password", max_length=6, min_length=6, widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit OTP'}))

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(label="New Password", widget=forms.PasswordInput, min_length=8)
    confirm_password = forms.CharField(label="Confirm New Password", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

# Helper function to generate and send OTP
def generate_and_send_otp(email):
    otp = str(random.randint(100000, 999999))
    subject = 'Password Reset OTP'
    message = f'Your OTP for password reset is: {otp}\nThis OTP is valid for 10 minutes.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
    return otp