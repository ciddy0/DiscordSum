import discord
from discord.ext import commands
from discord import app_commands
import logging
from db.database import (is_channel_monitored, add_monitored_channel, 
                        remove_monitored_channel, get_channel_info, 
                        get_message_count, channel_exists_in_db)

logger = logging.getLogger(__name__)

class SetupCog(commands.Cog):
    """Cog for bot setup commands"""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Set up message monitoring for this channel")
    async def setup(self, interaction: discord.Interaction):
        """Set up the bot to monitor this channel for messages"""
        
        # Check if user has manage channels permission
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ You need 'Manage Channels' permission to set up the bot dummy.", 
                ephemeral=True
            )
            return
        
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        channel_name = interaction.channel.name
        user_id = interaction.user.id
        username = interaction.user.display_name
        
        # Check if channel is already being monitored
        if is_channel_monitored(guild_id, channel_id):
            channel_info = get_channel_info(guild_id, channel_id)
            await interaction.response.send_message(
                f"✅ This channel is already being monitored for message summarization. :D\n"
                f"Set up by: {channel_info['setup_by_username']} on {channel_info['created_at']}",
                ephemeral=True
            )
            return
        
        # Check if channel existed before but was disabled
        was_previously_monitored = channel_exists_in_db(guild_id, channel_id)
        
        # Add/reactivate channel monitoring
        success = add_monitored_channel(guild_id, channel_id, channel_name, user_id, username)
        if not success:
            await interaction.response.send_message(
                "❌ ermmm failed to set up channel monitoring. Please try again.",
                ephemeral=True
            )
            return
        
        # Send success message
        if was_previously_monitored:
            embed = discord.Embed(
                title="✅ Channel Monitoring Re-enabled",
                description=f"**#{channel_name}** monitoring has been reactivated! :D",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Channel Setup Complete",
                description=f"I will now monitor **#{channel_name}** for messages and store them for summarization. >:),
                color=discord.Color.green()
            )
        embed.add_field(
            name="hehe im spy on you: ",
            value="• I'll start storing all messages sent in this channel\n"
                  "• Use `/status` to check monitoring status\n"
                  "• Use `/unset` to stop monitoring this channel",
            inline=False
        )
        embed.set_footer(text=f"Set up by {username}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unset", description="Stop monitoring this channel")
    async def unset(self, interaction: discord.Interaction):
        """Stop monitoring this channel for messages"""
        
        # Check if user has manage channels permission
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ ermmm you need 'Manage Channels' permission to unset the bot LOSER.", 
                ephemeral=True
            )
            return
        
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        channel_name = interaction.channel.name
        
        if not is_channel_monitored(guild_id, channel_id):
            await interaction.response.send_message(
                "❌ errmmm this channel is not currently being monitored for message summarization.",
                ephemeral=True
            )
            return
        
        # Remove channel from monitoring
        success = remove_monitored_channel(guild_id, channel_id)
        if not success:
            await interaction.response.send_message(
                "❌ ermmm failed to stop monitoring this channel. SORRY Please try again.",
                ephemeral=True
            )
            return
        
        # Send success message
        embed = discord.Embed(
            title="✅ Channel Monitoring Disabled",
            description=f"I will no longer monitor **#{channel_name}** for new messages </3.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Note",
            value="Previously stored messages will remain in the database jajaja. Use `/setup` to re-enable monitoring.",
            inline=False
        )
        embed.set_footer(text=f"Disabled by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status", description="Check the monitoring status of this channel")
    async def status(self, interaction: discord.Interaction):
        """Check if this channel is being monitored"""
        
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        channel_name = interaction.channel.name
        
        if is_channel_monitored(guild_id, channel_id):
            channel_info = get_channel_info(guild_id, channel_id)
            message_count = get_message_count(guild_id, channel_id)
            
            embed = discord.Embed(
                title="✅ Channel Status: Active",
                description=f"**#{channel_name}** is currently being monitored for message summarization >:).",
                color=discord.Color.green()
            )
            embed.add_field(name="Set up by", value=channel_info['setup_by_username'], inline=True)
            embed.add_field(name="Set up on", value=channel_info['created_at'], inline=True)
            embed.add_field(name="Messages stored", value=str(message_count), inline=True)
            
        else:
            embed = discord.Embed(
                title="❌ Channel Status: Inactive",
                description=f"**ermmm #{channel_name}** is not currently being monitored for message summarization.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="To enable monitoring",
                value="Use the `/setup` command in this channel.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)