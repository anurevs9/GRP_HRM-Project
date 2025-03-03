from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import (
    Employee, Department, Role, Task, Leave, Performance,
    Recruitment, Candidate, Training, Payroll, Attendance
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email", "first_name", "last_name")

# class LoginForm(AuthenticationForm):  # Use AuthenticationForm for login
#     """Base class for authenticating users."""
#     pass


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Password and confirm password do not match.")
        return cleaned_data
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Username already exists.')
        return username
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password") # Get password
        if password:
             user.set_password(password)  # Hash the password, only if it is given
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
        fields = ['title', 'description', 'assigned_to', 'due_date', 'status']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4})
        }


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
        fields = ['review_period', 'rating', 'feedback', 'goals']
        widgets = {
            'review_period': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Q1 2025'
            }),
            'rating': forms.Select(attrs={
                'class': 'form-control'
            }),
            'feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide detailed feedback...'
            }),
            'goals': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Set goals for next period...'
            })
        }


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
        # REMOVE 'employee' and 'status' from the fields list:
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            # REMOVE the 'employee' widget as it's no longer a form field:
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


from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django import forms

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Enter your email', 'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'placeholder': 'Enter your password', 'class': 'form-control'})

    def save(self, request):
        """Authenticate and log in the user."""
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return user
        return None


class SignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, help_text="Required. 30 characters or fewer.")
    last_name = forms.CharField(max_length=30, required=True, help_text="Required. 30 characters or fewer.")
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Enter your username', 'class': 'form-control'})
        self.fields['first_name'].widget.attrs.update({'placeholder': 'Enter your first name', 'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Enter your last name', 'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Enter your email', 'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Enter your password', 'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirm your password', 'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user