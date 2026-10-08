from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("otp/request/", views.RequestOTPView.as_view(), name="otp-request"),
    path("otp/verify/", views.VerifyOTPView.as_view(), name="otp-verify"),
    path("profiles/", views.UserProfileCreateView.as_view(), name="profile-create"),
]
