import discord
from discord.ext import commands
import asyncio
import logging
from config import BOT_TOKEN, COMMAND_PREFIX, BOT_DESCRIPTION

# Set up logging
logging.basicConfig(level=logging.INFO)

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    description=BOT_DESCRIPTION,
    intents=intents
)

@bot.event
async def on_ready():
    print(f'{bot.user} has landed! 🚀')
    print(f'Connected to {len(bot.guilds)} servers')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Game(name=f"{COMMAND_PREFIX}help | Fun & Games!")
    )

@bot.event
async def on_command_error(ctx, error):
    try:
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("🤔 Command not found! Use `!help` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param}")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            print(f"Error: {error}")
    except discord.Forbidden:
        # Bot doesn't have permission to send messages in this channel
        print(f"Cannot send error message in {ctx.channel.name}: Missing permissions")
    except Exception as e:
        print(f"Error in error handler: {e}")

# Load cogs
async def load_cogs():
    cogs = ['cogs.games', 'cogs.group_finder', 'cogs.integrations', 'cogs.economy', 'cogs.admin', 'cogs.quotes', 'cogs.welcome', 'cogs.bump_reminder', 'cogs.audit_log', 'cogs.phrase_tracker', 'cogs.role_system']
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f'✅ Loaded {cog}')
        except Exception as e:
            print(f'❌ Failed to load {cog}: {e}')

async def main():
    await load_cogs()
    await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())