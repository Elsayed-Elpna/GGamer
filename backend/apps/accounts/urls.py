from django.urls import path
from .views import *

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("register/", register_view, name="register"),
    
    # User profile
    path("me/", me_view, name="me"),
    path("avatar/", upload_avatar, name="avatar"),
    
    # Public profile
    path("public-profile/", update_public_profile, name="public_profile"),
    
    # Private profile (KYC)
    path("private-profile/", private_profile_view, name="private_profile"),
    
    # Admin actions
    path("ban/<int:user_id>/", ban_user, name="ban_user"),
    path("unban/<int:user_id>/", unban_user, name="unban_user"),
]

