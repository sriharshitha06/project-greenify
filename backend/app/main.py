import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base, SessionLocal
from .routers import auth, carbon, verify, recommendations, gamification
from .routers.gamification import seed_badges

app = FastAPI(
    title="Greenify API",
    description="Backend service for Greenify carbon tracking, ML estimation, CV verification, and RAG advising.",
    version="1.0.0"
)

# Enable CORS for frontend integration (supports loading via local server or file://)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Seed badges if they don't exist
db = SessionLocal()
try:
    seed_badges(db)
finally:
    db.close()

# Mount uploads directory to serve verified images
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount frontend directory if we want to serve frontend directly from backend, 
# but we will run frontend statically or serve it. Mounting is great for unified running.
# Let's keep backend and frontend modular.

# Include API Routers
app.include_router(auth.router)
app.include_router(carbon.router)
app.include_router(verify.router)
app.include_router(recommendations.router)
app.include_router(gamification.router)

from fastapi.responses import RedirectResponse

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "message": "Welcome to Greenify API!",
        "documentation": "/docs"
    }

@app.get("/")
def read_root():
    return RedirectResponse(url="/login.html")

# Mount root directory to serve HTML pages and CSS/JS assets
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
app.mount("/", StaticFiles(directory=ROOT_DIR, html=True), name="static")
