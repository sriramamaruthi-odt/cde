from rest_framework.permissions import BasePermission

from users.models import UserProfile


class IsResolvedCaller(BasePermission):
    """Baseline for every tool-assignment endpoint: the caller must have
    resolved to a real UserProfile via authentication. Role/organization
    checks beyond this are done per-action in the views, since they
    depend on the target of the request (e.g. the role of the profile
    being granted a tool), not just the caller.
    """

    message = "A valid X-Acting-As-User-Id header is required."

    def has_permission(self, request, view):
        return isinstance(request.user, UserProfile)
