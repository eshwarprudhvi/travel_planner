import os 
from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
QRAIL_API_KEY = os.getenv("QRAIL_API_KEY")
RAILRADAR_API_KEY = os.getenv("RAILRADAR_API_KEY")


if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables.")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the environment variables.")
if not OPENROUTESERVICE_API_KEY:
    raise ValueError("OPENROUTESERVICE_API_KEY is not set in the environment variables.")

