from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_payroll_email(payroll):
    subject = f'Salary Payment Processed - {payroll.period_start.strftime("%B %Y")}'

    context = {
        'employee_name': payroll.employee.user.get_full_name(),
        'period': f"{payroll.period_start.strftime('%B %d')} - {payroll.period_end.strftime('%B %d, %Y')}",
        'basic_salary': payroll.basic_salary,
        'overtime_pay': payroll.overtime_hours * payroll.overtime_rate,
        'bonuses': payroll.bonuses,
        'deductions': payroll.deductions,
        'net_salary': payroll.net_salary,
        'payment_date': payroll.payment_date.strftime("%B %d, %Y")
    }

    html_message = render_to_string('hrm/email/payroll_processed.html', context)

    send_mail(
        subject=subject,
        message='',
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[payroll.employee.user.email],
        fail_silently=False
    )