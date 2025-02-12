import json
import logging
from datetime import datetime

import razorpay
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q, Avg
from django.db.models.functions import ExtractMonth
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import *  # Import all models from the current app (core)
from .forms import *  # Import all forms from the current app (core)
from django.utils import timezone


logger = logging.getLogger(__name__)

# Custom Decorator to handle Employee.DoesNotExist (BEST PRACTICE)
def employee_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login_register')  # Use namespaced URL
        if request.resolver_match.url_name == 'profile_setup':
            return view_func(request, *args, **kwargs)

        try:
            # Check if the user has an associated employee profile
            request.employee
        except Employee.DoesNotExist:
            messages.warning(request, "Please complete your profile setup.")
            return redirect('core:profile_setup')  # Redirect to profile setup
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@employee_required
def dashboard(request):
    # ... rest of your view ...
    try:
        # Access the employee profile within the try block
        employee = request.employee
        # Get all trainings where the employee is a trainer
        trainer_trainings = employee.trainer_sessions.all()
        # Get all trainings where the employee is a participant
        participant_trainings = employee.participated_sessions.all()
    except Employee.DoesNotExist:
        messages.warning(request, "Please complete your profile setup.")
        return redirect('core:profile_setup')  # Redirect to profile setup
    context = {
        'today': timezone.now(),
        'total_employees': Employee.objects.count(), # No change, model query
        'total_departments': Department.objects.count(), # No change, model query
        'open_positions': Recruitment.objects.filter(status='OPEN').count(), # No change
        'pending_leaves': Leave.objects.filter(status='PENDING').count(),# No change
        'recent_tasks': Task.objects.filter(assigned_to=request.employee).order_by('-due_date')[:5], # No change
        'upcoming_trainings': Training.objects.filter(
            start_date__gte=timezone.now()
        ).order_by('start_date')[:3], # No change
        'today_attendance': Attendance.objects.filter(
            employee=request.employee,
            date=timezone.now().date()
        ).first(), # No change
        'leave_balance': { # This should ideally come from a model or calculation
            'annual': 20,
            'sick': 10,
            'casual': 5
        },
        'announcements': [],  # Replace with your announcements logic
        'trainer_trainings': trainer_trainings,
        'participant_trainings': participant_trainings,
    }

    # Get performance data for charts (example, adapt to your needs)
    performance_data = Performance.objects.filter(
        employee=request.employee
    ).order_by('review_date')

    # Calculate monthly average ratings (example)
    monthly_ratings = Performance.objects.filter(
        employee=request.employee
    ).annotate(
        month=ExtractMonth('review_date')
    ).values('month').annotate(
        avg_rating=Avg('rating')
    ).order_by('month')

    # Prepare data for charts
    performance_labels = [p.review_date.strftime('%b %Y') for p in performance_data]
    performance_values = [p.rating for p in performance_data]

    monthly_labels = [f"Month {data['month']}" for data in monthly_ratings]
    monthly_values = [float(data['avg_rating']) for data in monthly_ratings]



    context.update({
        'performance_labels': performance_labels,
        'performance_values': performance_values,
        'monthly_labels': monthly_labels,
        'monthly_values': monthly_values,
    })
    return render(request, 'hrm/dashboard.html', context) # Assuming core/dashboard.html


@employee_required
def employee_list(request):
    # Check if user has permission to view employees.
    if request.employee.role.name not in 'settings.PAYROLL_ADMIN_ROLES': # Use settings
        messages.error(request, 'You do not have permission to view the employee list.')
        return redirect('core:dashboard')

    employees = Employee.objects.select_related('user', 'department', 'role').all()
    return render(request, 'hrm/employee_list.html', {'employees': employees}) # Assuming core/employee_list.html


@employee_required
def task_list(request):
    # Example of role-based access (adjust roles as needed)
    if request.employee.role.name in ['ADMIN', 'MANAGER', 'TEAM_LEADER']:
        tasks = Task.objects.all()  # Admin/Manager/Team Leader can see all tasks
    else:
        tasks = Task.objects.filter(assigned_to=request.employee)  # Employees see their own tasks
    return render(request, 'hrm/task_list.html', {'tasks': tasks}) # Assuming core/task_list.html


from django.shortcuts import render, redirect
from django.contrib import messages
# ... your other imports ...
from .forms import LeaveRequestForm # Assuming your form is in forms.py

# ... your decorator ...
@employee_required
def leave_request(request):
    print("Leave Request View Function Called!")  # Debug print at the start

    if request.method == 'POST':
        print("Request method is POST") # Debug print for POST request
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            print("Form is valid!") # Debug print if form is valid
            leave = form.save(commit=False)
            leave.employee = request.employee
            leave.status = 'PENDING'  # Set initial status
            leave.save()
            messages.success(request, 'Leave request submitted successfully.')
            return redirect('core:leave_request')  # Redirect - adjust app name if needed
        else:
            print("Form is NOT valid!") # Debug print if form is invalid
            print(form.errors)       # Print form errors to console
    else:
        print("Request method is GET") # Debug print for GET request
        form = LeaveRequestForm(initial={'employee': request.employee})

    leave_history = Leave.objects.filter(employee=request.employee).order_by('-applied_on')
    return render(request, 'hrm/leave_request.html', { # Assuming core/leave_request.html
        'form': form,
        'leave_history': leave_history
    })

@employee_required
def performance_review(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    previous_reviews = Performance.objects.filter(
        employee=employee
    ).order_by('-review_date')

    if request.method == 'POST':
        form = PerformanceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.employee = employee
            review.reviewed_by = request.user  # The logged-in user is the reviewer
            review.review_date = timezone.now()  # Use timezone.now() for consistency
            review.save()
            messages.success(request, 'Performance review submitted successfully.')
            return redirect('core:employee_list')  # Redirect to employee list
    else:
        form = PerformanceReviewForm()

    context = {
        'employee': employee,
        'form': form,
        'previous_reviews': previous_reviews
    }
    return render(request, 'hrm/performance_review.html', context) # Assuming core/performance_review.html



@employee_required
def add_employee(request):
    if request.employee.role.name not in 'settings.PAYROLL_ADMIN_ROLES':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        user_form = UserForm(request.POST)
        employee_form = EmployeeForm(request.POST, request.FILES)

        if user_form.is_valid() and employee_form.is_valid():
            user = user_form.save()
            employee = employee_form.save(commit=False)
            employee.user = user
            employee.save()
            messages.success(request, 'Employee added successfully.')
            return redirect('core:employee_list')
        else:
            messages.error(request, 'There was an error adding the employee. Please check the form.')
    else:
        user_form = UserForm()
        employee_form = EmployeeForm()

    context = {
        'user_form': user_form,
        'employee_form': employee_form,
    }
    return render(request, 'hrm/add_employee.html', context)  # Assuming core/add_employee.html

@login_required
def profile_setup(request):
    # Check if the user already has an employee profile
    if hasattr(request.user, 'employee'):
        return redirect('core:dashboard')  # Redirect if profile already exists

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.user = request.user
            employee.save()
            messages.success(request, 'Profile setup completed successfully!')
            return redirect('core:dashboard')
    else:
        form = ProfileForm(user=request.user)

    return render(request, 'hrm/profile_setup.html', {'form': form})


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('core:login_register')


@employee_required
def edit_employee(request, employee_id):
    if request.employee.role.name not in 'settings.PAYROLL_ADMIN_ROLES':
        messages.error(request, 'You do not have permission to edit employees.')
        return redirect('core:employee_list')

    employee = get_object_or_404(Employee, id=employee_id)
    user = employee.user

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        employee_form = EmployeeForm(request.POST, request.FILES, instance=employee)
        print("Initial user_form data:", user_form.initial)

        if user_form.is_valid() and employee_form.is_valid():
            user = user_form.save(commit=False)
            if user_form.cleaned_data['password']:
                user.set_password(user_form.cleaned_data['password'])  # Hash password
            user.save()
            employee = employee_form.save()
            messages.success(request, 'Employee updated successfully.')
            return redirect('core:employee_list')
    else:
        user_form = UserForm(instance=user)
        employee_form = EmployeeForm(instance=employee)

    context = {
        'user_form': user_form,
        'employee_form': employee_form,
        'employee': employee  # Pass the employee object to the template
    }
    return render(request, 'hrm/edit_employee.html', context) # Assuming core/edit_employee.html


@employee_required
def add_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user  # Assigned by the current user
            task.save()
            messages.success(request, 'Task created successfully.')
            return redirect('core:task_list')
    else:
        form = TaskForm()
    return render(request, 'hrm/add_task.html', {'form': form}) # Assuming core/add_task.html

@employee_required
def update_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully.')
            return redirect('core:task_list')
    else:
        form = TaskForm(instance=task)
    return render(request, 'hrm/update_task.html', {'form': form, 'task': task}) # Assuming core/update_task.html

def is_admin(user):
    try:
        return user.is_authenticated and user.employee.role.name == 'ADMIN'
    except Employee.DoesNotExist: # Handle case where employee doesn't exist
        return False



@user_passes_test(is_admin) # Use the test function
def department_list(request):
    search_query = request.GET.get('search', '')
    departments = Department.objects.all()

    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    context = {
        'departments': departments,
        'search_query': search_query
    }
    return render(request, 'hrm/department/list.html', context) # Assuming core/department/list.html


@user_passes_test(is_admin)
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department created successfully.')
            return redirect('core:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'hrm/department/create.html', {'form': form}) # Assuming core/department/create.html


@user_passes_test(is_admin)
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully.')
            return redirect('core:department_list')
    else:
        form = DepartmentForm(instance=department)

    return render(request, 'hrm/department/edit.html', {
        'form': form,
        'department': department
    })

@user_passes_test(is_admin)
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        # Check if there are employees in this department
        if Employee.objects.filter(department=department).exists():
            messages.error(request, 'Cannot delete department.  Employees are assigned to it.')
            return redirect('core:department_list')

        department.delete()  # Correctly DELETE the department
        messages.success(request, 'Department deleted successfully.')
        return redirect('core:department_list')

    return render(request, 'hrm/department/delete.html', {'department': department}) # Assuming core/department/delete.html


@employee_required
def edit_profile(request):
    employee = request.employee
    is_admin_or_manager = employee.role.name in ['ADMIN', 'MANAGER'] # Check if user is Admin or Manager

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            # Before saving, check again if it's admin/manager and if not, exclude dept/role
            if not is_admin_or_manager:
                form.cleaned_data.pop('department', None) # Remove department from cleaned_data if not admin/manager
                form.cleaned_data.pop('role', None)       # Remove role from cleaned_data if not admin/manager

            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('core:dashboard')
    else:
        form = ProfileForm(instance=employee, user=request.user)
        # If not admin/manager, disable department and role fields in the form
        if not is_admin_or_manager:
            form.fields['department'].widget.attrs['disabled'] = 'disabled'
            form.fields['role'].widget.attrs['disabled'] = 'disabled'

    context = {'form': form}
    return render(request, 'hrm/edit_profile.html', context)

@employee_required
def recruitment_list(request):
    recruitments = Recruitment.objects.all().order_by('-created_at')
    return render(request, 'hrm/recruitment/list.html', {'recruitments': recruitments}) # Assuming core/recruitment/list.html

def recruitment_detail(request, recruitment_id):
    recruitment = get_object_or_404(Recruitment, pk=recruitment_id)
    return render(request, 'hrm/recruitment/detail.html', {'recruitment': recruitment})

@employee_required
def recruitment_create(request):
    if request.method == 'POST':
        form = RecruitmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Position created successfully.')
            return redirect('core:recruitment_list')
    else:
        form = RecruitmentForm()
    return render(request, 'hrm/recruitment/create.html', {'form': form})

@employee_required
def candidate_list(request, recruitment_id):
    recruitment = get_object_or_404(Recruitment, id=recruitment_id)
    candidates = Candidate.objects.filter(position=recruitment).order_by('-applied_date')
    return render(request, 'hrm/recruitment/candidates.html', { # Assuming core/recruitment/candidates.html
        'recruitment': recruitment,
        'candidates': candidates
    })

@employee_required
def training_list(request):
    employee = request.employee
    # Get all trainings where the employee is a trainer
    trainer_trainings = employee.trainer_sessions.all()
    # Get all trainings where the employee is a participant
    participant_trainings = employee.participated_sessions.all()

    context = {
        'trainer_trainings': trainer_trainings,
        'participant_trainings': participant_trainings,
    }
    return render(request, 'hrm/training/list.html', context)

@employee_required
def training_create(request):
    print("training_create view called")  # Debugging print

    if request.method == 'POST':
        form = TrainingForm(request.POST, request.FILES)
        if form.is_valid():
            print("Form is valid")  # Debugging print
            training = form.save(commit=False)
            training.trainer = request.employee
            training.save()
            form.save_m2m()
            messages.success(request, 'Training session created successfully.')
            print("Training created and saved") # Debugging print
            return redirect('core:training_list')
        else:
            print("Form is NOT valid") # Debugging print
            print(form.errors)  # Print form errors to console
    else:
        form = TrainingForm()

    return render(request, 'hrm/training/create.html', {'form': form})

@employee_required
def attendance_mark(request):
    today = timezone.now().date()
    try:
        attendance = Attendance.objects.get(
            employee=request.employee,
            date=today
        )
    except Attendance.DoesNotExist:
        attendance = None

    if request.method == 'POST':
        if not attendance:
            attendance = Attendance.objects.create(
                employee=request.employee,
                date=today,
                check_in=timezone.now().time(),
                status='PRESENT'
            )
            messages.success(request, 'Attendance marked successfully.')
        else:
            attendance.check_out = timezone.now().time()
            attendance.save()
            messages.success(request, 'Check-out time recorded successfully.')
        return redirect('core:dashboard')

    return render(request, 'hrm/attendance/mark.html', {'attendance': attendance}) # Assuming core/attendance/mark.html

@employee_required
def attendance_report(request):
    if request.employee.role.name in ['ADMIN', 'MANAGER']:
        attendances = Attendance.objects.all().order_by('-date')
    else:
        attendances = Attendance.objects.filter(
            employee=request.employee
        ).order_by('-date')
    return render(request, 'hrm/attendance/report.html', {'attendances': attendances}) # Assuming core/attendance/report.html

@employee_required
def payroll_list(request):
    if request.employee.role.name in "settings.PAYROLL_ADMIN_ROLES":
        payrolls = Payroll.objects.all().order_by('-payment_date')
    else:
        payrolls = Payroll.objects.filter(
            employee=request.employee
        ).order_by('-payment_date')
    return render(request, 'hrm/payroll/list.html', {'payrolls': payrolls, 'razorpay_key_id': settings.RAZORPAY_KEY_ID}) # Assuming core/payroll/list.html

@employee_required
def payroll_detail(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    # Check if the user is staff or the owner of the payroll
    if not request.user.is_staff and payroll.employee.user != request.user:
        messages.error(request, 'You do not have permission to view this payroll.')
        return redirect('core:payroll_list')
    return render(request, 'hrm/payroll/detail.html', {'payroll': payroll,  'razorpay_key_id': settings.RAZORPAY_KEY_ID}) # Assuming core/payroll/detail.html

@employee_required
def process_payroll_payment(request, payroll_id):
    # ... (rest of your view code up to the try-except block) ...

    if not request.employee.role.name in "settings.PAYROLL_ADMIN_ROLES":
        print("Unauthorized access attempt")  # Log unauthorized attempts
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    # 2. Retrieve Payroll Object
    payroll = get_object_or_404(Payroll, pk=payroll_id)
    print(f"Payroll object retrieved: {payroll}")

    # 3. Double-Payment Check
    if payroll.payment_status:
        print("Payment already processed")
        return JsonResponse({'status': 'error', 'message': 'Payment already processed'}, status=400)

    # 4. Initialize Razorpay Client (using settings)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    print(f"Razorpay client initialized: {client}")

    # 5. Prepare Order Data
    amount_in_paise = int(payroll.net_salary * 100)  # ALWAYS work with the smallest unit
    data = {
        'amount': amount_in_paise,
        'currency': 'INR',  # Or your currency
        'receipt': f'payroll_{payroll.id}',  # Use a more descriptive receipt
        'payment_capture': 1,  # Auto-capture the payment
        'notes': {  # Add notes as needed
            "payroll_id": payroll_id,
            "employee_name": payroll.employee.user.get_full_name()
        }
    }
    print(f"Razorpay order data: {data}")

    try:
        order = client.order.create(data=data)
        payroll.razorpay_order_id = order['id']
        payroll.payment_status = True  # set the payment status.
        payroll.save()

        # --- EMAIL SENDING (CORRECTED) ---
        context = {
            'employee_name': payroll.employee.user.get_full_name() if payroll.employee.user.get_full_name() else "Employee",  # Handle potential None
            'period': f"{payroll.period_start.strftime('%Y-%m-%d')} to {payroll.period_end.strftime('%Y-%m-%d')}" if payroll.period_start and payroll.period_end else "N/A",
            'basic_salary': payroll.basic_salary if payroll.basic_salary is not None else 0,  # Handle None
            'overtime_pay': payroll.overtime_hours * payroll.overtime_rate if payroll.overtime_hours and payroll.overtime_rate else 0, # calculate
            'bonuses': payroll.bonuses if payroll.bonuses is not None else 0,
            'deductions': payroll.deductions if payroll.deductions is not None else 0,
            'net_salary': payroll.net_salary if payroll.net_salary is not None else 0,
            'payment_date': payroll.payment_date.strftime('%Y-%m-%d') if payroll.payment_date else "N/A",
        }


        html_message = render_to_string('hrm/email/payroll_processed.html', context)
        plain_message = (f"Dear {context['employee_name']},\n\n"
                         f"Your salary of ${context['net_salary']} for the period {context['period']} has been processed.\n"
                         f"Payment Date: {context['payment_date']}\n\n"
                         f"If you have any questions, please contact the HR department.")

        send_mail(
            subject='Salary Payment Processed',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[payroll.employee.user.email],
            html_message=html_message,
            fail_silently=False,
        )


        return JsonResponse({
            'status': 'success',
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'employee_name': payroll.employee.user.get_full_name(),  # Pass this to the client
            'employee_email': payroll.employee.user.email,  # Pass this to the client
        })

    except Exception as e:
        print(f"An error occurred: {e}")
        payroll.payment_status = False  # IMPORTANT: Reset status on failure
        payroll.save()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@employee_required
def create_payroll(request):
    if request.method == 'POST':
        form = PayrollForm(request.POST)
        if form.is_valid():
            payroll = form.save(commit=False)
            payroll.net_salary = payroll.calculate_net_salary()
            payroll.save()
            messages.success(request, 'Payroll created successfully.')
            return redirect('core:payroll_list')
    else:
        form = PayrollForm()

    return render(request, 'hrm/payroll/create.html', {'form': form})

@require_POST
@csrf_exempt
def razorpay_webhook(request):
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    payload_body = request.body.decode('utf-8')

    if not webhook_signature:
        return HttpResponse("Signature missing", status=400)

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.utility.verify_webhook_signature(payload_body, webhook_signature, webhook_secret)

        payload = json.loads(payload_body)

        if payload['event'] == 'payment.captured':
            razorpay_payment_id = payload['payload']['payment']['entity']['id']
            razorpay_order_id = payload['payload']['payment']['entity']['order_id']

            try:
                payroll = Payroll.objects.get(razorpay_order_id=razorpay_order_id)

                if not payroll.payment_status:
                    payment = client.payment.fetch(razorpay_payment_id)
                    if payment["status"] == "captured":
                        payroll.payment_status = True
                        payroll.razorpay_payment_id = razorpay_payment_id
                        payroll.save()
                        return HttpResponse("Payment processed", status=200)
                    else:
                        return HttpResponse("Payment not captured", status=400)
                else:
                    return HttpResponse("Payment already processed", status=200)

            except Payroll.DoesNotExist:
                return HttpResponse("Payroll record not found", status=404)

        return HttpResponse("OK", status=200)

    except razorpay.errors.SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)
    except Exception as e:
        return HttpResponse(str(e), status=500)

@employee_required
def get_payment_status(request, payroll_id):
    payroll = get_object_or_404(Payroll, pk=payroll_id)
    return JsonResponse({'payment_status': payroll.payment_status})

@employee_required
def employee_profile(request):
    employee = request.employee
    # Get all trainings where the employee is a trainer
    trainer_trainings = employee.trainer_sessions.all()
    # Get all trainings where the employee is a participant
    participant_trainings = employee.participated_sessions.all()

    context = {
        'employee': employee,
        'trainer_trainings': trainer_trainings,
        'participant_trainings': participant_trainings,
    }
    return render(request, 'hrm/employee_profile.html', context)

@user_passes_test(is_admin)
def department_deactivate(request, pk):
    department = get_object_or_404(Department, pk=pk)

    if request.method == 'POST':
        # Check if there are employees in this department
        employees_in_department = Employee.objects.filter(department=department)
        if employees_in_department.exists():
            messages.error(request, f'Cannot deactivate {department.name}. {employees_in_department.count()} employees are currently assigned to this department. Reassign employees first.')
        else:
            department.status = False  # Set status to False for deactivation (soft delete)
            department.save()
            messages.success(request, f'{department.name} deactivated successfully.')

        return redirect('core:department_list') # Redirect back to department list

    return render(request, 'hrm/department/deactivate_confirm.html', {'department': department}) # Optional confirmation page (see next step - can be removed if you don't want confirmation)




def login_register_view(request):
    login_form = LoginForm(prefix='login')
    signup_form = SignupForm(prefix='signup')
    context = {'login_form': login_form, 'signup_form': signup_form}

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            login_form = LoginForm(request, data=request.POST, prefix='login')
            if login_form.is_valid():
                user = login_form.get_user()
                if user is not None:
                    login(request, user)
                    messages.success(request, 'Login successful!')
                    return redirect('core:dashboard')
                else:
                    messages.error(request, 'Login failed. Please check your credentials.')
            else:
                messages.error(request, 'Login failed. Please correct the errors below.')
                context['login_form'] = login_form  # Re-populate the form with errors

        elif 'signup_submit' in request.POST:
            signup_form = SignupForm(request.POST, prefix='signup')
            if signup_form.is_valid():
                user = signup_form.save()
                messages.success(request, 'Signup successful! Please login.')
                signup_form = SignupForm(prefix='signup') # Clear form after successful signup.
            else:
                messages.error(request, 'Signup failed. Please correct the errors below.')
                context['signup_form'] = signup_form # Re-populate

    return render(request, 'login_register.html', context)

def apply_for_job(request, recruitment_id):
    recruitment = get_object_or_404(Recruitment, id=recruitment_id)

    if request.method == 'POST':
        form = CandidateForm(request.POST, request.FILES)  # Include request.FILES for resume
        if form.is_valid():
            candidate = form.save(commit=False)  # Don't save immediately
            candidate.position = recruitment  # Set the position
            candidate.save()  # Now save
            messages.success(request, 'Application submitted successfully!')
            return redirect('core:recruitment_detail', recruitment_id=recruitment.id)  # Redirect to the detail page (see step 2)
    else:
        form = CandidateForm(initial={'position': recruitment}) # Pre-fill position

    return render(request, 'hrm/recruitment/apply.html', {'form': form, 'recruitment': recruitment})

@login_required
def reports_view(request):
    context = {
        'report_types': [
            {'name': 'Employee Report', 'url': reverse('core:employee_report')},
            {'name': 'Task Report', 'url': reverse('core:task_report')},
            {'name': 'Performance Report', 'url': reverse('core:performance_report')},
            {'name': 'Payroll Report', 'url': reverse('core:payroll_report')},
            {'name': 'Recruitment Report', 'url': reverse('core:recruitment_report')},
            {'name': 'Training Report', 'url': reverse('core:training_report')},
        ]
    }
    return render(request, 'hrm/reports/reports.html', context)

@login_required
def employee_report(request):
    employees = Employee.objects.select_related('user', 'department', 'role').all()
    context = {
        'employees': employees,
        'report_title': 'Employee Report',
    }
    return render(request, 'hrm/reports/employee_report.html', context)

@login_required
def task_report(request):
    tasks = Task.objects.select_related('assigned_to', 'assigned_by').all()
    context = {
        'tasks': tasks,
        'report_title': 'Task Report',
    }
    return render(request, 'hrm/reports/task_report.html', context)

@login_required
def performance_report(request):
    performances = Performance.objects.select_related('employee', 'reviewed_by').all()
    context = {
        'performances': performances,
        'report_title': 'Performance Report',
    }
    return render(request, 'hrm/reports/performance_report.html', context)

@login_required
def payroll_report(request):
    if request.employee.role.name in "settings.PAYROLL_ADMIN_ROLES":
        payrolls = Payroll.objects.all().order_by('-payment_date')
    else:
        payrolls = Payroll.objects.filter(employee=request.employee).order_by('-payment_date')

    context = {
        'payrolls': payrolls,
        'report_title': 'Payroll Report',
    }
    return render(request, 'hrm/reports/payroll_report.html', context)

@login_required
def recruitment_report(request):
    recruitments = Recruitment.objects.all().order_by('-created_at')
    candidates = Candidate.objects.select_related('position').all()

    context = {
        'recruitments': recruitments,
        'candidates': candidates,
        'report_title': 'Recruitment Report',
    }
    return render(request, 'hrm/reports/recruitment_report.html', context)

@login_required
def training_report(request):
    employee = request.employee
    trainer_trainings = employee.trainer_sessions.all()
    participant_trainings = employee.participated_sessions.all()

    context = {
        'trainer_trainings': trainer_trainings,
        'participant_trainings': participant_trainings,
        'report_title': 'Training Report',
    }
    return render(request, 'hrm/reports/training_report.html', context)