from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import connect_db, close_db
from app.routes import nits
from app.routes import auth                  

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(
    title="ASCENT API",
    description="AI-Powered M.Tech Admission Prediction and Recommendation System",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nits.router, prefix="/api/v1", tags=["NITs"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])  

@app.get("/")
def root():
    return {
        "project": "ASCENT",
        "status": "running",
        "message": "AI-Powered M.Tech Admission Recommendation System"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}