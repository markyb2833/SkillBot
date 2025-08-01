# Discord Fun Bot 🎮

A feature-rich Discord bot with games, integrations, and a group finder system!

## Features

### 🎮 Games
- **Rock Paper Scissors** (`!rps rock/paper/scissors`)
- **Magic 8-Ball** (`!8ball <question>`)
- **Trivia Questions** (`!trivia`)
- **Dice Rolling** (`!dice [sides] [count]`)

### 🔗 Fun Integrations
- **Random Memes** (`!meme`)
- **Jokes** (`!joke`)
- **Inspirational Quotes** (`!quote`)
- **Polls** (`!poll "Question?" "Option 1" "Option 2"`)
- **Coin Flip** (`!coinflip`)
- **Random Choice** (`!choose option1 option2 option3`)
- **Reminders** (`!remind <minutes> <message>`)

### 👥 Group Finder System
- **Create Groups** (`!creategroup <activity> [max_size] [description]`)
- **Join Groups** (`!joingroup <group_id>`)
- **Leave Groups** (`!leavegroup <group_id>`)
- **List Groups** (`!listgroups`)
- **Group Info** (`!groupinfo <group_id>`)

## Setup

1. **Install Python 3.8+**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a Discord Bot:**
   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the bot token

4. **Configure the bot:**
   - Copy `.env.example` to `.env`
   - Add your bot token to the `.env` file

5. **Invite the bot to your server:**
   - Go to OAuth2 > URL Generator
   - Select "bot" scope
   - Select permissions: Send Messages, Use Slash Commands, Add Reactions, Read Message History
   - Use the generated URL to invite your bot

6. **Run the bot:**
   ```bash
   python bot.py
   ```

## Commands

Use `!help` to see all available commands in Discord!

## File Structure

```
discord-bot/
├── bot.py              # Main bot file
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── cogs/              # Bot modules
│   ├── games.py       # Game commands
│   ├── group_finder.py # Group finder system
│   └── integrations.py # Fun integrations
└── data/              # Data storage (auto-created)
    └── groups.json    # Group data
```

## Customization

- Edit `config.py` to change colors, timeouts, and other settings
- Add new commands to the appropriate cog files
- Modify the command prefix (default: `!`)

Enjoy your new Discord bot! 🚀