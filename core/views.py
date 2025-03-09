import json
import logging
from datetime import datetime, time

import razorpay
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.paginator import PageNotAnInteger, Paginator, EmptyPage
from django.db.models import Q, Avg, Max, Sum
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
    try:
        employee = request.employee
        trainer_trainings = employee.trainer_sessions.all()
        participant_trainings = employee.participated_sessions.all()
    except Employee.DoesNotExist:
        messages.warning(request, "Please complete your profile setup.")
        return redirect('core:profile_setup')

    # Fetch employees for the filter dropdown
    if request.employee.role.name == 'ADMIN':
        all_employees = Employee.objects.all()
        assignments_queryset = TaskAssignment.objects.select_related('employee__user', 'task').all()
        performances = Performance.objects.all()  # For Admin: all performance reviews
    elif request.employee.role.name in ['MANAGER', 'TEAM_LEADER']:
        all_employees = Employee.objects.filter(reporting_manager=request.employee)
        assignments_queryset = TaskAssignment.objects.select_related('employee__user', 'task').filter(
            employee__in=all_employees)
        performances = Performance.objects.filter(
            employee__in=all_employees)  # For Manager/TL: reviews of reporting employees
    else:  # EMPLOYEE
        all_employees = Employee.objects.filter(id=request.employee.id)
        assignments_queryset = TaskAssignment.objects.select_related('employee__user', 'task').filter(
            employee=request.employee)
        performances = Performance.objects.filter(employee=request.employee)  # For Employee: their own reviews

    # Apply task filters (same as before)
    employee_filter = request.GET.get('employee')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if employee_filter:
        assignments_queryset = assignments_queryset.filter(employee__id=employee_filter)
    if status_filter:
        assignments_queryset = assignments_queryset.filter(status=status_filter)
    if date_from and date_to:
        try:
            date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            date_from_start = timezone.make_aware(datetime.combine(date_from_dt, time.min))
            date_to_end = timezone.make_aware(datetime.combine(date_to_dt, time.max))
            assignments_queryset = assignments_queryset.filter(assigned_date__range=[date_from_start, date_to_end])
        except ValueError as e:
            messages.error(request,
                           f"Invalid date format for Date From or Date To. Please use YYYY-MM-DD. Error: {str(e)}")
    elif date_from or date_to:
        messages.warning(request, "Please provide both Date From and Date To for date filtering.")

    assignments_queryset = assignments_queryset.order_by('assigned_date')

    # Pagination for tasks
    paginator = Paginator(assignments_queryset, 5)
    page = request.GET.get('page')
    try:
        assignments = paginator.page(page)
    except PageNotAnInteger:
        assignments = paginator.page(1)
    except EmptyPage:
        assignments = paginator.page(paginator.num_pages)

    status_choices = ['PENDING', 'IN_PROGRESS', 'COMPLETED']

    # Performance statistics
    performance_stats = {
        'total_reviews': performances.count(),
        'monthly': performances.filter(review_period='MONTHLY').count(),
        'quarterly': performances.filter(review_period='QUARTERLY').count(),
        'annual': performances.filter(review_period='ANNUAL').count(),
        'rating_1_5': performances.filter(rating__lte=5).count(),
        'rating_6_8': performances.filter(rating__gte=6, rating__lte=8).count(),
        'rating_9_10': performances.filter(rating__gte=9).count(),
    }

    # Fetch leave balances for the logged-in employee
    leave_quotas = LeaveQuota.objects.filter(employee=request.employee)

    # Structure leave balance data for the template
    leave_balance = {
        'SL': {'total': 0, 'remaining': 0, 'used': 0},
        'PL': {'total': 0, 'remaining': 0, 'used': 0},
        'CL': {'total': 0, 'remaining': 0, 'used': 0},
    }

    for quota in leave_quotas:
        leave_type = quota.leave_type
        if leave_type in leave_balance:
            # Adjust based on your LeaveQuota model fields
            # Assuming fields are total_quota, remain_quota, used_quota
            total = quota.total_quota if hasattr(quota, 'total_quota') else (
                quota.quota if hasattr(quota, 'quota') else 0)
            remaining = quota.remain_quota if hasattr(quota, 'remain_quota') else 0
            used = quota.used_quota if hasattr(quota, 'used_quota') else (total - remaining)
            leave_balance[leave_type] = {
                'total': total,
                'remaining': remaining,
                'used': used,
            }

    context = {
        'today': timezone.now(),
        'total_employees': Employee.objects.count(),
        'total_departments': Department.objects.count(),
        'open_positions': Recruitment.objects.filter(status='OPEN').count(),
        'pending_leaves': Leave.objects.filter(status='PENDING').count(),
        'upcoming_trainings': Training.objects.filter(start_date__gte=timezone.now()).order_by('start_date')[:3],
        'today_attendance': Attendance.objects.filter(employee=request.employee, date=timezone.now().date()).first(),
        'leave_balance': leave_balance,  # Updated leave balance data
        'announcements': [],
        'trainer_trainings': trainer_trainings,
        'participant_trainings': participant_trainings,
        'assignments': assignments,
        'all_employees': all_employees,
        'status_choices': status_choices,
        'employee_filter': employee_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'performance_stats': performance_stats,  # Add performance stats to context
    }

    # Performance data for charts
    performance_data = Performance.objects.filter(employee=request.employee).order_by('review_date')
    monthly_ratings = Performance.objects.filter(employee=request.employee).annotate(
        month=ExtractMonth('review_date')
    ).values('month').annotate(avg_rating=Avg('rating')).order_by('month')

    context.update({
        'performance_labels': [p.review_date.strftime('%b %Y') for p in performance_data],
        'performance_values': [p.rating for p in performance_data],
        'monthly_labels': [f"Month {data['month']}" for data in monthly_ratings],
        'monthly_values': [float(data['avg_rating']) for data in monthly_ratings],
    })

    return render(request, 'hrm/dashboard.html', context)

@employee_required
def employee_list(request):
    # Check if user has permission to view employees.
    if request.employee.role.name not in 'settings.PAYROLL_ADMIN_ROLES': # Use settings
        messages.error(request, 'You do not have permission to view the employee list.')
        return redirect('core:dashboard')

    employees = Employee.objects.select_related('user', 'department', 'role').all()
    return render(request, 'hrm/employee_list.html', {'employees': employees}) # Assuming core/employee_list.html


@login_required
def leave_request(request):
    employee = request.user.employee
    # Redirect both ADMIN and MANAGER to admin_leave_dashboard
    if employee.role.name in ['ADMIN', 'MANAGER']:
        return redirect('core:admin_leave_dashboard')

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.status = 'PENDING'
            quota = LeaveQuota.objects.get_or_create(employee=employee, leave_type=leave.leave_type)[0]
            if quota.remain_quota < leave.total_days:
                messages.error(request,
                               f"Insufficient {leave.get_leave_type_display} balance. Remaining: {quota.remain_quota} days.")
            else:
                leave.save()
                quota.used_quota += leave.total_days
                quota.remain_quota -= leave.total_days
                quota.save()
                messages.success(request, 'Leave request submitted successfully.')
            return redirect('core:leave_request')
        else:
            print(form.errors)
    else:
        form = LeaveRequestForm()

    leave_history = Leave.objects.filter(employee=employee).order_by('-created_at')
    paginator = Paginator(leave_history, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    leave_balances = {
        'PL': LeaveQuota.objects.get_or_create(employee=employee, leave_type='PL')[0].remain_quota,
        'CL': LeaveQuota.objects.get_or_create(employee=employee, leave_type='CL')[0].remain_quota,
        'SL': LeaveQuota.objects.get_or_create(employee=employee, leave_type='SL')[0].remain_quota,
    }
    return render(request, 'hrm/employee_leave_dashboard.html', {
        'form': form,
        'leave_history': page_obj,
        'leave_balances': leave_balances,
        'user_role': employee.role.name  # Pass the user's role to the template
    })


@login_required
def apply_leave(request):
    employee = request.user.employee
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.employee = employee
            leave.status = 'PENDING'
            quota = LeaveQuota.objects.get_or_create(employee=employee, leave_type=leave.leave_type)[0]
            if quota.remain_quota < leave.total_days:
                messages.error(request,
                               f"Insufficient {leave.get_leave_type_display} balance. Remaining: {quota.remain_quota} days.")
            else:
                leave.save()
                quota.used_quota += leave.total_days
                quota.remain_quota -= leave.total_days
                quota.save()
                messages.success(request, 'Leave request submitted successfully.')
                return redirect('core:leave_request')
        else:
            print(form.errors)  # Debug form errors
    else:
        form = LeaveRequestForm()

    leave_balances = {
        'PL': LeaveQuota.objects.get_or_create(employee=employee, leave_type='PL')[0].remain_quota,
        'CL': LeaveQuota.objects.get_or_create(employee=employee, leave_type='CL')[0].remain_quota,
        'SL': LeaveQuota.objects.get_or_create(employee=employee, leave_type='SL')[0].remain_quota,
    }
    return render(request, 'hrm/apply_leave.html', {
        'form': form,
        'leave_balances': leave_balances,
    })


@login_required
def admin_leave_dashboard(request):
    if request.user.employee.role.name not in ['ADMIN', 'MANAGER']:
        return redirect('core:leave_request')

    admin_leaves = Leave.objects.filter(employee=request.user.employee).order_by('-created_at')
    reportees_leaves = Leave.objects.exclude(employee=request.user.employee).filter(status='PENDING').order_by(
        '-created_at')

    paginator_admin = Paginator(admin_leaves, 5)
    paginator_reportees = Paginator(reportees_leaves, 5)
    page_number_admin = request.GET.get('page_admin')
    page_number_reportees = request.GET.get('page_reportees')
    admin_leave_history = paginator_admin.get_page(page_number_admin)
    reportees_leave_history = paginator_reportees.get_page(page_number_reportees)

    total_pl = \
    LeaveQuota.objects.filter(leave_type='PL', employee=request.user.employee).aggregate(total=Sum('remain_quota'))[
        'total'] or 0
    total_cl = \
    LeaveQuota.objects.filter(leave_type='CL', employee=request.user.employee).aggregate(total=Sum('remain_quota'))[
        'total'] or 0
    total_sl = \
    LeaveQuota.objects.filter(leave_type='SL', employee=request.user.employee).aggregate(total=Sum('remain_quota'))[
        'total'] or 0

    return render(request, 'hrm/admin_leave_dashboard.html', {
        'admin_leave_history': admin_leave_history,
        'reportees_leave_history': reportees_leave_history,
        'total_pl': total_pl,
        'total_cl': total_cl,
        'total_sl': total_sl,
        'user_role': request.user.employee.role.name  # Pass the role to the template
    })

# core/views.py
@employee_required
def edit_leave(request, leave_id):
    leave = get_object_or_404(Leave, leaveid=leave_id)
    if leave.employee.user != request.user or leave.status != 'PENDING':
        messages.error(request, 'You cannot edit this leave request.')
        return redirect('core:leave_request')

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, instance=leave)
        if form.is_valid():
            leave = form.save(commit=False)
            delta = leave.end_date - leave.start_date
            leave.total_days = delta.days + 1
            leave.save()
            messages.success(request, 'Leave request updated successfully.')
            return redirect('core:dashboard')
    else:
        form = LeaveRequestForm(instance=leave)
    return render(request, 'hrm/edit_leave.html', {'form': form})


@login_required
def delete_leave(request, leave_id):
    leave = get_object_or_404(Leave, leaveid=leave_id)
    logger.debug(f"Attempting to delete leave with ID: {leave_id}, Status: {leave.status}")

    if request.method == 'POST':
        logger.debug("POST request received, proceeding with deletion")
        # Restore quota if the leave was approved
        if leave.status == 'APPROVED':
            quota = LeaveQuota.objects.get_or_create(employee=leave.employee, leave_type=leave.leave_type)[0]
            quota.remain_quota += leave.total_days
            quota.used_quota -= leave.total_days
            quota.save()
            logger.debug(f"Quota updated for leave type {leave.leave_type}")
        leave.delete()
        logger.debug("Leave deleted successfully")
        messages.success(request, 'Leave request deleted successfully.')
        return redirect('core:admin_leave_dashboard')

    logger.debug("Rendering confirmation page")
    return render(request, 'hrm/comfirm_delete.html', {'leave': leave})


@login_required
def add_leave_quota(request):
    # Check if the user has permission to access this page
    if request.user.employee.role.name not in ['ADMIN', 'MANAGER']:
        messages.warning(request, 'You do not have permission to view this page.')
        return redirect('core:leave_request')

    if request.method == 'POST':
        form = LeaveQuotaForm(request.POST, is_edit=False)
        if form.is_valid():
            form.save()
            messages.success(request, 'Leave quotas updated successfully.')
            return redirect('core:add_leave_quota')
    else:
        form = LeaveQuotaForm(is_edit=False)

    # Fetch all employees and construct employee_quotas list
    employees = Employee.objects.all()
    employee_quotas = []
    for emp in employees:
        sl_quota = LeaveQuota.objects.filter(employee=emp, leave_type='SL').first()
        pl_quota = LeaveQuota.objects.filter(employee=emp, leave_type='PL').first()
        cl_quota = LeaveQuota.objects.filter(employee=emp, leave_type='CL').first()
        employee_quotas.append({
            'employee': emp,
            'sl_quota': sl_quota.remain_quota if sl_quota else 0,
            'pl_quota': pl_quota.remain_quota if pl_quota else 0,
            'cl_quota': cl_quota.remain_quota if cl_quota else 0,
            'quotaid': emp.id  # Note: Using emp.id as quotaid; adjust if this should be LeaveQuota's ID
        })

    # Add pagination
    paginator = Paginator(employee_quotas, 5)  # Show 5 quotas per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'hrm/add_leave_quote.html', {
        'form': form,
        'employee_quotas': page_obj,  # Pass the paginated Page object
    })


@login_required
def approve_reject_leave(request, leave_id):
    leave = get_object_or_404(Leave, leaveid=leave_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['APPROVED', 'REJECTED']:
            leave.status = status
            leave.save()
            if status == 'APPROVED':
                quota = LeaveQuota.objects.get_or_create(employee=leave.employee, leave_type=leave.leave_type)[0]
                quota.remain_quota -= leave.total_days
                quota.used_quota += leave.total_days
                quota.save()
            messages.success(request, f'Leave {status.lower()} successfully.')
            return redirect('core:admin_leave_dashboard')
    return render(request, 'hrm/approve_reject_leave.html', {'leave': leave})

@login_required
def update_admin_leave_status(request, leave_id):
    leave = get_object_or_404(Leave, leaveid=leave_id, employee=request.user.employee)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['APPROVED', 'REJECTED', 'CANCELLED']:  # Added CANCELLED as an option for admin
            leave.status = status
            leave.save()
            if status == 'APPROVED':
                quota = LeaveQuota.objects.get_or_create(employee=leave.employee, leave_type=leave.leave_type)[0]
                quota.remain_quota -= leave.total_days
                quota.used_quota += leave.total_days
                quota.save()
            elif status == 'CANCELLED':
                quota = LeaveQuota.objects.get_or_create(employee=leave.employee, leave_type=leave.leave_type)[0]
                quota.remain_quota += leave.total_days
                quota.used_quota -= leave.total_days
                quota.save()
            messages.success(request, f'Leave {status.lower()} successfully.')
            return redirect('core:admin_leave_dashboard')
    return render(request, 'hrm/approve_reject_leave.html', {'leave': leave})


@login_required
def edit_quota(request, quotaid):
    if request.user.employee.role.name not in ['ADMIN', 'MANAGER']:
        messages.warning(request, 'You do not have permission to view this page.')
        return redirect('core:leave_request')

    employee = get_object_or_404(Employee, id=quotaid)
    sl_quota = LeaveQuota.objects.filter(employee=employee, leave_type='SL').first()
    pl_quota = LeaveQuota.objects.filter(employee=employee, leave_type='PL').first()
    cl_quota = LeaveQuota.objects.filter(employee=employee, leave_type='CL').first()

    initial_data = {
        'employee': employee,
        'sl_quota': sl_quota.remain_quota if sl_quota else 0,
        'pl_quota': pl_quota.remain_quota if pl_quota else 0,
        'cl_quota': cl_quota.remain_quota if cl_quota else 0,
    }

    if request.method == 'POST':
        form = LeaveQuotaForm(request.POST, is_edit=True, employee_instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Leave quotas updated successfully.')
            return redirect('core:add_leave_quota')
    else:
        form = LeaveQuotaForm(initial=initial_data, is_edit=True, employee_instance=employee)
        return render(request, 'hrm/edit_quota.html', {'form': form, 'employee': employee})

@employee_required
def delete_quota(request, quotaid):
    if request.employee.role.name not in 'settings.PAYROLL_ADMIN_ROLES':
        messages.error(request, 'You do not have permission to delete quotas.')
        return redirect('core:add_leave_quota')
    quota = get_object_or_404(LeaveQuota, quotaid=quotaid)
    if request.method == 'POST':
        quota.delete()
        messages.success(request, 'Leave quota deleted successfully.')
        return redirect('core:add_leave_quota')
    return render(request, 'hrm/delete_quota.html', {'quota': quota})

@employee_required
def performance_review(request):
    if request.user.employee.role.name not in ['ADMIN', 'MANAGER', 'TEAM_LEADER']:
        messages.error(request, 'You do not have permission to add performance reviews.')
        return redirect('core:dashboard')

    # Get employees based on role
    if request.user.employee.role.name == 'ADMIN':
        employees = Employee.objects.all()
        all_employees = Employee.objects.select_related('user').all()
    else:
        employees = Employee.objects.filter(reporting_manager=request.user.employee)
        all_employees = Employee.objects.filter(reporting_manager=request.user.employee).select_related('user')

    # Filter employees needing review
    employees_needing_review = []
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    six_months_ago_date = six_months_ago.date()
    for emp in employees:
        latest_review = Performance.objects.filter(employee=emp).aggregate(Max('review_date'))['review_date__max']
        if not latest_review or latest_review < six_months_ago_date:
            employees_needing_review.append(emp)

    # Filter performance reviews
    performances = Performance.objects.filter(employee__in=employees).select_related('employee__user', 'reviewed_by')

    # Apply filters
    employee_id = request.GET.get('employee')
    review_period = request.GET.get('review_period')
    rating_range = request.GET.get('rating_range')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if employee_id:
        performances = performances.filter(employee_id=employee_id)
    if review_period:
        performances = performances.filter(review_period=review_period.upper())
    if rating_range:
        if rating_range == '1_5':
            performances = performances.filter(rating__lte=5)
        elif rating_range == '6_8':
            performances = performances.filter(rating__gte=6, rating__lte=8)
        elif rating_range == '9_10':
            performances = performances.filter(rating__gte=9)
    if date_from:
        performances = performances.filter(review_date__gte=date_from)
    if date_to:
        performances = performances.filter(review_date__lte=date_to)

    # Pagination
    paginator = Paginator(performances, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Handle form submission
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        employee = get_object_or_404(Employee, id=employee_id)

        if request.user.employee.role.name != 'ADMIN':
            reporting_employees = Employee.objects.filter(reporting_manager=request.user.employee)
            if employee not in reporting_employees:
                messages.error(request, 'You can only review employees who report to you.')
                return redirect('core:employee_list')

        form = PerformanceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.employee = employee
            review.reviewed_by = request.user
            review.save()
            messages.success(request, 'Performance review submitted successfully.')
            return redirect('core:performance_review')
    else:
        form = PerformanceReviewForm()

    context = {
        'employees_needing_review': employees_needing_review,
        'all_employees': all_employees,
        'form': form,
        'performances': page_obj,
        'employee_filter': employee_id,
        'review_period_filter': review_period,
        'rating_range_filter': rating_range,
        'date_from': date_from,
        'date_to': date_to,
        'review_period_choices': [choice[0] for choice in Performance.REVIEW_PERIOD_CHOICES],
        'rating_ranges': [
            ('1_5', '1-5'),
            ('6_8', '6-8'),
            ('9_10', '9-10'),
        ],
    }
    return render(request, 'hrm/performance_review.html', context)

@employee_required
def performance_review_edit(request, performance_id):
    performance = get_object_or_404(Performance, pk=performance_id)
    # Permission check: Only the reviewer (or Admin) can edit
    if request.user.employee.role.name not in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] or \
       (request.user.employee.role.name in ['MANAGER', 'TEAM_LEADER'] and performance.reviewed_by != request.user.employee and request.user.employee != performance.employee.reporting_manager):
        messages.error(request, 'You do not have permission to edit this review.')
        return redirect('core:dashboard' if request.user.employee.role.name == 'EMPLOYEE' else
                       'core:manager_performance_view' if request.user.employee.role.name in ['MANAGER', 'TEAM_LEADER'] else 'core:admin_performance_view')

    if request.method == 'POST':
        form = PerformanceReviewForm(request.POST, instance=performance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Performance review updated successfully.')
            return redirect('core:performance_review_detail', performance_id=performance.id)
    else:
        form = PerformanceReviewForm(instance=performance)

    context = {'form': form, 'performance': performance}
    return render(request, 'hrm/performance_review_edit.html', context)

@employee_required
def performance_review_delete(request, performance_id):
    performance = get_object_or_404(Performance, pk=performance_id)
    # Permission check: Only the reviewer (or Admin) can delete
    if request.user.employee.role.name not in ['ADMIN', 'MANAGER', 'TEAM_LEADER'] or \
       (request.user.employee.role.name in ['MANAGER', 'TEAM_LEADER'] and performance.reviewed_by != request.user.employee and request.user.employee != performance.employee.reporting_manager):
        messages.error(request, 'You do not have permission to delete this review.')
        return redirect('core:dashboard' if request.user.employee.role.name == 'EMPLOYEE' else
                       'core:manager_performance_view' if request.user.employee.role.name in ['MANAGER', 'TEAM_LEADER'] else 'core:admin_performance_view')

    if request.method == 'POST':
        performance.delete()
        messages.success(request, 'Performance review deleted successfully.')
        return redirect('core:manager_performance_view' if request.user.employee.role.name in ['MANAGER', 'TEAM_LEADER'] else 'core:admin_performance_view')

    context = {'performance': performance}
    return render(request, 'hrm/performance_review_delete.html', context)

# Admin Performance View
@employee_required
def admin_performance_view(request):
    if request.user.employee.role.name != 'ADMIN':
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('core:dashboard')

    performances = Performance.objects.select_related('employee__user', 'reviewed_by').all()

    # Apply filters
    department_id = request.GET.get('department')
    employee_id = request.GET.get('employee')
    review_period = request.GET.get('review_period')
    rating_range = request.GET.get('rating_range')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    employee_search = request.GET.get('employee_search')

    if department_id:
        performances = performances.filter(employee__department_id=department_id)
    if employee_id:
        performances = performances.filter(employee_id=employee_id)
    if review_period:
        performances = performances.filter(review_period=review_period.upper())
    if rating_range:
        if rating_range == '1_5':
            performances = performances.filter(rating__lte=5)
        elif rating_range == '6_8':
            performances = performances.filter(rating__gte=6, rating__lte=8)
        elif rating_range == '9_10':
            performances = performances.filter(rating__gte=9)
    if date_from:
        performances = performances.filter(review_date__gte=date_from)
    if date_to:
        performances = performances.filter(review_date__lte=date_to)
    if employee_search:
        # Split the search term into parts (e.g., "Sam Lee" -> ["Sam", "Lee"])
        search_terms = employee_search.strip().split()
        if len(search_terms) == 1:
            # Single term: match either first_name or last_name
            term = search_terms[0]
            performances = performances.filter(
                Q(employee__user__first_name__icontains=term) |
                Q(employee__user__last_name__icontains=term)
            )
        elif len(search_terms) >= 2:
            # Two or more terms: assume first term is first_name, second is last_name
            first_name = search_terms[0]
            last_name = search_terms[1]
            performances = performances.filter(
                Q(employee__user__first_name__icontains=first_name) &
                Q(employee__user__last_name__icontains=last_name)
            )

    # Pagination
    paginator = Paginator(performances, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    performances_for_stats = Performance.objects.all()
    performance_stats = {
        'monthly': performances_for_stats.filter(review_period='MONTHLY').count(),
        'quarterly': performances_for_stats.filter(review_period='QUARTERLY').count(),
        'annual': performances_for_stats.filter(review_period='ANNUAL').count(),
        'rating_1_5': performances_for_stats.filter(rating__lte=5).count(),
        'rating_6_8': performances_for_stats.filter(rating__gte=6, rating__lte=8).count(),
        'rating_9_10': performances_for_stats.filter(rating__gte=9).count(),
    }

    context = {
        'performances': page_obj,
        'all_employees': Employee.objects.select_related('user').all(),
        'departments': Department.objects.all(),
        'department_id': department_id,
        'employee_filter': employee_id,
        'review_period_filter': review_period,
        'rating_range_filter': rating_range,
        'date_from': date_from,
        'date_to': date_to,
        'employee_search': employee_search,
        'review_period_choices': [choice[0] for choice in Performance.REVIEW_PERIOD_CHOICES],
        'rating_ranges': [
            ('1_5', '1-5'),
            ('6_8', '6-8'),
            ('9_10', '9-10'),
        ],
        'performance_stats': performance_stats,
    }
    return render(request, 'hrm/admin_performance_view.html', context)

# Manager/Team Leader Performance View
@employee_required
def manager_performance_view(request):
    if request.user.employee.role.name not in ['MANAGER', 'TEAM_LEADER']:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('core:dashboard')

    employees = Employee.objects.filter(reporting_manager=request.user.employee)
    performances = Performance.objects.filter(employee__in=employees).select_related('employee__user', 'reviewed_by')

    # Apply filters
    employee_id = request.GET.get('employee')
    review_period = request.GET.get('review_period')
    rating_range = request.GET.get('rating_range')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    employee_search = request.GET.get('employee_search')

    if employee_id:
        performances = performances.filter(employee_id=employee_id)
    if review_period:
        performances = performances.filter(review_period=review_period.upper())
    if rating_range:
        if rating_range == '1_5':
            performances = performances.filter(rating__lte=5)
        elif rating_range == '6_8':
            performances = performances.filter(rating__gte=6, rating__lte=8)
        elif rating_range == '9_10':
            performances = performances.filter(rating__gte=9)
    if date_from:
        performances = performances.filter(review_date__gte=date_from)
    if date_to:
        performances = performances.filter(review_date__lte=date_to)
    if employee_search:
        # Split the search term into parts
        search_terms = employee_search.strip().split()
        if len(search_terms) == 1:
            # Single term: match either first_name or last_name
            term = search_terms[0]
            performances = performances.filter(
                Q(employee__user__first_name__icontains=term) |
                Q(employee__user__last_name__icontains=term)
            )
        elif len(search_terms) >= 2:
            # Two or more terms: assume first term is first_name, second is last_name
            first_name = search_terms[0]
            last_name = search_terms[1]
            performances = performances.filter(
                Q(employee__user__first_name__icontains=first_name) &
                Q(employee__user__last_name__icontains=last_name)
            )

    # Pagination
    paginator = Paginator(performances, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics
    performances_for_stats = Performance.objects.filter(employee__in=employees)
    performance_stats = {
        'monthly': performances_for_stats.filter(review_period='MONTHLY').count(),
        'quarterly': performances_for_stats.filter(review_period='QUARTERLY').count(),
        'annual': performances_for_stats.filter(review_period='ANNUAL').count(),
        'rating_1_5': performances_for_stats.filter(rating__lte=5).count(),
        'rating_6_8': performances_for_stats.filter(rating__gte=6, rating__lte=8).count(),
        'rating_9_10': performances_for_stats.filter(rating__gte=9).count(),
    }

    context = {
        'performances': page_obj,
        'all_employees': employees,
        'employee_filter': employee_id,
        'review_period_filter': review_period,
        'rating_range_filter': rating_range,
        'date_from': date_from,
        'date_to': date_to,
        'employee_search': employee_search,
        'review_period_choices': [choice[0] for choice in Performance.REVIEW_PERIOD_CHOICES],
        'rating_ranges': [
            ('1_5', '1-5'),
            ('6_8', '6-8'),
            ('9_10', '9-10'),
        ],
        'performance_stats': performance_stats,
    }
    return render(request, 'hrm/manager_performance_view.html', context)

# Employee Review Dashboard (Updated for Consistency)
@employee_required
def employee_review_dashboard(request):
    performances = Performance.objects.filter(employee=request.user.employee).select_related('employee__user', 'reviewed_by')

    # Apply filters
    review_period = request.GET.get('review_period')
    rating_range = request.GET.get('rating_range')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    employee_filter = request.GET.get('employee')  # Added employee filter parameter

    if review_period:
        performances = performances.filter(review_period=review_period.upper())
    if rating_range:
        if rating_range == '1_5':
            performances = performances.filter(rating__lte=5)
        elif rating_range == '6_8':
            performances = performances.filter(rating__gte=6, rating__lte=8)
        elif rating_range == '9_10':
            performances = performances.filter(rating__gte=9)
    if date_from:
        performances = performances.filter(review_date__gte=date_from)
    if date_to:
        performances = performances.filter(review_date__lte=date_to)
    # Handle employee filter (only for the logged-in employee)
    if employee_filter and employee_filter == str(request.user.employee.id):
        performances = performances.filter(employee_id=employee_filter)

    # Pagination
    paginator = Paginator(performances, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Statistics (for employee's own reviews)
    performances_for_stats = Performance.objects.filter(employee=request.user.employee)
    performance_stats = {
        'monthly': performances_for_stats.filter(review_period='MONTHLY').count(),
        'quarterly': performances_for_stats.filter(review_period='QUARTERLY').count(),
        'annual': performances_for_stats.filter(review_period='ANNUAL').count(),
        'rating_1_5': performances_for_stats.filter(rating__lte=5).count(),
        'rating_6_8': performances_for_stats.filter(rating__gte=6, rating__lte=8).count(),
        'rating_9_10': performances_for_stats.filter(rating__gte=9).count(),
    }

    context = {
        'performances': page_obj,
        'review_period_filter': review_period,
        'rating_range_filter': rating_range,
        'date_from': date_from,
        'date_to': date_to,
        'employee_filter': employee_filter,  # Added to context for dropdown pre-selection
        'review_period_choices': [choice[0] for choice in Performance.REVIEW_PERIOD_CHOICES],
        'rating_ranges': [
            ('1_5', '1-5'),
            ('6_8', '6-8'),
            ('9_10', '9-10'),
        ],
        'performance_stats': performance_stats,
    }
    return render(request, 'hrm/employee_review_dashboard.html', context)



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
            return redirect('core:employee_list')  # Redirect to dashboard
        else:
            messages.error(request, 'There was an error adding the employee. Please check the form.')
    else:
        user_form = UserForm()
        employee_form = EmployeeForm()

    context = {
        'user_form': user_form,
        'employee_form': employee_form,
    }
    return render(request, 'hrm/add_employee.html', context)

def is_admin(user):
    try:
        return user.is_authenticated and user.employee.role.name == 'ADMIN'
    except Employee.DoesNotExist: # Handle case where employee doesn't exist
        return False

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
    messages.success(request, 'You have been logged out successfully.', extra_tags='logout-success')
    return redirect('core:login_register')

@login_required
def role_list(request):
    roles = Role.objects.all()
    return render(request, 'hrm/core/role_list.html', {'roles': roles})

@login_required
def role_create(request):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role created successfully.')
            return redirect('core:role_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RoleForm() # Create an instance of RoleForm
    return render(request, 'hrm/core/role_create.html', {'form': form}) # Pass the form to the template

@login_required
def role_update(request, role_id):
    role = get_object_or_404(Role, pk=role_id)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()  # This will now save name, description, and status
            messages.success(request, 'Role updated successfully.')
            return redirect('core:role_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RoleForm(instance=role)
    return render(request, 'hrm/core/role_update.html', {'form': form, 'role': role})

@login_required
@user_passes_test(is_admin)# Restrict to Admin users
def role_delete(request, role_id):
    role = get_object_or_404(Role, pk=role_id)

    if request.method == 'POST':
        role.status = False  # Soft delete: set status to False (inactive)
        role.save()
        messages.success(request, f'Role "{role.name}" made inactive successfully.') # Updated message
        return redirect('core:role_list')

    return redirect('core:role_list')

@employee_required
def edit_employee(request, employee_id):
    if request.employee.role.name not in 'settings.PAYROLL_ADMIN_ROLES':
        messages.error(request, 'You do not have permission to edit employees.')
        return redirect('core:employee_list')

    employee = get_object_or_404(Employee, id=employee_id)
    user = employee.user

    if request.method == 'POST':
        # Store the original password hash
        original_password = user.password
        user_form = UserForm(request.POST, instance=user)
        employee_form = EmployeeForm(request.POST, request.FILES, instance=employee)
        print("Initial user_form data:", user_form.initial)

        if user_form.is_valid() and employee_form.is_valid():
            user = user_form.save(commit=False)
            new_password = user_form.cleaned_data.get('password')
            if new_password:  # Only set password if a new one is provided
                user.set_password(new_password)
            else:
                user.password = original_password  # Restore original password if no new one
            user.save()
            employee = employee_form.save()
            messages.success(request, 'Employee updated successfully.')
            return redirect('core:employee_list')  # Redirect to dashboard
    else:
        user_form = UserForm(instance=user)
        employee_form = EmployeeForm(instance=employee)

    context = {
        'user_form': user_form,
        'employee_form': employee_form,
        'employee': employee
    }
    return render(request, 'hrm/edit_employee.html', context)

@employee_required
def delete_employee(request, employee_id):
    if request.employee.role.name not in 'settings.PAYROLL_ADMIN_ROLES':
        messages.error(request, 'You do not have permission to delete employees.')
        return redirect('core:employee_list')

    if request.method == 'POST':
        try:
            employee = get_object_or_404(Employee, id=employee_id)
            employee.delete()
            messages.success(request, 'Employee deleted successfully.')
        except Employee.DoesNotExist:
            messages.error(request, 'No employee matches the given query.')
    else:  # Handle GET requests
        messages.error(request,
                       'Deletion is not allowed via GET request. Please use the delete button on the employee list.')

    return redirect('core:employee_list')

logger = logging.getLogger(__name__) # Get logger

@employee_required
def employee_performance_detail(request, employee_id):
    employee = get_object_or_404(Employee, pk=employee_id)
    performance_reviews = Performance.objects.filter(employee=employee).order_by('-review_date') # Get all reviews for this employee

    logger.debug(f"Fetched performance_reviews for employee_id {employee_id}: {performance_reviews}") # Debug log

    for review in performance_reviews:
        logger.debug(f"Review ID: {review.id}")

    context = {
        'employee': employee,
        'performance_reviews': performance_reviews,
    }
    return render(request, 'hrm/employee_performance_detail.html', context) # Create this template

@employee_required
def performance_review_detail(request, performance_id):
    performance = get_object_or_404(Performance, pk=performance_id)

    # Restrict access: Employees can only see their own reviews; Managers/TLs can see reviews of their reporting employees
    if request.employee.role.name == 'EMPLOYEE' and performance.employee != request.employee:
        messages.error(request, 'You do not have permission to view this review.')
        return redirect('core:employee_review_dashboard')
    elif request.employee.role.name in ['MANAGER', 'TEAM_LEADER']:
        reporting_employees = Employee.objects.filter(reporting_manager=request.employee)
        if performance.employee not in reporting_employees:
            messages.error(request, 'You can only view reviews of employees who report to you.')
            return redirect('core:dashboard')

    context = {
        'performance': performance,
    }
    return render(request, 'hrm/performance_review_list.html', context)


@employee_required
def add_task(request):
    if request.employee.role.name not in ['ADMIN', 'MANAGER', 'TEAM_LEADER']:
        messages.error(request, 'You do not have permission to create tasks.')
        return redirect('core:task_list')

    if request.method == 'POST':
        task_form = TaskForm(request.POST)
        assignment_form = TaskAssignmentForm(request.user, request.POST)

        if task_form.is_valid() and assignment_form.is_valid():
            task = task_form.save()  # First save the Task

            assignment = assignment_form.save(commit=False)  # Get TaskAssignment instance without saving yet
            assignment.task = task  # Link to the Task we just saved
            assignment.assigned_by = request.user  # Use request.user (User instance)
            assignment.save()  # Now save TaskAssignment with task and assigned_by set

            messages.success(request, 'Task created and assigned successfully.')
            return redirect('core:manager_task_view')  # Redirect to manager view for consistency
        else:
            messages.error(request, 'There was an error in the form. Please correct it.')
    else:  # GET request
        task_form = TaskForm()
        assignment_form = TaskAssignmentForm(request.user)

    context = {'task_form': task_form, 'assignment_form': assignment_form}
    return render(request, 'hrm/add_task.html', context)


@employee_required
def update_task(request, task_id):
    task = get_object_or_404(Task, task_id=task_id)
    assignment = get_object_or_404(TaskAssignment, task=task)

    if request.method == 'POST':
        task_form = TaskForm(request.POST, instance=task)
        assignment_form = TaskAssignmentForm(request.user, request.POST, instance=assignment)

        if task_form.is_valid() and assignment_form.is_valid():
            # Save the task first
            task = task_form.save()

            # Update the existing assignment instead of creating a new one
            assignment = assignment_form.save(commit=False)
            assignment.task = task  # Ensure the task reference is updated
            assignment.assigned_by = request.user  # Update assigned_by if needed
            assignment.save()  # Save the existing assignment

            messages.success(request, 'Task updated successfully.')
            return redirect('core:manager_task_view')  # Redirect to manager_task_view for consistency
        else:
            messages.error(request, 'There was an error updating the task. Please correct the form.')
    else:
        task_form = TaskForm(instance=task)
        assignment_form = TaskAssignmentForm(request.user, instance=assignment)

    context = {
        'task_form': task_form,
        'assignment_form': assignment_form,
        'task': task,
        'assignment': assignment  # Pass assignment to context for debugging or display
    }
    return render(request, 'hrm/update_task.html', context)

# core/views.py
@employee_required
def task_detail(request, assignment_id):
    assignment = get_object_or_404(TaskAssignment, assignment_id=assignment_id)
    context = {
        'assignment': assignment,
        'task_stats': {
            'total': TaskAssignment.objects.filter(task=assignment.task).count(),  # Total assignments for this task
            'completed': TaskAssignment.objects.filter(task=assignment.task, status='COMPLETED').count(),
            'in_progress': TaskAssignment.objects.filter(task=assignment.task, status='IN_PROGRESS').count(),
            'pending': TaskAssignment.objects.filter(task=assignment.task, status='PENDING').count(),
        }
    }
    return render(request, 'hrm/task_detail.html', context)

@employee_required
def delete_task(request, task_id):
    print(f"delete_task view called with task_id: {task_id}")  # Debug print

    task = get_object_or_404(Task, task_id=task_id)
    print(f"Task to be deleted: {task.task_title}") # Debug print

    if request.method == 'POST':
        try:
            assignment = get_object_or_404(TaskAssignment, task=task)
            print(f"Deleting task assignment: {assignment}") # Debug print
            assignment.delete()

            print(f"Deleting task: {task.task_title}") # Debug print
            task.delete()

            messages.success(request, 'Task deleted successfully.')
            return redirect('core:task_list')  # Redirect back to the task list

        except TaskAssignment.DoesNotExist:
            print("TaskAssignment does not exist.")  # Should not happen, but good to check
            messages.error(request, 'Task assignment does not exist')
            return redirect('core:task_list')
        except Exception as e:
            print(f"An error occurred during deletion: {e}")
            messages.error(request, f"An error occurred: {e}")
            return redirect('core:task_list')

    else:
        print("GET request to delete_task - not allowed") # DEBUG
        messages.error(request,"Deletion is not allowed via GET request.")
        return redirect('core:task_list')



@employee_required
def get_employees_by_department(request):
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest': # Check for AJAX
        department_id = request.GET.get('department_id')
        if department_id:
            employees = Employee.objects.filter(department_id=department_id).select_related('user')
            employee_list = [
                {
                    'id': emp.id,
                    'user__get_full_name': emp.user.get_full_name() if emp.user.get_full_name() else 'Unnamed Employee'
                }
                for emp in employees
            ]
            return JsonResponse({'employees': employee_list})
        return JsonResponse({'employees': []})
    return JsonResponse({'error': 'Invalid request'}, status=400) # Return 400 for non-AJAX or non-GET


@employee_required
def admin_task_view(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to view this page.')
        return redirect('core:login_register')

    # Restrict access to ADMIN role
    if request.employee.role.name != 'ADMIN':
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('core:task_list')

    # Fetch departments
    departments = Department.objects.all()

    # Fetch filter values from the request
    department_id = request.GET.get('department')
    employee_filter = request.GET.get('employee')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Get all employees (unfiltered for the initial context)
    all_employees = Employee.objects.select_related('user').all()

    # Filter employees for the form based on department_id
    employees = all_employees
    if department_id:
        employees = employees.filter(department_id=department_id)

    # Fetch task assignments with filtering (unpaginated queryset for stats)
    assignments_queryset = TaskAssignment.objects.select_related('employee__user', 'task').all()

    if department_id:
        assignments_queryset = assignments_queryset.filter(employee__department_id=department_id)
    if employee_filter:
        assignments_queryset = assignments_queryset.filter(employee__id=employee_filter)
    if status_filter:
        assignments_queryset = assignments_queryset.filter(status=status_filter)
    if date_from and date_to:
        assignments_queryset = assignments_queryset.filter(assigned_date__range=[date_from, date_to])

    # Task statistics (calculated on unpaginated queryset)
    task_stats = {
        'total': assignments_queryset.count(),
        'completed': assignments_queryset.filter(status='COMPLETED').count(),
        'in_progress': assignments_queryset.filter(status='IN_PROGRESS').count(),
        'pending': assignments_queryset.filter(status='PENDING').count(),
    }

    # Pagination
    paginator = Paginator(assignments_queryset, 5)  # 5 items per page
    page = request.GET.get('page')
    try:
        assignments = paginator.page(page)
    except PageNotAnInteger:
        assignments = paginator.page(1)
    except EmptyPage:
        assignments = paginator.page(paginator.num_pages)

    context = {
        'today': timezone.now(),
        'assignments': assignments,
        'task_stats': task_stats,
        'departments': departments,
        'employees': employees,
        'all_employees': all_employees,
        'department_id': department_id,
        'employee_filter': employee_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': ['PENDING', 'IN_PROGRESS', 'COMPLETED'],
    }

    return render(request, 'hrm/admin_task_view.html', context)

@employee_required
def manager_task_view(request):
    if request.employee.role.name not in ['MANAGER', 'TEAM_LEADER', 'ADMIN']:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('core:task_list')

    departments = Department.objects.all()
    department_id = request.GET.get('department')
    employee_filter = request.GET.get('employee')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if request.employee.role.name == 'ADMIN':
        all_employees = Employee.objects.all().select_related('user')
    else:
        all_employees = Employee.objects.filter(reporting_manager=request.employee).select_related('user')

    employees = all_employees
    if department_id:
        employees = employees.filter(department_id=department_id)

    if request.employee.role.name == 'ADMIN':
        assignments_queryset = TaskAssignment.objects.select_related('employee__user', 'task').all().distinct()
        performances = Performance.objects.all()
    else:
        assignments_queryset = TaskAssignment.objects.select_related('employee__user', 'task').filter(
            employee__in=all_employees
        ).distinct()
        performances = Performance.objects.filter(employee__in=all_employees)

    if department_id:
        assignments_queryset = assignments_queryset.filter(employee__department_id=department_id)
    if employee_filter:
        assignments_queryset = assignments_queryset.filter(employee__id=employee_filter)
    if status_filter:
        assignments_queryset = assignments_queryset.filter(status=status_filter)
    if date_from and date_to:
        assignments_queryset = assignments_queryset.filter(assigned_date__range=[date_from, date_to])

    task_stats = {
        'total': assignments_queryset.count(),
        'completed': assignments_queryset.filter(status='COMPLETED').count(),
        'in_progress': assignments_queryset.filter(status='IN_PROGRESS').count(),
        'pending': assignments_queryset.filter(status='PENDING').count(),
    }

    # Performance statistics
    performance_stats = {
        'total_reviews': performances.count(),
        'monthly': performances.filter(review_period='MONTHLY').count(),
        'quarterly': performances.filter(review_period='QUARTERLY').count(),
        'annual': performances.filter(review_period='ANNUAL').count(),
        'rating_1_5': performances.filter(rating__lte=5).count(),
        'rating_6_8': performances.filter(rating__gte=6, rating__lte=8).count(),
        'rating_9_10': performances.filter(rating__gte=9).count(),
    }

    paginator = Paginator(assignments_queryset, 5)
    page = request.GET.get('page')
    try:
        assignments = paginator.page(page)
    except PageNotAnInteger:
        assignments = paginator.page(1)
    except EmptyPage:
        assignments = paginator.page(paginator.num_pages)

    context = {
        'today': timezone.now(),
        'assignments': assignments,
        'task_stats': task_stats,
        'departments': departments,
        'employees': employees,
        'all_employees': all_employees,
        'department_id': department_id,
        'employee_filter': employee_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': ['PENDING', 'IN_PROGRESS', 'COMPLETED'],
        'performance_stats': performance_stats,  # Add performance stats
    }

    return render(request, 'hrm/manager_task_view.html', context)

@employee_required
def employee_task_view(request):
    if request.employee.role.name != 'EMPLOYEE':
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('core:task_list')

    # Fetch filter values from the request
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Fetch only the current employee's assignments (unpaginated queryset for stats)
    assignments_queryset = TaskAssignment.objects.select_related('employee__user', 'task').filter(employee=request.employee)

    # Apply filters
    if status_filter:
        assignments_queryset = assignments_queryset.filter(status=status_filter)
    if date_from and date_to:
        assignments_queryset = assignments_queryset.filter(assigned_date__range=[date_from, date_to])

    # Task statistics (calculated on unpaginated queryset)
    task_stats = {
        'total': assignments_queryset.count(),
        'completed': assignments_queryset.filter(status='COMPLETED').count(),
        'in_progress': assignments_queryset.filter(status='IN_PROGRESS').count(),
        'pending': assignments_queryset.filter(status='PENDING').count(),
    }

    # Pagination
    paginator = Paginator(assignments_queryset, 5)  # 5 items per page
    page = request.GET.get('page')
    try:
        assignments = paginator.page(page)
    except PageNotAnInteger:
        assignments = paginator.page(1)
    except EmptyPage:
        assignments = paginator.page(paginator.num_pages)

    context = {
        'today': timezone.now(),
        'assignments': assignments,
        'task_stats': task_stats,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': ['PENDING', 'IN_PROGRESS', 'COMPLETED'],
    }

    return render(request, 'hrm/employee_task_view.html', context)

@employee_required
@require_POST
def mark_completed(request, assignment_id):
    try:
        assignment = get_object_or_404(TaskAssignment, assignment_id=assignment_id)
        is_admin = request.employee.role.name == 'ADMIN'
        is_manager_or_leader = request.employee.role.name in ['MANAGER', 'TEAM_LEADER']
        is_reporting_manager = assignment.employee.reporting_manager == request.employee

        if is_admin or (is_manager_or_leader and is_reporting_manager):
            if assignment.status != 'COMPLETED':
                assignment.status = 'COMPLETED'
                assignment.completed_at = timezone.now()
                assignment.save()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Task marked as completed',
                    'completed_at': timezone.now().strftime('%d-%m-%Y %H:%M')
                })
            else:
                return JsonResponse({'status': 'error', 'message': 'Task already completed'}, status=400)
        else:
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
            messages.success(request, 'Your profile has been updated successfully.', extra_tags='profile')
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
                user = login_form.save(request)
                if user:
                    messages.success(request, f"Welcome back, {user.first_name or user.username}! Login successful.", extra_tags='login-success')
                    return redirect('core:dashboard')
                else:
                    messages.error(request, "Authentication failed. Please check your credentials.")
            else:
                errors = login_form.errors.as_data()
                if 'username' in errors:
                    for error in errors['username']:
                        messages.error(request, str(error))
                if 'password' in errors:
                    for error in errors['password']:
                        messages.error(request, str(error))
                if '__all__' in errors:
                    for error in errors['__all__']:
                        messages.error(request, str(error))
                context['login_form'] = login_form
        # ... (signup logic unchanged)
        elif 'signup_submit' in request.POST:
            signup_form = SignupForm(request.POST, prefix='signup')
            if signup_form.is_valid():
                user = signup_form.save()
                messages.success(request, f"Welcome, {user.first_name or user.username}! Your account has been created successfully. Please log in.")
                signup_form = SignupForm(prefix='signup')  # Reset form after success
                context['signup_form'] = signup_form
            else:
                errors = signup_form.errors.as_data()
                for field, error_list in errors.items():
                    for error in error_list:
                        messages.error(request, f"{signup_form.fields[field].label}: {error}")
                context['signup_form'] = signup_form

    messages_list = messages.get_messages(request)
    context['messages'] = messages_list
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

def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            otp = generate_and_send_otp(email)
            # Store OTP in cache with a 10-minute expiration
            cache.set(f'otp_{email}', otp, 600)  # 600 seconds = 10 minutes
            cache.set(f'email_{otp}', email, 600)
            messages.success(request, 'An OTP has been sent to your email. Please check your inbox.')
            return redirect('core:verify_otp')
    else:
        form = ForgotPasswordForm()
    return render(request, 'hrm/forgot_password.html', {'form': form})

def verify_otp(request):
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            cached_email = cache.get(f'email_{otp}')
            if cached_email:
                cache.delete(f'email_{otp}')  # Clear the OTP
                cache.delete(f'otp_{cached_email}')  # Clear the email-OTP mapping
                cache.set('reset_email', cached_email, 600)  # Store email for reset
                messages.success(request, 'OTP verified successfully. Please set a new password.')
                return redirect('core:reset_password')
            else:
                messages.error(request, 'Invalid or expired OTP. Please try again.')
    else:
        form = OTPVerificationForm()
    return render(request, 'hrm/verify_otp.html', {'form': form})

def reset_password(request):
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            user_email = cache.get('reset_email')  # Retrieve email from previous step (set in verify_otp if needed)
            if user_email:
                user = User.objects.get(email=user_email)
                user.set_password(form.cleaned_data['new_password'])
                user.save()
                cache.delete('reset_email')  # Clear the email after reset
                messages.success(request, 'Password reset successfully. Please log in with your new password.')
                return redirect('core:login_register')
            else:
                messages.error(request, 'Session expired. Please start the process again.')
    else:
        form = ResetPasswordForm()
        # Store the email in cache for the reset process (set this in verify_otp view)
        if 'email' in request.session:
            cache.set('reset_email', request.session['email'], 600)
    return render(request, 'hrm/reset_password.html', {'form': form})