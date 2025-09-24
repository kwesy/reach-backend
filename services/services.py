import requests
from decouple import config
from rest_framework.exceptions import (
    ValidationError,
    APIException
)
import logging
from django.core.mail import send_mail
from django.template.loader import get_template
from django.conf import settings

logger = logging.getLogger("anypay")

def send_sms(recipients: list, message: str) -> bool:
    """
    Send an SMS to the specified phone number with the given message.
    
    Args:
        phone_number (str): The recipient's phone number.
        message (str): The message content to be sent.
        
    Returns:
        bool: True if the SMS was sent successfully, False otherwise.
    """
    url = "https://sms.arkesel.com/api/v2/sms/send"
    api_key = config("SMS_API_KEY")
    
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    body = {
        "sender": "Hello world",
        "message":message,
        "recipients": recipients,
        "sandbox": True
    }
    
    try:
        response = requests.post(url=url,headers=headers, json=body)
        response.raise_for_status()
        print(response.json())
        return response.json().get("status", False)
    except requests.RequestException as e:
        print(f"Error sending SMS: {e}")
        return False
    
def check_sms_balance():
    """
    Check the SMS balance of the account.
    
    Returns:
        dict: A dictionary containing balance details if successful, None otherwise.
    """
    api_url = "https://sms.arkesel.com/api/v2/clients/balance-details"
    api_key = config("SMS_API_KEY")
    
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers) 
        response.raise_for_status()
        print(response.json())
        return response.json().get("status", None)
    except requests.RequestException as e:
        print(f"Error sending SMS: {e}")
        return False
    
def charge_mobile_money(amount:int, phone_number:str, provider:str, email:str=None, metadata:dict=None):
    """
    Debit the account by the specified amount via mobile money.
    
    Args:
        amount (float): The amount to debit.
        
    Returns:
        bool: True if the transaction was successful, False otherwise.
    """
    url = "https://api.AnyPay.co/charge"
    api_key = config("AnyPay_SECRET_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "email": email or "customer@osx.com",
        "amount": int(amount*100),  # AnyPay expects amount in the smallest currency unit (pesewa)
        "currency": "GHS",
        "mobile_money": {
            "phone": phone_number,
            "provider": provider
        },
        "metadata": metadata
        # "reference": id # uncomment to provide your own reference
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code == 401:
            logger.error("AnyPay API key Invalid: %s", response.json())
        elif response.status_code == 400:
            logger.error("AnyPay Validation error: %s", response.json())
        
        raise APIException("internal error") # AnyPay error
    except requests.exceptions.Timeout:
        logger.error("AnyPay request timed out.")
        raise APIException("internal error")
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to AnyPay.")
        raise APIException("internal error")
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        raise APIException("An unexpected error occured.")

    data = response.json()

    # If status is False in AnyPay response, treat as ValidationError
    if not data.get("status", False):
        logger.error("AnyPay returned an error: %s", data)
        raise ValidationError(data.get("message", "Unknown error"))

    return data

def send_email(subject, template_name, context, recipient_list):
    """
    Generic function to send templated HTML emails.
    """
    
    # html_message = render_to_string(template_name, context)
    html_message = get_template(template_name).render(context)
    send_mail(
        subject=subject,
        message="",
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
    )

