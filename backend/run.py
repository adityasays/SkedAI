import uvicorn
import sys
import os

backend_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )