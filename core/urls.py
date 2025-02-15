from django.urls import path
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
    path('tasks/', views.task_list, name='task_list'),
    path('leave-request/', views.leave_request, name='leave_request'),
    path('performance-review/<int:employee_id>/', views.performance_review, name='performance_review'),

    # Employee management URLs
    path('employee/add/', views.add_employee, name='add_employee'),
    path('employee/edit/<int:employee_id>/', views.edit_employee, name='edit_employee'),

    #Role URLs
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),
    path('roles/update/<int:role_id>/', views.role_update, name='role_update'),
    path('roles/delete/<int:role_id>/', views.role_delete, name='role_delete'),

    # Task management URLs
    path('task/add/', views.add_task, name='add_task'),
    path('task/update/<int:task_id>/', views.update_task, name='update_task'),

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