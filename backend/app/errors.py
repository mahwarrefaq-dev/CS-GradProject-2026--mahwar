"""Unified error body {code, message, fields} (API_Spec, sheet Conventions; Security_Design, sheet Errors)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    """Raised by services and routers; converted to a JSON error response."""

    def __init__(self, status_code: int, code: str, message: str, fields: list[dict] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields or []


def error_body(code: str, message: str, fields: list[dict] | None = None) -> dict:
    return {"code": code, "message": message, "fields": fields or []}


# Arabic messages for the generic Pydantic validation errors (NFR-06).
_PYDANTIC_MESSAGES = {
    "missing": "هذا الحقل مطلوب",
    "string_too_short": "القيمة أقصر من الحد الأدنى ({min_length} أحرف)",
    "string_too_long": "القيمة أطول من الحد الأقصى ({max_length} حرفًا)",
    "string_pattern_mismatch": "القيمة لا تطابق الصيغة المسموحة",
    "literal_error": "القيمة غير مسموحة؛ القيم المسموحة: {expected}",
    "enum": "القيمة غير مسموحة؛ القيم المسموحة: {expected}",
    "date_from_datetime_parsing": "صيغة التاريخ غير صحيحة (المطلوب YYYY-MM-DD)",
    "date_parsing": "صيغة التاريخ غير صحيحة (المطلوب YYYY-MM-DD)",
    "date_type": "صيغة التاريخ غير صحيحة (المطلوب YYYY-MM-DD)",
    "int_parsing": "يجب أن تكون القيمة عددًا صحيحًا",
    "int_type": "يجب أن تكون القيمة عددًا صحيحًا",
    "greater_than": "يجب أن تكون القيمة أكبر من {gt}",
    "greater_than_equal": "يجب ألا تقل القيمة عن {ge}",
    "less_than_equal": "يجب ألا تزيد القيمة على {le}",
    "bool_parsing": "يجب أن تكون القيمة true أو false",
    "json_invalid": "صيغة JSON غير صحيحة",
}


def _field_message(err: dict) -> str:
    if err["type"] == "value_error":
        # Custom validators raise ValueError with an Arabic message.
        msg = err.get("msg", "")
        return msg.removeprefix("Value error, ")
    template = _PYDANTIC_MESSAGES.get(err["type"])
    if template is None:
        return "قيمة غير صالحة"
    try:
        return template.format(**(err.get("ctx") or {}))
    except (KeyError, IndexError):
        return template


def _field_name(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    return ".".join(parts) or "body"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, exc.fields))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [{"field": _field_name(tuple(e["loc"])), "message": _field_message(e)} for e in exc.errors()]
        return JSONResponse(status_code=422,
                            content=error_body("VALIDATION_ERROR", "تحقق من الحقول المظللة", fields))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        messages = {404: ("NOT_FOUND", "العنصر غير موجود"), 405: ("METHOD_NOT_ALLOWED", "الطريقة غير مسموحة")}
        code, message = messages.get(exc.status_code, ("HTTP_ERROR", str(exc.detail)))
        if isinstance(exc.detail, str) and exc.status_code not in messages:
            message = exc.detail
        return JSONResponse(status_code=exc.status_code, content=error_body(code, message))
