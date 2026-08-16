import time, requests, os
from typing import Optional, Dict, Any
from seedance import GenerationRequest, TaskResult, SeedanceClient
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("SEEDANCE_API_KEY")

if not API_KEY:
    raise ValueError("API key not found. Please check your .env file")

Base_URL = "https://api.piapi.ai"
prmpt = "Generate a video of a drone flying through a neon city"

HEADERS = {
    "Authorization":f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
