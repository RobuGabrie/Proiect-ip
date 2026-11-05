class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def unauthorized(message: str = "Autentifică-te din nou cu contul Google.") -> ApiError:
    return ApiError(401, "NEAUTENTIFICAT", message)


def invalid(message: str) -> ApiError:
    return ApiError(400, "DATE_INVALIDE", message)


def forbidden(message: str = "Nu ai drepturi pentru această operație.") -> ApiError:
    return ApiError(403, "ACCES_INTERZIS", message)


def not_found(message: str = "Elementul cerut nu există.") -> ApiError:
    return ApiError(404, "NEGASIT", message)


def conflict(code: str, message: str) -> ApiError:
    return ApiError(409, code, message)


def business_rule(code: str, message: str) -> ApiError:
    return ApiError(422, code, message)


def invalid_transition(message: str = "Operația nu este permisă în starea curentă a cererii.") -> ApiError:
    return conflict("TRANZITIE_INTERZISA", message)
