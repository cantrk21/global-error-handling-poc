"""Exception -> HTTP dönüşümünün tek merkezi."""
import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from .domain import DomainError, InsufficientStock, ProductNotFound

logger = logging.getLogger("poc.errors")


def error_response(request, status, code, message, details=None, headers=None):
    request_id = request.state.request_id
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message,
                           "details": details or [], "request_id": request_id}},
        headers={**(headers or {}), "X-Request-ID": request_id},
    )


def register_handlers(app: FastAPI):
    @app.exception_handler(DomainError)
    async def domain_handler(request: Request, exc: DomainError):
        mapping = {
            ProductNotFound: (404, "PRODUCT_NOT_FOUND", "Ürün bulunamadı."),
            InsufficientStock: (409, "INSUFFICIENT_STOCK", "İstenen miktar stoktan fazla."),
        }
        spec = mapping.get(type(exc))
        if spec is None:
            return await unexpected_handler(request, exc)
        status, code, message = spec
        logger.info("request_id=%s code=%s", request.state.request_id, code)
        return error_response(request, status, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        # input / body / ctx geri gönderilmez: parola vb. değerleri sızdırmayalım.
        details = [{"field": ".".join(map(str, e["loc"])), "type": e["type"]}
                   for e in exc.errors()]
        return error_response(request, 422, "VALIDATION_ERROR",
                              "İstek alanlarını kontrol et.", details)

    @app.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException):
        # Starlette taban sınıfı: framework 404/405 hataları da kapsanır.
        message = HTTPStatus(exc.status_code).phrase
        return error_response(request, exc.status_code, f"HTTP_{exc.status_code}",
                              message, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unexpected_handler(request: Request, exc: Exception):
        logger.error("Unhandled error request_id=%s", request.state.request_id,
                     exc_info=(type(exc), exc, exc.__traceback__))
        return error_response(request, 500, "INTERNAL_ERROR",
                              "Beklenmeyen bir hata oluştu. Destek için istek kimliğini paylaş.")
