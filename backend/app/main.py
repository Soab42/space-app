import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .db import init_db
from .routers import publications, qa
from .routers.search import router as search_router
from .routers.analytics import router as analytics_router
from .routers.graph import router as graph_router
from .routers import categories
import logging

settings = get_settings()

logging.basicConfig(level=logging.DEBUG)
logging.debug("Starting application...")

app = FastAPI(title="NASA Bioscience Dashboard API", version="0.2.0", debug=True)

origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

app.include_router(publications.router)
app.include_router(qa.router)
app.include_router(search_router)
app.include_router(analytics_router)
app.include_router(graph_router)
app.include_router(categories.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
