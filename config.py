import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
COMMAND_PREFIX = '!'
BOT_DESCRIPTION = 'A fun Discord bot with games and group finder!'

# Colors for embeds
COLORS = {
    'primary': 0x5865F2,
    'success': 0x57F287,
    'warning': 0xFEE75C,
    'error': 0xED4245,
    'info': 0x5865F2
}

# Game settings
GAME_TIMEOUT = 60  # seconds
MAX_GROUP_SIZE = 10

# Economy settings
CURRENCY_NAME = "coins"
STARTING_BALANCE = 1000
DAILY_REWARD = 500

# RPG settings
STARTING_GOLD = 10
STARTING_EQUIPMENT = [1]

# API Keys
RAWG_API_KEY = os.getenv('RAWG_API_KEY')