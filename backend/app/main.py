from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ASCENT API",
    description="AI-Powered M.Tech Admission Prediction and Recommendation System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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