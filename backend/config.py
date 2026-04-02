from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = BACKEND_DIR / ".env"
_ENV_LOADED = False


def load_backend_env() -> Path:
    global _ENV_LOADED
    if not _ENV_LOADED:
        load_dotenv(dotenv_path=ENV_PATH)
        _ENV_LOADED = True
    return ENV_PATH
