#bot token, database path, etc.
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables. Please set it in your .env file.")

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'drink_check_bot.db')

# Bot Configuration
BOT_PREFIX = os.getenv('BOT_PREFIX', '!')

# Channel Configuration
TRACKED_CHANNELS = os.getenv('TRACKED_CHANNELS', '').split(',') if os.getenv('TRACKED_CHANNELS') else []

# Bot permissions and intents
REQUIRED_PERMISSIONS = [
    'send_messages',
    'read_message_history',
    'use_slash_commands',
    'add_reactions'
]