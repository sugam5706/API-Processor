"""
Configuration and constants for the API Processor system
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Queue Topics
REQUEST_TOPIC = "requests"
RESPONSE_TOPIC = "responses"

# Cache Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = 86400  # 24 hours

# Server Configuration
API_SERVER_PORT = int(os.getenv("API_SERVER_PORT", 8000))
API_SERVER_HOST = os.getenv("API_SERVER_HOST", "0.0.0.0")

# Processor Configuration
PROCESSOR_POLL_INTERVAL = int(os.getenv("PROCESSOR_POLL_INTERVAL", 1))
PROCESSOR_TIMEOUT = int(os.getenv("PROCESSOR_TIMEOUT", 300))  # 5 minutes

# Response Handler Configuration
HANDLER_POLL_INTERVAL = int(os.getenv("HANDLER_POLL_INTERVAL", 1))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Processing Configuration
DEFAULT_PROCESSING_TIME = 2  # seconds for simulation
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1 MB
