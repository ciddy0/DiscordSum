import discord
from discord.ext import commands
import logging
from config import DISCORD_TOKEN
from cogs.setup_cog import SetupCog
from cogs.summarizer_cog import SummarizerCog
from db.database import is_channel_monitored, store_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    """Called when a message is sent"""
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Check if this channel is being monitored for summarization
    if is_channel_monitored(message.guild.id, message.channel.id):
        # Store the message for later summarization
        success = store_message(
            guild_id=message.guild.id,
            channel_id=message.channel.id,
            message_id=message.id,
            author_id=message.author.id,
            author_name=message.author.display_name,
            content=message.content,
            timestamp=message.created_at,
            has_attachments=bool(message.attachments),
            reply_to=message.reference.message_id if message.reference else None
        )
        if success:
            logger.debug(f"Stored message {message.id} from {message.author} in {message.channel}")

async def main():
    """Main function to run the bot"""
    async with bot:
        # Load cogs
        await bot.add_cog(SetupCog(bot))
        await bot.add_cog(SummarizerCog(bot))
        logger.info("Loaded cogs")
        
        # Start the bot
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())