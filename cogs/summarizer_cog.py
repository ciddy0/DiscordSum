import discord
from discord.ext import commands
from discord import app_commands
import logging
import google.generativeai as genai
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from db.database import (is_channel_monitored, get_messages, get_message_count, 
                        get_messages_by_timeframe)

logger = logging.getLogger(__name__)

class SummarizerCog(commands.Cog):
    """Cog for message summarization using Google Gemini"""
    
    def __init__(self, bot):
        self.bot = bot
        # Configure Gemini API
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

    
    def get_messages_in_timeframe_backup(self, guild_id: int, channel_id: int, hours: int) -> List[Dict]:
        """Backup method - Get messages from the last X hours (use database version instead)"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] + '+00:00'
        
        all_messages = get_messages(guild_id, channel_id, limit=1000)
        
        filtered_messages = []
        for msg in all_messages:
            try:
                if msg['timestamp'] >= cutoff_str:
                    filtered_messages.append(msg)
            except Exception as e:
                logger.warning(f"Error comparing timestamp for message {msg.get('message_id', 'unknown')}: {e}")
                continue
        
        # Sort by timestamp
        filtered_messages.sort(key=lambda x: x['timestamp'])
        return filtered_messages
    
    def format_messages_for_ai(self, messages: List[Dict], channel_name: str, hours: int) -> str:
        """Format messages into a readable format for AI processing"""
        if not messages:
            return f"No messages found in #{channel_name} from the last {hours} hour(s)."
        
        formatted = f"Discord Channel: #{channel_name}\n"
        formatted += f"Messages from the last {hours} hour(s) ({len(messages)} total messages):\n\n"
        
        for msg in messages:
            # Parse timestamp to make it more readable
            timestamp_str = msg['timestamp']
            try:
                # Your format: 2025-08-17 00:09:56.151000+00:00
                dt = datetime.fromisoformat(timestamp_str)
                readable_time = dt.strftime('%H:%M:%S')  # Just show time like 00:09:56
            except:
                readable_time = timestamp_str  
            
            author = msg['author_name']
            content = msg['content'] or "[No text content]"
            
            # Handle attachments
            if msg.get('has_attachments'):
                content += " [Has attachments]"
            
            # Handle replies
            if msg.get('reply_to'):
                content = f"[Reply] {content}"
            
            formatted += f"[{readable_time}] {author}: {content}\n"
        
        return formatted
    
    def create_summarization_prompt(self, formatted_messages: str, channel_name: str, hours: int) -> str:
        """Prompt for Gemini"""
        prompt = f"""Hey bestie! Can you help me summarize what went down in the #{channel_name} Discord channel over the last {hours} hour(s)? 

                    Here are all the messages:

                    {formatted_messages}

                    Please give me a fun, casual summary that sounds like you're gossiping with friends! Include:
                    - The main topics/conversations that happened
                    - Any drama, funny moments, or interesting discussions 
                    - Who was the most active/chatty
                    - Overall vibe of the chat
                    - Any important announcements or decisions

                    Make it sound natural and entertaining - like you're telling your bestie what they missed while they were away! Use emojis and keep it light and fun. Don't be too formal or robotic - we're all friends here!

                    If there were barely any messages or just boring stuff, be honest about it but still make it entertaining!
                    """
        return prompt
    
    async def generate_summary(self, messages: List[Dict], channel_name: str, hours: int) -> str:
        """Generate summary using Google Gemini"""
        try:
            if not messages:
                return f"Bestie, #{channel_name} was dead silent for the past {hours} hour(s) LOL. Not a single message! Everyone must be touching grass or something idk"
            
            # Format messages for AI
            formatted_messages = self.format_messages_for_ai(messages, channel_name, hours)
            
            # Create prompt
            prompt = self.create_summarization_prompt(formatted_messages, channel_name, hours)
            
            # Generate summary
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            else:
                return f"Oop, Gemini decided to be mysterious and didn't give me a summary 🤷‍♀️ Maybe try again?"
                
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Ermmm, something went wrong while trying to summarize  mb gang. Error: {str(e)}"
    
    @app_commands.command(name="summarize", description="Get a fun summary of recent channel messages")
    @app_commands.describe(
        hours="How many hours back to summarize (1-5)"
    )
    @app_commands.choices(hours=[
        app_commands.Choice(name="1 hour ago", value=1),
        app_commands.Choice(name="2 hours ago", value=2),
        app_commands.Choice(name="3 hours ago", value=3),
        app_commands.Choice(name="4 hours ago", value=4),
        app_commands.Choice(name="5 hours ago", value=5),
    ])
    async def summarize(self, interaction: discord.Interaction, hours: app_commands.Choice[int]):
        """Generate a summary of recent messages in this channel"""
        
        # Check if channel is being monitored
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        channel_name = interaction.channel.name
        
        if not is_channel_monitored(guild_id, channel_id):
            embed = discord.Embed(
                title="❌ Channel Not Monitored",
                description=f"Sorry bestie! I'm not monitoring **#{channel_name}** yet, so I can't summarize it\n\nUse `/setup` first to start monitoring this channel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Defer response since AI generation might take time
        await interaction.response.defer()
        
        try:
            # Get messages from timeframe using the optimized database function
            hours_value = hours.value
            messages = get_messages_by_timeframe(guild_id, channel_id, hours_value)
            
            # Generate summary
            summary = await self.generate_summary(messages, channel_name, hours_value)
            
            # Create embed
            embed = discord.Embed(
                title=f"Channel Summary - Last {hours_value} Hour{'s' if hours_value > 1 else ''}",
                description=summary,
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Stats",
                value=f"**Messages analyzed:** {len(messages)}\n**Channel:** #{channel_name}\n**Timeframe:** {hours_value} hour{'s' if hours_value > 1 else ''}",
                inline=True
            )
            
            embed.set_footer(
                text=f"Summary requested by {interaction.user.display_name} • Powered by Google Gemini"
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in summarize command: {e}")
            error_embed = discord.Embed(
                title="❌ Oopsies!",
                description=f"Something went wrong while generating your summary XD\n\n**Error:** {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)