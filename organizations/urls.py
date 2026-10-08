from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("tools/", views.ToolListView.as_view(), name="tool-list"),
    path(
        "organizations/<int:organization_id>/tools/",
        views.OrganizationToolListCreateView.as_view(),
        name="organization-tool-list",
    ),
    path(
        "organizations/<int:organization_id>/tools/<int:tool_id>/",
        views.OrganizationToolDetailView.as_view(),
        name="organization-tool-detail",
    ),
    path(
        "profiles/<int:profile_id>/tools/",
        views.UserToolView.as_view(),
        name="profile-tool-list",
    ),
]
