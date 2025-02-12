import razorpay
from django.conf import settings


def create_razorpay_payment(amount, currency="INR"):
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    payment_data = {
        'amount': amount * 100,  # Razorpay expects amount in paise
        'currency': currency,
        'payment_capture': 1
    }

    payment = client.order.create(data=payment_data)
    return payment