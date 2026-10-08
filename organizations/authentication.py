from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from users.models import UserProfile

ACTING_AS_HEADER = "HTTP_X_ACTING_AS_USER_ID"


class ActingAsHeaderAuthentication(BaseAuthentication):
    """Resolves the caller from an X-Acting-As-User-Id header.

    STOPGAP: the header is trusted as-is, with no proof the request is
    really from that user - there is no login/token system yet. Replace
    with real authentication before this is exposed beyond local
    development; nothing downstream should need to change when it is,
    since views/permissions only ever read `request.user`.
    """

    def authenticate(self, request):
        user_id = request.META.get(ACTING_AS_HEADER)
        if not user_id:
            return None
        try:
            profile = UserProfile.objects.get(pk=user_id)
        except (UserProfile.DoesNotExist, ValueError, TypeError):
            raise AuthenticationFailed("Unknown X-Acting-As-User-Id.")
        return (profile, None)

    def authenticate_header(self, request):
        return "ActingAs"
