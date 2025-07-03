from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.config import Config
from app.logging_config import logger

# Create FastAPI app
app = FastAPI(
    title="AI Appointment Booking Agent",
    description="An AI-powered appointment booking system using Google Calendar",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "AI Appointment Booking Agent API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        Config.validate()
        return {"status": "healthy", "message": "All systems operational"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)