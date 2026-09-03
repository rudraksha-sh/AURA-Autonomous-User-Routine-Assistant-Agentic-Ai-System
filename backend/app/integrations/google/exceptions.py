class GoogleOAuthError(Exception):
    """Base exception for Google OAuth failures."""


class GoogleOAuthStateError(GoogleOAuthError):
    """Raised when an OAuth state value is invalid or expired."""