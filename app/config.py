import os


class Config:
    # "memory" for local development, "apex" to forward data to Oracle APEX
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "memory")
    APEX_ORDS_BASE_URL = os.getenv("APEX_ORDS_BASE_URL", "")
    APEX_ORDS_TOKEN = os.getenv("APEX_ORDS_TOKEN") or None
    APEX_TIMEOUT_SECONDS = float(os.getenv("APEX_TIMEOUT_SECONDS", "5"))
    # When set, devices must send this value in the X-API-Key header
    DEVICE_API_KEY = os.getenv("DEVICE_API_KEY") or None
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "500"))
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
