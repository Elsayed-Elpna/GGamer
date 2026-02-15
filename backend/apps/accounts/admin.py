from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from .models import User, PublicProfile, PrivateProfile


# ============================
# User Admin Forms
# ============================

class UserCreationForm(forms.ModelForm):
    """Form for creating new users in admin."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'role')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Form for updating users in admin."""
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change the password using "
            "<a href=\"../password/\">this form</a>."
        ),
    )

    class Meta:
        model = User
        fields = '__all__'


# ============================
# User Admin
# ============================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin for User model.
    Includes proper password handling and security controls.
    """
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        'email',
        'role',
        'is_active',
        'is_banned',
        'email_verified',
        'is_staff',
        'date_joined'
    )
    
    list_filter = (
        'role',
        'is_active',
        'is_banned',
        'email_verified',
        'is_staff',
        'is_superuser'
    )
    
    search_fields = ('email',)
    
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('avatar',)}),
        ('Permissions', {
            'fields': (
                'role',
                'is_active',
                'is_staff',
                'is_superuser',
                'email_verified',
                'groups',
                'user_permissions'
            ),
        }),
        ('Ban info', {
            'fields': ('is_banned', 'ban_reason', 'banned_at'),
            'classes': ('collapse',),
        }),
        ('Important dates', {
            'fields': ('date_joined', 'updated_at', 'last_login'),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'role', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('date_joined', 'updated_at', 'last_login', 'banned_at')

    def save_model(self, request, obj, form, change):
        """
        Prevent banning superusers via admin panel.
        """
        if obj.is_superuser and obj.is_banned:
            from django.contrib import messages
            messages.error(request, "Cannot ban superuser accounts!")
            obj.is_banned = False
            obj.ban_reason = None
            obj.banned_at = None
        
        super().save_model(request, obj, form, change)


# ============================
# Public Profile Admin
# ============================

@admin.register(PublicProfile)
class PublicProfileAdmin(admin.ModelAdmin):
    """Admin for public profiles."""
    
    list_display = ('username', 'user', 'rating', 'completed_orders', 'created_at')
    search_fields = ('username', 'user__email')
    list_filter = ('created_at',)
    readonly_fields = ('rating', 'completed_orders', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('user', 'username', 'bio')}),
        ('Reputation', {'fields': ('rating', 'completed_orders')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


# ============================
# Private Profile Admin
# ============================

@admin.register(PrivateProfile)
class PrivateProfileAdmin(admin.ModelAdmin):
    """
    Admin for private profiles.
    Displays masked sensitive data for security.
    """
    
    list_display = (
        'user',
        'phone_number_masked',
        'national_id_masked',
        'phone_verified',
        'national_id_verified'
    )
    
    search_fields = ('user__email', 'phone_number', 'national_id')
    list_filter = ('phone_verified', 'national_id_verified', 'created_at')
    
    readonly_fields = (
        'phone_verified',
        'national_id_verified',
        'created_at',
        'updated_at',
        'phone_number_masked',
        'national_id_masked'
    )
    
    fieldsets = (
        (None, {'fields': ('user',)}),
        ('PII Data (Sensitive)', {
            'fields': ('phone_number', 'national_id'),
            'classes': ('collapse',),
        }),
        ('Masked Display', {
            'fields': ('phone_number_masked', 'national_id_masked'),
        }),
        ('Verification Status', {
            'fields': ('phone_verified', 'national_id_verified'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def phone_number_masked(self, obj):
        """Display masked phone number."""
        if obj.phone_number:
            return obj.phone_number[:7] + "****"
        return "-"
    phone_number_masked.short_description = "Phone (Masked)"

    def national_id_masked(self, obj):
        """Display masked national ID."""
        if obj.national_id:
            return obj.national_id[:5] + "*********"
        return "-"
    national_id_masked.short_description = "National ID (Masked)"

