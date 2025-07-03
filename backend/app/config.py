import os
from dotenv import load_dotenv

# Resolve project root (D:\ai-appointment-booking-agent)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

class Config:
    GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
    SERVICE_ACCOUNT_FILE = os.path.abspath(
        os.path.join(project_root, os.getenv("SERVICE_ACCOUNT_FILE", "backend/credentials/service_account.json"))
    )
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_CALENDAR_ID:
            missing.append("GOOGLE_CALENDAR_ID")
        if not cls.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if not os.path.exists(cls.SERVICE_ACCOUNT_FILE):
            missing.append(f"SERVICE_ACCOUNT_FILE at {cls.SERVICE_ACCOUNT_FILE}")
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True