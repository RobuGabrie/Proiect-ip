class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def unauthorized(message: str = "Autentifică-te din nou cu contul Google.") -> ApiError:
    return ApiError(401, "NEAUTENTIFICAT", message)
