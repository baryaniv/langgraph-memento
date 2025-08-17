from dotenv import load_dotenv
import os

load_dotenv()  # take environment variables from .env.


OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", None)
POSTGRES_URL=os.getenv("POSTGRES_URL", None)
OPENAI_API_BASE_URL=os.getenv("OPENAI_API_BASE_URL", None)
OPENAI_MODEL=os.getenv("OPENAI_MODEL", None)


required_env_vars = [
    "OPENAI_API_KEY",
]

for var in required_env_vars:
    if not var:
        raise ValueError(f"Missing required environment variable: {var}")