"""
Centralized validators for the marketplace application.
Includes validators for phone numbers, national IDs, and file uploads.
"""
import re
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
import magic
import os


# ============================
# Phone Number Validator (International Format)
# ============================

phone_regex = RegexValidator(
    regex=r'^\+?[1-9]\d{7,14}$',
    message="Phone number must be in international format (e.g., +1234567890)"
)


def validate_international_phone_number(value):
    """
    Validates international phone number format.
    Accepts formats with country code: +1234567890, +447700900123, etc.
    Length: 8-15 digits (excluding + sign)
    SECURITY: Rejects non-ASCII to prevent unicode bypass attacks.
    """
    # Remove spaces, dashes, and parentheses
    cleaned = re.sub(r'[\s\-()]', '', value)
    
    # SECURITY: Reject non-ASCII characters to prevent unicode bypass
    if not cleaned.isascii():
        raise ValidationError(
            "Phone number must contain only ASCII characters"
        )
    
    # Check if it matches international phone pattern
    if not re.match(r'^\+?[1-9]\d{7,14}$', cleaned):
        raise ValidationError(
            "Phone number must be in international format with country code (e.g., +1234567890, +447700900123)"
        )
    
    # SECURITY: Return cleaned value, not original
    return cleaned


# Backward compatibility alias
validate_egyptian_phone_number = validate_international_phone_number



# ============================
# National ID Validator (International Format)
# ============================

national_id_regex = RegexValidator(
    regex=r'^[A-Z0-9\-]{5,20}$',
    message="National ID must be 5-20 alphanumeric characters"
)


def validate_national_id(value):
    """
    Validates National ID or Passport Number format.
    Accepts alphanumeric IDs from any country.
    Format: 5-20 characters (letters, numbers, hyphens allowed)
    SECURITY: Returns normalized (uppercase) value to prevent case sensitivity bypass.
    Examples:
    - Egyptian ID: 12345678901234 (14 digits)
    - US Passport: A12345678 (9 chars)
    - UK Passport: AB1234567 (9 chars)
    - Generic ID: ABC-123-456
    """
    # Remove spaces and normalize to uppercase
    cleaned = value.strip().upper()
    
    # Check length
    if len(cleaned) < 5 or len(cleaned) > 20:
        raise ValidationError("National ID must be between 5 and 20 characters")
    
    # Check if it contains only valid characters
    if not re.match(r'^[A-Z0-9\-]+$', cleaned):
        raise ValidationError("National ID must contain only letters, numbers, and hyphens")
    
    # SECURITY: Return normalized value to prevent case bypass
    # This ensures hashing is consistent and duplicates are detected
    return cleaned


# Backward compatibility alias
validate_egyptian_national_id = validate_national_id


# ============================
# File Upload Validators
# ============================

@deconstructible
class FileSizeValidator:
    """
    Validates that uploaded file size is within acceptable limits.
    """
    def __init__(self, max_size_mb=5):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def __call__(self, value):
        if value.size > self.max_size_bytes:
            raise ValidationError(
                f"File size must not exceed {self.max_size_mb}MB. "
                f"Current size: {value.size / (1024 * 1024):.2f}MB"
            )
    
    def __eq__(self, other):
        return isinstance(other, FileSizeValidator) and self.max_size_mb == other.max_size_mb


@deconstructible
class FileTypeValidator:
    """
    Validates file type using python-magic (checks actual file content, not just extension).
    """
    def __init__(self, allowed_types=None):
        if allowed_types is None:
            # Default: common image types
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        self.allowed_types = allowed_types
    
    def __call__(self, value):
        # Read file content to determine actual MIME type
        file_mime = magic.from_buffer(value.read(2048), mime=True)
        value.seek(0)  # Reset file pointer
        
        if file_mime not in self.allowed_types:
            raise ValidationError(
                f"File type '{file_mime}' is not allowed. "
                f"Allowed types: {', '.join(self.allowed_types)}"
            )
    
    def __eq__(self, other):
        return isinstance(other, FileTypeValidator) and self.allowed_types == other.allowed_types


@deconstructible
class ImageDimensionValidator:
    """
    Validates image dimensions (width and height).
    """
    def __init__(self, max_width=2048, max_height=2048, min_width=100, min_height=100):
        self.max_width = max_width
        self.max_height = max_height
        self.min_width = min_width
        self.min_height = min_height
    
    def __call__(self, value):
        from PIL import Image
        
        try:
            img = Image.open(value)
            width, height = img.size
            
            if width > self.max_width or height > self.max_height:
                raise ValidationError(
                    f"Image dimensions too large. Max: {self.max_width}x{self.max_height}px, "
                    f"Got: {width}x{height}px"
                )
            
            if width < self.min_width or height < self.min_height:
                raise ValidationError(
                    f"Image dimensions too small. Min: {self.min_width}x{self.min_height}px, "
                    f"Got: {width}x{height}px"
                )
        except Exception as e:
            raise ValidationError(f"Invalid image file: {str(e)}")
        finally:
            value.seek(0)  # Reset file pointer
    
    def __eq__(self, other):
        return (isinstance(other, ImageDimensionValidator) and 
                self.max_width == other.max_width and 
                self.max_height == other.max_height and
                self.min_width == other.min_width and
                self.min_height == other.min_height)


def validate_safe_filename(value):
    """
    Validates that filename doesn't contain dangerous characters or path traversal attempts.
    """
    filename = os.path.basename(value.name)
    
    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValidationError("Filename contains invalid characters")
    
    # Check for dangerous extensions
    dangerous_extensions = [
        '.exe', '.bat', '.cmd', '.sh', '.php', '.asp', '.aspx', 
        '.jsp', '.js', '.py', '.rb', '.pl', '.cgi'
    ]
    
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext in dangerous_extensions:
        raise ValidationError(f"File extension '{file_ext}' is not allowed")
    
    return value


# ============================
# Username Validator
# ============================

username_regex = RegexValidator(
    regex=r'^[a-zA-Z0-9_-]{3,50}$',
    message="Username must be 3-50 characters and contain only letters, numbers, underscores, and hyphens"
)


def validate_username_not_email(value):
    """
    Ensures username doesn't look like an email address.
    """
    if '@' in value:
        raise ValidationError("Username cannot contain '@' symbol")
    return value
