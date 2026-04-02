from fastapi import FastAPI
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()


app = FastAPI()

@app.get("/config")
def get_config():
    app_name = os.getenv("APP_NAME")
    admin_email = os.getenv("ADMIN_EMAIL")
    environment = os.getenv("ENVIRONMENT")


    return {
        "app_name": app_name,
        "admin_email": admin_email,
        "environment": environment
    }
