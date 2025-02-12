from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.functional import SimpleLazyObject  # Correct import


def get_employee(user):
    if not hasattr(user, '_employee_cache'):
        if user.is_authenticated:
            try:
                user._employee_cache = user.employee  # Use user.employee
            except user._meta.model.employee.RelatedObjectDoesNotExist:
                # Use _meta.model and .RelatedObjectDoesNotExist
                user._employee_cache = None
        else:
            user._employee_cache = None
    return user._employee_cache

class EmployeeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user'):
            request.employee = SimpleLazyObject(lambda: get_employee(request.user))
        response = self.get_response(request)
        return response


class ProfileSetupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Exclude paths using namespaced URL names AND startswith for static/media
            excluded_paths = [
                reverse('core:profile_setup'),
                reverse('core:logout'),
                reverse('core:login_register'),
                # reverse('core:register'),
                '/admin/',  # Always exclude admin
                settings.STATIC_URL,  # Exclude static files
                settings.MEDIA_URL,  # Exclude media files
            ]

            # Use a loop for cleaner exclusion checks
            if not any(request.path.startswith(path) for path in excluded_paths):
                employee = get_employee(request.user) # Using the correct get_employee
                if not employee:
                    messages.warning(request, "Please complete your profile setup first.")
                    return redirect('core:profile_setup')  # CORRECT: Use namespaced URL

        response = self.get_response(request)
        return response