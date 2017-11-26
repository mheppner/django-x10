"""Custom authentication drivers for rest framework."""
from rest_framework.authentication import TokenAuthentication

from .models import PersistentToken


class PersistentTokenAuthentication(TokenAuthentication):
    """Uses base authentication driver, looking for PToken headers."""

    model = PersistentToken
    keyword = 'PToken'
