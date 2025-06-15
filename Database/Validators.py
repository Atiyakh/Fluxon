import re
import validators
import phonenumbers
import ipaddress
from email_validator import validate_email as validate_email_, EmailNotValidError
from dateutil import parser
import mimetypes
from creditcard import CreditCard

def validate_email(email: str, check_deliverability=False):
    """Validate an email address."""
    try:
        validate_email_(email, check_deliverability=check_deliverability)
        return True
    except:
        return False

def validate_password(password: str, min_length=8, require_upper=True, require_special=True):
    """Check if the password meets strength requirements."""
    if len(password) < min_length:
        return False # password must be at least {min_length} characters long
    if require_upper and not re.search(r'[A-Z]', password):
        return False # password must contain at least one uppercase letter
    if require_special and not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
        return False # password must contain at least one special character
    return True

def validate_username(username: str):
    """Validate username (only alphanumeric and underscore)."""
    if re.match(r'^[a-zA-Z0-9_]+$', username):
        return True
    return False

def validate_phone(phone: str, region="US"):
    """Validate phone number format using the phonenumbers library."""
    try:
        number = phonenumbers.parse(phone, region)
        if phonenumbers.is_valid_number(number):
            return True
        return False
    except phonenumbers.NumberParseException:
        return False

def validate_url(url: str):
    """Validate a URL format."""
    if validators.url(url):
        return True
    return False

def validate_mime_type(filename: str):
    """Validate MIME type using Python's mimetypes module."""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return True
    return False

def validate_ip(ip: str):
    """Validate IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def validate_date(date_str: str):
    """Validate date format using dateutil."""
    try:
        parsed_date = parser.parse(date_str)
        return True
    except ValueError:
        return False

def validate_credit_card(card_number: str):
    """Validate credit card number using Luhn algorithm."""
    if CreditCard(card_number).is_valid:
        return True
    return False
