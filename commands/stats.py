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
                
                today_dcs = db.query(func.count(DrinkCheck.message_id))\
                    .filter(
                        DrinkCheck.user_id == target_user.id,
                        DrinkCheck.timestamp >= today_start_utc,
                        DrinkCheck.timestamp <= today_end_utc
                    ).scalar() or 0

                # Get yesterday's drink checks
                yesterday = today - timedelta(days=1)
                yesterday_start = central.localize(datetime.combine(yesterday, datetime.min.time()))
                yesterday_end = central.localize(datetime.combine(yesterday, datetime.max.time()))
                
                # Convert to UTC for database query
                yesterday_start_utc = yesterday_start.astimezone(pytz.UTC)
                yesterday_end_utc = yesterday_end.astimezone(pytz.UTC)
                
                yesterday_dcs = db.query(func.count(DrinkCheck.message_id))\
                    .filter(
                        DrinkCheck.user_id == target_user.id,
                        DrinkCheck.timestamp >= yesterday_start_utc,
                        DrinkCheck.timestamp <= yesterday_end_utc
                    ).scalar() or 0

                # Get highest daily count using SQLite's date() function and timezone conversion
                # First convert the timestamp to Central Time using strftime
                daily_counts = db.query(
                    func.strftime('%Y-%m-%d', DrinkCheck.timestamp).label('date'),
                    func.count(DrinkCheck.message_id).label('count')
                ).filter(
                    DrinkCheck.user_id == target_user.id
                ).group_by(
                    func.strftime('%Y-%m-%d', DrinkCheck.timestamp)
                ).order_by(
                    func.count(DrinkCheck.message_id).desc()
                ).first()

                highest_daily = daily_counts[1] if daily_counts else 0
                highest_date = daily_counts[0] if daily_counts else None

                logger.info(f"Stats for {target_user.name}: initial={initial_dcs}, chain={chain_dcs}, today={today_dcs}")

                # Create embed
                embed = discord.Embed(
                    title=f"🍺 Drink Check Profile: {target_user.name}",
                    color=discord.Color.gold()
                )
                
                embed.add_field(
                    name="Total Credits",
                    value=f"🍺 {db_user.total_credits}",
                    inline=False
                )
                
                embed.add_field(
                    name="Initial Drink Checks",
                    value=f"📝 {initial_dcs}",
                    inline=True
                )
                
                embed.add_field(
                    name="Chain Participations",
                    value=f"⛓️ {chain_dcs}",
                    inline=True
                )

                # Add daily stats section
                embed.add_field(
                    name="\u200b",  # Empty field for spacing
                    value="\u200b",
                    inline=False
                )

                embed.add_field(
                    name="Today's Drink Checks (CT)",
                    value=f"📅 {today_dcs}",
                    inline=True
                )

                embed.add_field(
                    name="Yesterday's Drink Checks (CT)",
                    value=f"📅 {yesterday_dcs}",
                    inline=True
                )

                if highest_date:
                    embed.add_field(
                        name="Most Active Day (CT)",
                        value=f"🏆 {highest_daily} checks on {highest_date}",
                        inline=False
                    )
                
                # Add user avatar
                embed.set_thumbnail(url=target_user.display_avatar.url)
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in profile command: {e}")
            await interaction.response.send_message("Error getting profile information.", ephemeral=True)
            raise  # Add this to see the full error trace in logs
    
    @app_commands.command(name="leaderboard", description="View the drink check leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Display the drink check leaderboard"""
        try:
            logger.info("Fetching leaderboard data")
            with DatabaseSession() as db:
                # Get top 10 users
                top_users = db.query(User)\
                    .order_by(User.total_credits.desc())\
                    .limit(10)\
                    .all()
                
                logger.info(f"Found {len(top_users)} users for leaderboard")
                
                if not top_users:
                    logger.info("No users found in database")
                    await interaction.response.send_message("No drink checks recorded yet!", ephemeral=True)
                    return
                
                # Create embed
                embed = discord.Embed(
                    title="🏆 Drink Check Leaderboard",
                    color=discord.Color.gold()
                )
                
                # Add leaderboard entries
                leaderboard_text = ""
                for i, user in enumerate(top_users, 1):
                    member = interaction.guild.get_member(user.user_id)
                    name = member.name if member else user.username
                    leaderboard_text += f"`{i}.` {name:<20} 🍺 {user.total_credits}\n"
                    logger.info(f"Leaderboard entry {i}: {name} with {user.total_credits} credits")
                
                embed.description = leaderboard_text
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}", exc_info=True)
            await interaction.response.send_message("Error getting leaderboard.", ephemeral=True)

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