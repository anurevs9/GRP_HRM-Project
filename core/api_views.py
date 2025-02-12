from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Department, Role, Employee, Task, Leave, Performance, Attendance, Payroll, Training, Candidate, \
    Recruitment
from .serializers import (
    DepartmentSerializer, RoleSerializer, EmployeeSerializer,
    TaskSerializer, LeaveSerializer, PerformanceSerializer, AttendanceSerializer, PayrollSerializer, TrainingSerializer,
    CandidateSerializer, RecruitmentSerializer
)

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        department = self.get_object()
        department.status = False
        department.save()
        return Response({'status': 'department deactivated'})

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Employee.objects.all()
        return Employee.objects.filter(user=self.request.user)

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Task.objects.all()
        return Task.objects.filter(assigned_to__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

class LeaveViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Leave.objects.all()
        return Leave.objects.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        employee = get_object_or_404(Employee, user=self.request.user)
        serializer.save(employee=employee)

class PerformanceViewSet(viewsets.ModelViewSet):
    serializer_class = PerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Performance.objects.all()
        return Performance.objects.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reviewed_by=self.request.user)

class RecruitmentViewSet(viewsets.ModelViewSet):
    queryset = Recruitment.objects.all()
    serializer_class = RecruitmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    @action(detail=True, methods=['post'])
    def close_position(self, request, pk=None):
        recruitment = self.get_object()
        recruitment.status = 'CLOSED'
        recruitment.save()
        return Response({'status': 'position closed'})

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    @action(detail=True, methods=['post'])
    def update_stage(self, request, pk=None):
        candidate = self.get_object()
        new_stage = request.data.get('stage')
        if new_stage in dict(Candidate.STAGE_CHOICES):
            candidate.stage = new_stage
            candidate.save()
            return Response({'status': 'stage updated'})
        return Response({'error': 'invalid stage'}, status=400)

class TrainingViewSet(viewsets.ModelViewSet):
    queryset = Training.objects.all()
    serializer_class = TrainingSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        training = self.get_object()
        employee = request.user.employee
        training.participants.add(employee)
        return Response({'status': 'enrolled successfully'})

class PayrollViewSet(viewsets.ModelViewSet):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        payroll = self.get_object()
        payroll.calculate_net_salary()
        payroll.payment_status = True
        payroll.save()
        return Response({'status': 'payment processed'})

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Attendance.objects.all()
        return Attendance.objects.filter(employee__user=self.request.user)