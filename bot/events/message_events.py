#message handling events
from discord.ext import commands
from discord import Message
from database.models import User, DrinkCheck, Credit, ActiveChain
from database.connection import DatabaseSession
from bot.trackers import DrinkCheckTracker
from datetime import datetime
import pytz
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Central timezone
central = pytz.timezone('America/Chicago')

class MessageEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracker = DrinkCheckTracker()

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Debug log the message content and attachments
        logger.info(f"Message received: {message.content}")
        logger.info(f"Has attachments: {len(message.attachments) > 0}")
        
        # Check if it's a valid drink check (requires 'dc' + attachment)
        is_drink_check = self.tracker.is_drink_check(message.content, message)
        if is_drink_check:
            logger.info("Valid drink check detected")
            await self._process_drink_check(message)

    async def _get_or_create_user(self, db, user_id, username):
        """Get or create a user in the database."""
        user = db.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(user_id=user_id, username=username, total_credits=0)
            db.add(user)
            db.commit()
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

    async def _create_new_chain(self, db, message_id, user_id):
        """Create a new chain and deactivate any existing ones."""
        # Deactivate any existing chains
        db.query(ActiveChain)\
            .filter_by(is_active=True)\
            .update({"is_active": False})
        
        # Create new chain with current time in Central Time
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        
        new_chain = ActiveChain(
            starter_id=user_id,
            start_message_id=message_id,
            last_message_id=message_id,
            last_message_author_id=user_id,
            start_time=now,
            last_activity=now
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
                
                # Create drink check record with current time in Central Time
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
                
                else:
                    # Active chain exists - add to it
                    drink_check.chain_id = active_chain.chain_id
                    is_chain_starter = message.author.id == active_chain.starter_id
                    is_self_reply = message.author.id == active_chain.last_message_author_id
                    
                    # Award chain credit to participant
                    chain_credit = Credit(
                        user_id=message.author.id,
                        message_id=message.id,
                        credit_type='chain',
                        timestamp=now
                    )
                    db.add(chain_credit)
                    user.total_credits += 1
                    
                    
                    
                    # Update chain's last message info
                    active_chain.last_message_id = message.id
                    active_chain.last_message_author_id = message.author.id
                    
                    # Only update last_activity (timer) if it's not a self-reply or same person
                    if not is_self_reply and not is_chain_starter:
                        active_chain.last_activity = now
                        logger.info("Chain timer reset")
                    else:
                        logger.info("Self-reply or starter drink check - timer not reset")

                db.commit()
                logger.info("Successfully committed all database changes")
                
                # Add reaction to confirm credit
                await message.add_reaction('🍺')
        
        except Exception as e:
            logger.error(f"Error in _process_drink_check: {e}")
            raise

async def setup(bot):
    await bot.add_cog(MessageEvents(bot))
    return True