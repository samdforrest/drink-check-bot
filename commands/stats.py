#statistics commands
import discord
from discord.ext import commands
from discord import app_commands
from database.models import User, DrinkCheck, Credit, ActiveChain
from database.connection import DatabaseSession
from sqlalchemy import func, text
from datetime import datetime, timedelta
import pytz
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Central timezone
central = pytz.timezone('America/Chicago')

class StatsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="test", description="Test command to verify slash commands work")
    async def test(self, interaction: discord.Interaction):
        """Simple test command"""
        await interaction.response.send_message("Test command works! Slash commands are functioning.", ephemeral=True)
        
    @app_commands.command(name="profile", description="View your drink check profile")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        """View detailed drink check profile for a user"""
        try:
            target_user = user or interaction.user
            logger.info(f"Getting profile for user: {target_user.name}")
            
            with DatabaseSession() as db:
                # Get user data
                db_user = db.query(User).filter_by(user_id=target_user.id).first()
                if not db_user:
                    logger.info(f"No profile found for user: {target_user.name}")
                    await interaction.response.send_message(f"{target_user.name} hasn't participated in any drink checks yet!", ephemeral=True)
                    return

                logger.info(f"Found user profile with {db_user.total_credits} total credits")

                # Get detailed stats
                initial_dcs = db.query(func.count(Credit.credit_id))\
                    .filter_by(user_id=target_user.id, credit_type='initial')\
                    .scalar() or 0
                    
                chain_dcs = db.query(func.count(Credit.credit_id))\
                    .filter_by(user_id=target_user.id, credit_type='chain')\
                    .scalar() or 0

                # Get current time in Central Time
                now = datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(central)
                today = now.date()
                
                # Create datetime ranges in Central Time
                today_start = central.localize(datetime.combine(today, datetime.min.time()))
                today_end = central.localize(datetime.combine(today, datetime.max.time()))
                
                # Convert back to UTC for database query
                today_start_utc = today_start.astimezone(pytz.UTC)
                today_end_utc = today_end.astimezone(pytz.UTC)
                
                # Get today's stats
                today_dcs = db.query(func.count(Credit.credit_id))\
                    .filter(Credit.user_id == target_user.id,
                           Credit.timestamp >= today_start_utc,
                           Credit.timestamp <= today_end_utc)\
                    .scalar() or 0

                # Check if user holds any server records
                has_record = db.query(ActiveChain)\
                    .filter_by(starter_id=target_user.id, is_server_record=True)\
                    .first() is not None

                # Create embed
                embed = discord.Embed(
                    title=f"🍺 DrinkCheck Profile for {target_user.name}",
                    color=discord.Color.blue()
                )
                
                # Add stats fields
                embed.add_field(
                    name="Total Credits",
                    value=f"{db_user.total_credits:,}",
                    inline=True
                )
                embed.add_field(
                    name="Chains Started",
                    value=f"{initial_dcs:,}",
                    inline=True
                )
                embed.add_field(
                    name="Chain Participations",
                    value=f"{chain_dcs:,}",
                    inline=True
                )
                
                # Add chain stats
                embed.add_field(
                    name="Longest Chain Streak",
                    value=f"{db_user.longest_chain_streak:,} drink checks",
                    inline=True
                )
                embed.add_field(
                    name="Server Record Holder",
                    value="🏆 Yes" if has_record else "No",
                    inline=True
                )
                embed.add_field(
                    name="Today's Drink Checks",
                    value=f"{today_dcs:,}",
                    inline=True
                )
                
                # Add user avatar
                embed.set_thumbnail(url=target_user.display_avatar.url)
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in profile command: {e}")
            await interaction.response.send_message("Error getting profile information.", ephemeral=True)
            raise
    
    @app_commands.command(name="leaderboard", description="View the drink check leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Display the drink check leaderboard"""
        try:
            logger.info("Fetching leaderboard data")
            with DatabaseSession() as db:
                # Get top 10 users by total credits
                top_credits = db.query(User)\
                    .order_by(User.total_credits.desc())\
                    .limit(10)\
                    .all()
                
                # Get server record
                server_record = db.query(ActiveChain)\
                    .filter_by(is_server_record=True)\
                    .first()

                # Create embed
                embed = discord.Embed(
                    title="🏆 Drink Check Leaderboard",
                    color=discord.Color.gold()
                )

                # Format top credits (main leaderboard)
                credits_text = "\n".join(
                    f"{idx+1}. {user.username} 🍺 {user.total_credits}"
                    for idx, user in enumerate(top_credits)
                )
                embed.description = credits_text or "No data"

                # Add server record if it exists
                if server_record:
                    # Get the starter's username
                    starter = db.query(User).filter_by(user_id=server_record.starter_id).first()
                    starter_name = starter.username if starter else "Unknown"
                    
                    embed.add_field(
                        name="Server Record Chain",
                        value=f"🏅 {server_record.total_messages} drink checks\nStarted by: {starter_name}",
                        inline=False
                    )

                await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await interaction.response.send_message("Error fetching leaderboard data.", ephemeral=True)
            raise

    @app_commands.command(name="timer", description="Check how much time is left in the current drink check chain")
    async def timer(self, interaction: discord.Interaction):
        """Check the status of the current chain and how much time is left"""
        try:
            logger.info("Checking chain timer")
            with DatabaseSession() as db:
                # Get active chain
                active_chain = db.query(ActiveChain)\
                    .filter_by(is_active=True)\
                    .order_by(ActiveChain.start_time.desc())\
                    .first()
                
                if not active_chain:
                    await interaction.response.send_message("🕒 No active chain right now! Start one with a drink check.", ephemeral=True)
                    return
                
                # Get current time in UTC since our timestamps are in UTC
                now = datetime.utcnow().replace(tzinfo=pytz.UTC)
                
                # Convert chain timestamps to Central Time for display
                start_time_ct = active_chain.start_time.astimezone(central)
                last_activity_ct = active_chain.last_activity.astimezone(central)
                
                # Calculate time difference
                last_activity_utc = active_chain.last_activity.replace(tzinfo=pytz.UTC)
                time_diff = now - last_activity_utc
                minutes_left = 30 - (time_diff.total_seconds() / 60)
                
                # Get starter's username
                starter = db.query(User).filter_by(user_id=active_chain.starter_id).first()
                starter_name = starter.username if starter else "Unknown"
                
                # Get last message author's username
                last_author = db.query(User).filter_by(user_id=active_chain.last_message_author_id).first()
                last_author_name = last_author.username if last_author else "Unknown"
                
                # Create embed
                embed = discord.Embed(
                    title="⏱️ Chain Timer Status",
                    color=discord.Color.blue() if minutes_left > 5 else discord.Color.red()
                )
                
                # Add chain info
                embed.add_field(
                    name="Chain Starter",
                    value=f"👑 {starter_name}",
                    inline=True
                )
                
                embed.add_field(
                    name="Last Activity By",
                    value=f"🎯 {last_author_name}",
                    inline=True
                )
                
                embed.add_field(
                    name="Time Left",
                    value=f"⏰ {minutes_left:.1f} minutes" if minutes_left > 0 else "⚠️ Chain expired!",
                    inline=False
                )
                
                embed.add_field(
                    name="Chain Started (CT)",
                    value=f"📅 {start_time_ct.strftime('%I:%M:%S %p')}",
                    inline=True
                )
                
                embed.add_field(
                    name="Last Activity (CT)",
                    value=f"📅 {last_activity_ct.strftime('%I:%M:%S %p')}",
                    inline=True
                )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in timer command: {e}")
            await interaction.response.send_message("Error checking chain timer.", ephemeral=True)
            raise

async def setup(bot):
    await bot.add_cog(StatsCommands(bot))
    return True