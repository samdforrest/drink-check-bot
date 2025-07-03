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
from typing import List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Central timezone
central = pytz.timezone('America/Chicago')

class LeaderboardView(discord.ui.View):
    def __init__(self, users: List[User], server_record: Optional[ActiveChain], starter_name: Optional[str]):
        super().__init__(timeout=None)  # No timeout to keep buttons always active
        self.users = users
        self.server_record = server_record
        self.starter_name = starter_name
        self.current_page = 0
        self.users_per_page = 10

    @property
    def max_pages(self):
        return max(0, (len(self.users) - 1) // self.users_per_page)

    def get_embed(self) -> discord.Embed:
        start_idx = self.current_page * self.users_per_page
        page_users = self.users[start_idx:start_idx + self.users_per_page]

        embed = discord.Embed(
            title="🏆 Drink Check Leaderboard",
            color=discord.Color.gold()
        )

        # Format top credits (main leaderboard)
        credits_text = "\n".join(
            f"{start_idx + idx + 1}. {user.username} 🍺 {user.total_credits}"
            for idx, user in enumerate(page_users)
        )
        embed.description = credits_text or "No data"

        # Add page number
        if self.max_pages > 0:
            embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages + 1}")

        # Add server record if it exists
        if self.server_record:
            embed.add_field(
                name="Server Record Chain",
                value=f"🏅 {self.server_record.total_messages} drink checks\nStarted by: {self.starter_name}",
                inline=False
            )

        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        
        # Update button states
        button.disabled = self.current_page == 0
        next_button = [x for x in self.children if x.label == "Next"][0]
        next_button.disabled = self.current_page >= self.max_pages
        
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.max_pages, self.current_page + 1)
        
        # Update button states
        button.disabled = self.current_page >= self.max_pages
        prev_button = [x for x in self.children if x.label == "Previous"][0]
        prev_button.disabled = self.current_page == 0
        
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def start(self, interaction: discord.Interaction):
        """Initial setup of the view"""
        # Set initial button states
        prev_button = [x for x in self.children if x.label == "Previous"][0]
        next_button = [x for x in self.children if x.label == "Next"][0]
        
        prev_button.disabled = self.current_page == 0
        next_button.disabled = self.max_pages == 0
        
        await interaction.response.send_message(embed=self.get_embed(), view=self)

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
                yesterday = today - timedelta(days=1)
                
                # Create datetime ranges in Central Time
                today_start = central.localize(datetime.combine(today, datetime.min.time()))
                today_end = central.localize(datetime.combine(today, datetime.max.time()))
                yesterday_start = central.localize(datetime.combine(yesterday, datetime.min.time()))
                yesterday_end = central.localize(datetime.combine(yesterday, datetime.max.time()))
                
                # Convert to UTC for database queries
                today_start_utc = today_start.astimezone(pytz.UTC)
                today_end_utc = today_end.astimezone(pytz.UTC)
                yesterday_start_utc = yesterday_start.astimezone(pytz.UTC)
                yesterday_end_utc = yesterday_end.astimezone(pytz.UTC)
                
                # Get today's and yesterday's stats
                today_dcs = db.query(func.count(Credit.credit_id))\
                    .filter(Credit.user_id == target_user.id,
                           Credit.timestamp >= today_start_utc,
                           Credit.timestamp <= today_end_utc)\
                    .scalar() or 0

                yesterday_dcs = db.query(func.count(Credit.credit_id))\
                    .filter(Credit.user_id == target_user.id,
                           Credit.timestamp >= yesterday_start_utc,
                           Credit.timestamp <= yesterday_end_utc)\
                    .scalar() or 0

                # Get most active day
                daily_counts = db.query(
                    func.strftime('%Y-%m-%d', Credit.timestamp).label('date'),
                    func.count(Credit.credit_id).label('count')
                ).filter(
                    Credit.user_id == target_user.id
                ).group_by(
                    func.strftime('%Y-%m-%d', Credit.timestamp)
                ).order_by(
                    text('count DESC')
                ).first()

                # Create embed
                embed = discord.Embed(
                    title=f"🍺 Drink Check Profile: {target_user.name}",
                    color=discord.Color.dark_theme()
                )
                
                # Add main stats with emojis
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

                # Add empty field for spacing
                embed.add_field(
                    name="\u200b",
                    value="\u200b",
                    inline=False
                )
                
                # Add today's and yesterday's stats
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

                # Add most active day if available
                if daily_counts and daily_counts.count > 0:
                    embed.add_field(
                        name="Most Active Day (CT)",
                        value=f"🏆 {daily_counts.count} checks on {daily_counts.date}",
                        inline=False
                    )

                # Add streak information at the bottom
                embed.add_field(
                    name="\u200b",
                    value=f"**Longest Streak**: 🍺 {db_user.longest_chain_streak}",
                    inline=False
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
                # Get all users ordered by total credits
                users = db.query(User)\
                    .order_by(User.total_credits.desc())\
                    .all()
                
                if not users:
                    await interaction.response.send_message("No leaderboard data available yet!", ephemeral=True)
                    return

                # Get server record
                server_record = db.query(ActiveChain)\
                    .filter_by(is_server_record=True)\
                    .first()

                # Get the starter's username if server record exists
                starter_name = "Unknown"
                if server_record:
                    starter = db.query(User).filter_by(user_id=server_record.starter_id).first()
                    starter_name = starter.username if starter else "Unknown"

                # Create and start the view
                view = LeaderboardView(users, server_record, starter_name)
                await view.start(interaction)

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

    @app_commands.command(name="chain", description="Display information about the current drink check chain")
    async def chain(self, interaction: discord.Interaction):
        """Display detailed information about the current drink check chain"""
        try:
            logger.info("Fetching chain information")
            with DatabaseSession() as db:
                # Get the most recent chain (active or inactive)
                current_chain = db.query(ActiveChain)\
                    .order_by(ActiveChain.start_time.desc())\
                    .first()
                
                if not current_chain:
                    await interaction.response.send_message("🔗 No chains have been started yet! Start one with a drink check.", ephemeral=True)
                    return
                
                # Get current time in UTC since our timestamps are in UTC
                now = datetime.utcnow().replace(tzinfo=pytz.UTC)
                
                # Check if chain is expired
                is_expired = current_chain.is_expired()
                
                # Convert chain timestamps to Central Time for display
                start_time_ct = current_chain.start_time.astimezone(central)
                last_activity_ct = current_chain.last_activity.astimezone(central)
                
                # Get starter's username
                starter = db.query(User).filter_by(user_id=current_chain.starter_id).first()
                starter_name = starter.username if starter else "Unknown"
                
                # Get last message author's username
                last_author = db.query(User).filter_by(user_id=current_chain.last_message_author_id).first()
                last_author_name = last_author.username if last_author else "Unknown"
                
                # Determine chain status and color
                if current_chain.is_active and not is_expired:
                    status = "🟢 Active"
                    color = discord.Color.green()
                elif current_chain.is_active and is_expired:
                    status = "🟡 Expired (but not yet closed)"
                    color = discord.Color.yellow()
                else:
                    status = "🔴 Closed"
                    color = discord.Color.red()
                
                # Create embed
                embed = discord.Embed(
                    title="🔗 Current Chain Status",
                    color=color
                )
                
                # Add main chain info
                embed.add_field(
                    name="Chain Length",
                    value=f"🍺 {current_chain.total_messages} drink checks",
                    inline=False
                )
                
                embed.add_field(
                    name="Chain Starter",
                    value=f"👑 {starter_name}",
                    inline=True
                )
                
                embed.add_field(
                    name="Last Participant",
                    value=f"🎯 {last_author_name}",
                    inline=True
                )
                
                embed.add_field(
                    name="Status",
                    value=status,
                    inline=False
                )
                
                # Add timing information
                embed.add_field(
                    name="Started (CT)",
                    value=f"📅 {start_time_ct.strftime('%m/%d/%Y at %I:%M:%S %p')}",
                    inline=True
                )
                
                embed.add_field(
                    name="Last Activity (CT)",
                    value=f"📅 {last_activity_ct.strftime('%m/%d/%Y at %I:%M:%S %p')}",
                    inline=True
                )
                
                # Add time remaining if active
                if current_chain.is_active and not is_expired:
                    last_activity_utc = current_chain.last_activity.replace(tzinfo=pytz.UTC)
                    time_diff = now - last_activity_utc
                    minutes_left = 30 - (time_diff.total_seconds() / 60)
                    
                    embed.add_field(
                        name="Time Remaining",
                        value=f"⏰ {minutes_left:.1f} minutes",
                        inline=False
                    )
                
                # Add server record indicator if applicable
                if current_chain.is_server_record:
                    embed.add_field(
                        name="🏆 Server Record",
                        value="This chain set a new server record!",
                        inline=False
                    )
                
                # Calculate chain duration
                # duration = current_chain.last_activity - current_chain.start_time
                # hours = int(duration.total_seconds() // 3600)
                # minutes = int((duration.total_seconds() % 3600) // 60)
                
                # embed.add_field(
                #     name="Chain Duration",
                #     value=f"⏱️ {hours}h {minutes}m",
                #     inline=True
                # )
                
                await interaction.response.send_message(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in chain command: {e}")
            await interaction.response.send_message("Error fetching chain information.", ephemeral=True)
            raise

async def setup(bot):
    await bot.add_cog(StatsCommands(bot))
    return True