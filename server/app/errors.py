from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_DEFAULT_DETAIL = {
    400: "请求有误",
    401: "请先登录",
    403: "没有权限",
    404: "接口不存在",
    405: "请求方法不支持",
}


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detail)


def _field_name(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(parts)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        field = _field_name(tuple(errors[0].get("loc", ()))) if errors else ""
        detail = f"请求参数有误：{field}" if field else "请求参数有误"
        return JSONResponse(status_code=400, content={"detail": detail})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if not isinstance(detail, str) or detail in ("Not Found", "Method Not Allowed", "Unauthorized", "Forbidden", "Bad Request"):
            detail = _DEFAULT_DETAIL.get(exc.status_code, "请求失败")
        return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=getattr(exc, "headers", None))
