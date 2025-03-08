from django.contrib import admin
from .models import (
    Department, Role, Employee, Task, Leave, Performance,
    Recruitment, Candidate, Training, Payroll, Attendance
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'user', 'department', 'role', 'date_joined')
    list_filter = ('department', 'role', 'date_joined')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'employee_id')

class TaskAssignmentStatusFilter(admin.SimpleListFilter):
    title = 'Assignment Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('PENDING', 'Pending'),
            ('IN_PROGRESS', 'In Progress'),
            ('COMPLETED', 'Completed'),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(taskassignment_set__status=self.value())
        return queryset

# Update TaskAdmin to include the custom filter
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_title', 'get_assigned_to', 'start_date', 'end_date', 'get_status')
    list_filter = ('start_date', 'end_date', TaskAssignmentStatusFilter)
    search_fields = ('task_title',)

    def get_assigned_to(self, obj):
        assignment = obj.taskassignment_set.first()
        return assignment.employee.user.get_full_name if assignment else "Not Assigned"
    get_assigned_to.short_description = 'Assigned To'

    def get_status(self, obj):
        assignment = obj.taskassignment_set.first()
        return assignment.status if assignment else "PENDING"
    get_status.short_description = 'Status'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related('taskassignment_set')

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('leave_type', 'status')
    search_fields = ('employee__user__username', 'reason')

@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'review_title', 'review_period', 'rating', 'review_date')
    list_filter = ('review_period', 'rating', 'review_date')
    search_fields = ('employee__user__username', 'review_title', 'feedback')

@admin.register(Recruitment)
class RecruitmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'positions', 'status', 'deadline')
    list_filter = ('status', 'department')
    search_fields = ('title', 'description')

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'email', 'stage', 'applied_date')
    list_filter = ('stage', 'applied_date')
    search_fields = ('name', 'email')

@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ('title', 'trainer', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'start_date')
    search_fields = ('title', 'description')
    filter_horizontal = ('participants',)

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'period_start', 'period_end', 'net_salary', 'payment_status')
    list_filter = ('payment_status', 'payment_date')
    search_fields = ('employee__user__username',)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')
    list_filter = ('status', 'date')
    search_fields = ('employee__user__username',)