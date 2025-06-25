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

# Get tracked channels from environment
# Convert comma-separated string of channel IDs to list of integers
TRACKED_CHANNELS_STR = os.getenv('TRACKED_CHANNELS', '')
TRACKED_CHANNELS = [int(channel_id.strip()) for channel_id in TRACKED_CHANNELS_STR.split(',') if channel_id.strip()]

# Bot permissions and intents
REQUIRED_PERMISSIONS = [
    'send_messages',
    'read_message_history',
    'use_slash_commands',
    'add_reactions'
]

# Chain settings
CHAIN_TIMEOUT_MINUTES = 30  # How long until a chain expires