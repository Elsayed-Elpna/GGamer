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
# Phone Number Validator (Egyptian Format)
# ============================

phone_regex = RegexValidator(
    regex=r'^(010|011|012|015)\d{8}$',
    message="Phone number must be a valid Egyptian mobile number (e.g., 01012345678)"
)


# ============================
# National ID Validator (Egyptian Format)
# ============================

national_id_regex = RegexValidator(
    regex=r'^\d{14}$',
    message="National ID must be exactly 14 digits"
)


def validate_egyptian_national_id(value):
    """
    Validates Egyptian National ID format and checksum.
    Format: 14 digits (YYMMDDSSGGGGG)
    - YY: Birth year
    - MM: Birth month (01-12)
    - DD: Birth day (01-31)
    - SS: Governorate code
    - GGGG: Sequence number
    - Last digit: Gender (odd=male, even=female)
    """
    if not re.match(r'^\d{14}$', value):
        raise ValidationError("National ID must be exactly 14 digits")
    
    # Validate month
    month = int(value[3:5])
    if month < 1 or month > 12:
        raise ValidationError("Invalid month in National ID")
    
    # Validate day
    day = int(value[5:7])
    if day < 1 or day > 31:
        raise ValidationError("Invalid day in National ID")
    
    return value


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
