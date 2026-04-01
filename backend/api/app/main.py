from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.session import init_db
from app.routers import auth, feedback, games, recommendations, reports, reviews, search, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Indie Game API", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(games.router, prefix="/api/v1/games", tags=["games"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(reviews.router, prefix="/api/v1/reviews", tags=["reviews"])
app.include_router(
    recommendations.router,
    prefix="/api/v1/recommendations",
    tags=["recommendations"],
)
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
