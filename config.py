import os
from dotenv import load_dotenv

# load env variables
load_dotenv()

# discord configs
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN env var is required")

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')