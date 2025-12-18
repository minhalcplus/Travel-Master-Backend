from contextlib import asynccontextmanager


from routes import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from .database import create_tables,create_db_if_not_exists
from core.config.helper import clearPyCache,create_and_mount_initial_dirs
from core.app.env import BASE_DIR,settings
from pathlib import Path
from travel.routes import router as travel_router
from event.routes import router as event_router

from .rate_limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_if_not_exists()
    create_tables()
    create_and_mount_initial_dirs(app=app)
    yield
    clearPyCache()
    


app = FastAPI(
    title="Travel Master",
    description="Discrip Of App",
    summary="Summary",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=settings.ALLOW_CREDENTIALS,
    allow_methods=settings.ALLOW_METHODS,
    allow_headers=settings.ALLOW_HEADERS,
)






app.include_router(router,prefix="/api")
app.include_router(travel_router, prefix="/api")
app.include_router(event_router, prefix="/api")

@app.get("/{full_path:path}",include_in_schema=False)
def root_route():
  static_path=Path("public/index.html")
  if not static_path.exists():
    return {"error":"React app not build"}
  return FileResponse(static_path)