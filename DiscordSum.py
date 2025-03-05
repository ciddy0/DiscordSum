from google import genai
import os
from dotenv import load_dotenv
import discord

# Load API key from .env file
load_dotenv()

#Set up Discord Intents
intents = discord.Intents.default()
intents.message_content = True

API_KEY = os.getenv("GENAI_API_KEY")  # Make sure this key exists in your .env file

client = genai.Client(api_key=API_KEY)

response = client.models.generate_content(
    model="gemini-2.0-flash", contents="Hello"
)

print(response.text)