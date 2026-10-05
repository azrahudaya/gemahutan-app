from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware_limits import PembatasLaju
from app.routers import audit as audit_router
from app.routers import auth as auth_router
from app.routers import batches as batches_router
from app.routers import devices as devices_router
from app.routers import exports as exports_router
from app.routers import jobs_stream as jobs_stream_router
from app.routers import model as model_router
from app.routers import recordings as recordings_router
from app.routers import simulasi as simulasi_router
from app.routers import sites as sites_router
from app.routers import spectrogram as spectrogram_router
from app.routers import users as users_router
from app.routers.detections import detections_router, jobs_router, species_router, stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    is_production = settings.environment.strip().lower() in {"production", "prod"}

    problems = settings.production_problems() if is_production else []
    if problems:
        raise RuntimeError(
            "Konfigurasi produksi belum aman, aplikasi sengaja tidak dijalankan: "
            + "; ".join(problems)
            + ". Isi nilai sungguhan di .env atau deploy/.env.prod, lihat docs/DEPLOY.md."
        )

    docs_enabled = settings.enable_docs and not is_production
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pembatas laju dipasang sebagai middleware ASGI murni, bukan
    # BaseHTTPMiddleware, supaya endpoint SSE di /api/v1/jobs/stream tidak
    # menggantung karena badan responsnya dibungkus.
    app.add_middleware(PembatasLaju, aktif=settings.rate_limit_enabled)

    @app.get("/healthz")
    async def healthz():
        import httpx
        import redis.asyncio as aioredis
        from sqlalchemy import text

        from app.database import async_engine

        services = {}

        # DB check
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            services["db"] = "up"
        except Exception:
            services["db"] = "down"

        # Redis check
        try:
            r = aioredis.from_url(settings.redis_url)
            await r.ping()
            await r.aclose()
            services["redis"] = "up"
        except Exception:
            services["redis"] = "down"

        # MinIO check
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.s3_endpoint}/minio/health/live")
                services["storage"] = "up" if resp.status_code == 200 else "down"
        except Exception:
            services["storage"] = "down"

        # Status model dibaca dari artefak nyata, bukan konstanta.
        from app.services.model_status import get_inference_status
        model_status = await get_inference_status()
        services["model"] = model_status["state"]

        required = ["db", "redis", "storage"]
        all_up = all(services[k] == "up" for k in required)
        status_code = 200 if all_up else 503

        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ok" if all_up else "degraded",
                "version": settings.app_version,
                "services": services,
                "services_required": required,
                "model_detail": model_status["detail"],
            },
        )

    @app.get("/readyz")
    async def readyz():
        return {"status": "ready"}

    # Wire routers
    app.include_router(auth_router.router)
    app.include_router(recordings_router.router)
    app.include_router(simulasi_router.router)
    app.include_router(model_router.router)
    app.include_router(detections_router)
    app.include_router(species_router)
    app.include_router(jobs_router)
    app.include_router(stats_router)
    app.include_router(sites_router.router)
    app.include_router(exports_router.router)
    app.include_router(spectrogram_router.router)
    app.include_router(devices_router.router)
    app.include_router(users_router.router)
    app.include_router(batches_router.router)
    app.include_router(jobs_stream_router.router)
    app.include_router(audit_router.router)

    # Protected /me endpoint
    from fastapi import Depends

    from app.deps import get_current_user
    from app.schemas.auth import UserResponse

    @app.get("/api/v1/me", response_model=UserResponse)
    async def me(current_user=Depends(get_current_user)):
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            role=current_user.role.value,
            created_at=current_user.created_at.isoformat(),
        )

    return app


app = create_app()
