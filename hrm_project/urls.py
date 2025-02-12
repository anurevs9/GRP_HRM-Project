"""
URL configuration for hrm_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from core.api_views import (
    DepartmentViewSet, RoleViewSet, EmployeeViewSet,
    TaskViewSet, LeaveViewSet, PerformanceViewSet, RecruitmentViewSet, CandidateViewSet, TrainingViewSet,
    PayrollViewSet, AttendanceViewSet
)
# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'departments', DepartmentViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'leaves', LeaveViewSet, basename='leave')
router.register(r'performances', PerformanceViewSet, basename='performance')
router.register(r'recruitment', RecruitmentViewSet)
router.register(r'candidates', CandidateViewSet)
router.register(r'training', TrainingViewSet)
router.register(r'payroll', PayrollViewSet)
router.register(r'attendance', AttendanceViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('api/', include(router.urls)),  # API endpoints
    path('api-auth/', include('rest_framework.urls')),  # DRF browsable API authentication
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)