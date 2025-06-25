#message handling events
from discord.ext import commands
from discord import Message
from database.models import User, DrinkCheck, Credit, ActiveChain
from database.connection import DatabaseSession
from bot.trackers import DrinkCheckTracker
from datetime import datetime
import pytz
import logging
from typing import Dict, Set

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Central timezone
central = pytz.timezone('America/Chicago')

class MessageEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = DrinkCheckTracker()
        # Add cache for users and allowed channels
        self.user_cache: Dict[int, User] = {}
        self.allowed_channels: Set[int] = set()
        self.cache_timeout = 3600  # Cache timeout in seconds
        self.last_cache_cleanup = datetime.utcnow()

    async def setup_channels(self):
        """Load allowed channels from settings"""
        try:
            from config.settings import TRACKED_CHANNELS
            self.allowed_channels = set(TRACKED_CHANNELS)
            logger.info(f"Loaded {len(self.allowed_channels)} tracked channels")
        except ImportError:
            logger.warning("No TRACKED_CHANNELS found in settings, all channels will be tracked")
            self.allowed_channels = set()

    def _should_process_message(self, message: Message) -> bool:
        """Quick check if message should be processed"""
        # Ignore bot messages
        if message.author.bot:
            logger.debug("Ignoring bot message")
            return False
            
        # If no channel restrictions, process all
        if not self.allowed_channels:
            return True
            
        # Check if message is in allowed channel
        is_allowed = message.channel.id in self.allowed_channels
        if not is_allowed:
            logger.debug(f"Channel {message.channel.id} not in tracked channels")
        return is_allowed

    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        now = datetime.utcnow()
        if (now - self.last_cache_cleanup).total_seconds() > 3600:  # Cleanup every hour
            logger.info("Cleaning up user cache")
            self.user_cache.clear()
            self.last_cache_cleanup = now

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        try:
            # Quick early return if message shouldn't be processed
            if not self._should_process_message(message):
                return

            # Debug log the message content and attachments
            logger.info(f"Processing message in channel {message.channel.id}: {message.content}")
            logger.info(f"Has attachments: {len(message.attachments) > 0}")
            
            # Check if it's a valid drink check (requires 'dc' + attachment)
            is_drink_check = self.tracker.is_drink_check(message.content, message)
            logger.info(f"Is drink check: {is_drink_check}")
            
            if is_drink_check:
                logger.info("Valid drink check detected")
                await self._process_drink_check(message)
                
            # Cleanup cache periodically
            self._cleanup_cache()
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    async def _get_or_create_user(self, db, user_id, username):
        """Get user from cache or create in database."""
        # Check cache first
        if user_id in self.user_cache:
            return self.user_cache[user_id]

        # If not in cache, get from database
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(user_id=user_id, username=username, total_credits=0)
            db.add(user)
            db.commit()
            
        # Add to cache
        self.user_cache[user_id] = user
        return user

    async def _get_active_chain(self, db):
        """Get the current active chain if it exists and isn't expired."""
        active_chain = db.query(ActiveChain)\
            .filter_by(is_active=True)\
            .order_by(ActiveChain.start_time.desc())\
            .first()
        
        if active_chain and active_chain.is_expired():
            active_chain.is_active = False
            db.commit()
            return None
            
        return active_chain

    async def _create_new_chain(self, db, message_id: int, user_id: int) -> ActiveChain:
        """Create a new chain and deactivate any existing ones."""
        # Deactivate any existing chains
        db.query(ActiveChain)\
            .filter_by(is_active=True)\
            .update({"is_active": False})
        
        # Create new chain with current time in UTC
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        
        new_chain = ActiveChain(
            starter_id=user_id,
            start_message_id=message_id,
            last_message_id=message_id,
            last_message_author_id=user_id,
            start_time=now,
            last_activity=now,
            total_messages=1  # Start with 1 message
        )
        db.add(new_chain)
        db.commit()
        return new_chain

    async def _process_drink_check(self, message: Message):
        """Process a drink check message and award credits."""
        logger.info(f"Processing drink check for user: {message.author.name}")
        
        try:
            with DatabaseSession() as db:
                # Get or create user
                user = await self._get_or_create_user(db, message.author.id, str(message.author))
                
                # Check for active chain
                active_chain = await self._get_active_chain(db)
                
                # Create drink check record with current time in UTC
                now = datetime.utcnow().replace(tzinfo=pytz.UTC)
                
                drink_check = DrinkCheck(
                    message_id=message.id,
                    user_id=message.author.id,
                    is_reply=message.reference is not None,
                    replied_to_message_id=message.reference.message_id if message.reference else None,
                    timestamp=now
                )
                db.add(drink_check)

                if not active_chain:
                    # No active chain - starting a new one
                    chain = await self._create_new_chain(db, message.id, message.author.id)
                    drink_check.chain_id = chain.chain_id
                    
                    # Award initial credit
                    credit = Credit(
                        user_id=message.author.id,
                        message_id=message.id,
                        credit_type='initial',
                        timestamp=now
                    )
                    db.add(credit)
                    user.total_credits += 1
                    logger.info(f"Started new chain, awarded initial credit to {message.author.name}")
                    
                    # Send chain start message
                    await message.channel.send(f"🔗 New chain started by {message.author.mention}!")
                
                else:
                    # Active chain exists - add to it
                    drink_check.chain_id = active_chain.chain_id
                    
                    # Award chain credit
                    credit = Credit(
                        user_id=message.author.id,
                        message_id=message.id,
                        credit_type='chain',
                        timestamp=now
                    )
                    db.add(credit)
                    user.total_credits += 1
                    
                    # Update chain's last message info and activity
                    active_chain.last_message_id = message.id
                    active_chain.last_message_author_id = message.author.id
                    active_chain.last_activity = now
                    active_chain.total_messages += 1
                    
                    # Check if this chain sets a new record
                    current_record = db.query(ActiveChain)\
                        .filter_by(is_server_record=True)\
                        .with_entities(ActiveChain.total_messages)\
                        .first()
                    
                    current_record_count = current_record[0] if current_record else 0
                    
                    if active_chain.total_messages > current_record_count:
                        # New server record!
                        active_chain.is_server_record = True
                        # Update old record holder
                        if current_record:
                            db.query(ActiveChain)\
                                .filter_by(is_server_record=True)\
                                .filter(ActiveChain.chain_id != active_chain.chain_id)\
                                .update({"is_server_record": False})
                        
                        await message.channel.send(
                            f"🏆 **New Server Record!**\n"
                            f"This chain now has {active_chain.total_messages} drink checks!"
                        )
                    
                    # Update user's personal best if needed
                    if active_chain.total_messages > user.longest_chain_streak:
                        user.longest_chain_streak = active_chain.total_messages
                    
                    # Send chain update message every 5 messages
                    if active_chain.total_messages % 5 == 0:
                        await message.channel.send(
                            f"🔗 Chain Update!\n"
                            f"Current streak: {active_chain.total_messages} drink checks"
                        )
                    
                    logger.info(f"Added to existing chain, total messages: {active_chain.total_messages}")

                db.commit()
                logger.info("Successfully committed all database changes")
                
                # Add reaction to confirm credit
                await message.add_reaction('🍺')
        
        except Exception as e:
            logger.error(f"Error in _process_drink_check: {e}")
            raise

async def setup(bot):
    cog = MessageEvents(bot)
    await cog.setup_channels()  # Initialize tracked channels
    await bot.add_cog(cog)
    return True