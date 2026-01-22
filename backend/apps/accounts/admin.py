from django.contrib import admin
from .models import User, PublicProfile, PrivateProfile


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    list_display = ("email", "role", "is_banned", "is_staff")
    search_fields = ("email",)
    list_filter = ("role", "is_banned")


admin.site.register(PublicProfile)
admin.site.register(PrivateProfile)
