import os
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(dotenv_path=os.path.join(project_root, ".env"))

service_account_file = os.path.abspath(
    os.path.join(project_root, os.getenv("SERVICE_ACCOUNT_FILE", "backend/credentials/service_account.json"))
)

print("Project Root:", project_root)
print("GOOGLE_CALENDAR_ID:", os.getenv("GOOGLE_CALENDAR_ID"))
print("LLM_API_KEY:", os.getenv("LLM_API_KEY"))
print("SERVICE_ACCOUNT_FILE:", service_account_file)
print("File exists:", os.path.exists(service_account_file))