from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Department, Role, Employee, Task, Leave, Performance, Payroll, Attendance, Training, Candidate, \
    Recruitment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'status']
        read_only_fields = ['id', 'created_at', 'updated_at']

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']

class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    role = RoleSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'employee_id', 'department', 'role',
            'phone', 'address', 'date_joined', 'profile_picture'
        ]
        read_only_fields = ['id', 'employee_id']

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = EmployeeSerializer(read_only=True)
    assigned_by = UserSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'assigned_to',
            'assigned_by', 'due_date', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class LeaveSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = Leave
        fields = [
            'id', 'employee', 'leave_type', 'start_date',
            'end_date', 'reason', 'status', 'applied_on'
        ]
        read_only_fields = ['id', 'applied_on']

class PerformanceSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)

    class Meta:
        model = Performance
        fields = [
            'id', 'employee', 'review_period', 'rating',
            'feedback', 'goals', 'reviewed_by', 'review_date'
        ]
        read_only_fields = ['id', 'review_date']


class RecruitmentSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = Recruitment
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class CandidateSerializer(serializers.ModelSerializer):
    position = RecruitmentSerializer(read_only=True)

    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ['id', 'applied_date']


class TrainingSerializer(serializers.ModelSerializer):
    trainer = EmployeeSerializer(read_only=True)
    participants = EmployeeSerializer(many=True, read_only=True)

    class Meta:
        model = Training
        fields = '__all__'
        read_only_fields = ['id']


class PayrollSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = Payroll
        fields = '__all__'
        read_only_fields = ['id', 'net_salary']


class AttendanceSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ['id']