from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

try:
    from starlette.middleware.proxy_headers import (
        ProxyHeadersMiddleware,  # type: ignore
    )
    _HAS_PROXY_MW = True
except Exception:  # pragma: no cover
    ProxyHeadersMiddleware = None  # type: ignore
    _HAS_PROXY_MW = False
from fastapi.responses import JSONResponse, ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from app.auth.routes import auth_router
from app.fixtures.routes import fixtures_router
from app.logger import logger
from app.manager.routes import manager_router
from app.player.routes import player_router
from app.scoring.routes import scoring_router
from app.settings import settings
from app.team.routes import team_router
from app.utils.db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize and seed the database on startup
    create_db_and_tables()
    try:
        from app.scripts.seed_db import main as seed_main
        seed_main()
    except Exception as _seed_err:  # pragma: no cover
        # Seeding errors should not prevent the app from starting in dev
        logger.warning(f"Seeding skipped or failed: {_seed_err!s}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A production ready boilerplate for FastAPI",
    version=settings.VERSION,
    root_path=settings.ROOT_PATH,
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional middlewares
if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.allowed_hosts and settings.allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

if settings.USE_PROXY_HEADERS and _HAS_PROXY_MW:
    app.add_middleware(ProxyHeadersMiddleware)  # type: ignore[arg-type]

if settings.ENABLE_HTTPS_REDIRECT:
    app.add_middleware(HTTPSRedirectMiddleware)


router = APIRouter()


@router.get("/healthz")
def healthz():
    """
    Public health check endpoint.
    """
    logger.info("Health check endpoint was called.")
    return {"status": "ok"}


app.include_router(router, prefix="")
app.include_router(auth_router, prefix=f"{settings.API_V1_PREFIX}/auth")
app.include_router(player_router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(team_router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(manager_router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(fixtures_router, prefix=f"{settings.API_V1_PREFIX}")
app.include_router(scoring_router, prefix=f"{settings.API_V1_PREFIX}")


# Structured error handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        f"Validation error on {request.method} {request.url}: {exc.errors()}"
    )
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status_code": HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Validation error",
            "error": "UnprocessableEntity",
            "data": None,
            "meta": {"detail": exc.errors()},
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException on {request.method} {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
            "error": exc.__class__.__name__,
            "data": None,
            "meta": None,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url}: {exc!s}")
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "message": "Internal server error",
            "error": exc.__class__.__name__,
            "data": None,
            "meta": None,
        },
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = str(request.url.path)
        logger.bind(path=path, method=request.method).info("Request started")
        response: Response = await call_next(request)
        logger.bind(path=path, status_code=response.status_code).info(
            "Request completed"
        )
        return response


app.add_middleware(RequestLoggingMiddleware)

