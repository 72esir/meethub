class AuthError(Exception):
    pass


class InvalidCredentialsError(AuthError):
    pass


class UserAlreadyExistsError(AuthError):
    pass


class RefreshTokenError(AuthError):
    pass


class UserNotFoundError(AuthError):
    pass
