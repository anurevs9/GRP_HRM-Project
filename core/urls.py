from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from . import views
from django.contrib.auth import views as auth_views

app_name = 'core'  # VERY IMPORTANT: Add app_name

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('employees/', views.employee_list, name='employee_list'),
    path('logout/', views.user_logout, name='logout'),
    path('profile-setup/', views.profile_setup, name='profile_setup'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('login-register/', views.login_register_view, name='login_register'),
    path('tasks/', RedirectView.as_view(url=reverse_lazy('core:admin_task_view')), name='task_list'),
    path('leave-request/', views.leave_request, name='leave_request'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('employee/<int:employee_id>/performance/', views.employee_performance_detail,name='employee_performance_detail'),
    # New Performance Management URLs
    path('performance-reviews/<int:performance_id>/', views.performance_review_detail, name='performance_review_detail'),
    path('performance-review/', views.performance_review, name='performance_review'),
    path('admin-performance-view/', views.admin_performance_view, name='admin_performance_view'),
    path('manager-performance-view/', views.manager_performance_view, name='manager_performance_view'),
    path('employee-review-dashboard/', views.employee_review_dashboard, name='employee_review_dashboard'),
    path('performance-review-edit/<int:performance_id>/', views.performance_review_edit, name='performance_review_edit'),
    path('performance-review-delete/<int:performance_id>/', views.performance_review_delete, name='performance_review_delete'),

    # Employee management URLs
    path('employee/add/', views.add_employee, name='add_employee'),
    path('employee/edit/<int:employee_id>/', views.edit_employee, name='edit_employee'),
    path('employee/delete/<int:employee_id>/', views.delete_employee, name='delete_employee'),

    #Role URLs
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/update/<int:role_id>/', views.role_update, name='role_update'),
    path('roles/delete/<int:role_id>/', views.role_delete, name='role_delete'),

    # Task management URLs
    path('task/add/', views.add_task, name='add_task'),
    path('task/update/<int:task_id>/', views.update_task, name='update_task'),
    path('task/delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('mark_completed/<int:assignment_id>/', views.mark_completed, name='mark_completed'),
    path('admin-tasks/', views.admin_task_view, name='admin_task_view'),
    path('manager-tasks/', views.manager_task_view, name='manager_task_view'),
    path('employee-tasks/', views.employee_task_view, name='employee_task_view'),
    path('get-employees-by-department/', views.get_employees_by_department, name='get_employees_by_department'),
    path('task/detail/<int:assignment_id>/', views.task_detail, name='task_detail'),


    # Department management URLs
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    path('departments/deactivate/<int:pk>/', views.department_deactivate, name='department_deactivate'), # New

    # Recruitment URLs
    path('recruitment/', views.recruitment_list, name='recruitment_list'),
    path('recruitment/create/', views.recruitment_create, name='recruitment_create'),
    path('recruitment/<int:recruitment_id>/candidates/', views.candidate_list, name='candidate_list'),
    path('recruitment/<int:recruitment_id>/apply/', views.apply_for_job, name='apply_for_job'),
    path('recruitment/<int:recruitment_id>/', views.recruitment_detail, name='recruitment_detail'),

    # Training URLs
    path('trainings/', views.training_list, name='training_list'),
    path('trainings/create/', views.training_create, name='training_create'),

    # Attendance URLs
    path('attendance/mark/', views.attendance_mark, name='attendance_mark'),
    path('attendance/report/', views.attendance_report, name='attendance_report'),

    #reports
    path('reports/', views.reports_view, name='reports'),
    path('reports/employee/', views.employee_report, name='employee_report'),
    path('reports/task/', views.task_report, name='task_report'),
    path('reports/performance/', views.performance_report, name='performance_report'),
    path('reports/payroll/', views.payroll_report, name='payroll_report'),
    path('reports/recruitment/', views.recruitment_report, name='recruitment_report'),
    path('reports/training/', views.training_report, name='training_report'),

    # Payroll URLs
    path('payroll/<int:payroll_id>/process/', views.process_payroll_payment, name='process_payroll_payment'),
    path('payroll/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('payroll/<int:payroll_id>/status/', views.get_payment_status, name='get_payment_status'),
    path('payroll/', views.payroll_list, name='payroll_list'),
    path('payroll/create/', views.create_payroll, name="payroll_create"), #Added missing /
    path('payroll/<int:pk>/', views.payroll_detail, name="payroll_detail")


]