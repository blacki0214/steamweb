from fastapi import FastAPI

from app.routers import games, recommendations, reviews, search, users

app = FastAPI(title="Indie Game API", version="0.1.0")

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(games.router, prefix="/games", tags=["games"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
app.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
