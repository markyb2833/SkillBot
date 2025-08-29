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

### 🎭 Role Management System
- **Multiple Panel Support** - Create separate panels for games, age, gender, etc.
- **Interactive Role Assignment** - Click buttons to get/remove roles
- **Admin Management** - Create, edit, and remove role buttons and panels
- **Persistent Panels** - Role panels automatically recover after bot restarts
- **Customizable Display** - Set custom labels and emojis for each role
- **Role Name Input** - Add roles by typing their names instead of copying IDs

### 🎯 Insult System
- **Tiered Insults** - Mild, Strong, and Cruel insult levels
- **Trigger Tracking** - Monitor specific phrases, words, or emojis
- **Automatic Responses** - Bot automatically insults users when triggers are used
- **Custom Insults** - Add your own insults to each tier
- **API Integration** - Fallback to Evil Insult Generator API
- **Trigger Statistics** - Track how many times each trigger has been activated

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

### 🎭 Role System Commands
- `!createrolepanel <panel_id> [channel]` - Create a role assignment panel (e.g., `!createrolepanel games`) (Admin only)
- `!displaypanel <panel_id> [channel]` - Display an existing panel in a channel (Admin only)
- `!movepanel <panel_id> <channel>` - Move a panel to a different channel (Admin only)
- `!removepanel <panel_id>` - Remove panel display (keeps data) (Admin only)
- `!listpanels` - List all panels and their display status (Admin only)
- `!adminrolepanel` - Open the role management admin panel (Admin only)

### 🎯 Insult System Commands
- `!insulton "trigger" [tier] @user` - Start tracking a phrase/emoji for a specific user (Admin only)
- `!insulton "trigger" [tier]` - Start tracking a phrase/emoji for everyone (Admin only)
- `!insultoff "trigger"` - Stop tracking a trigger (Admin only)
- `!listinsults` - List all active insult triggers (Admin only)
- `!addinsult <tier> <text>` - Add a custom insult to a tier (Admin only)
- `!removeinsult <tier> <index>` - Remove a custom insult by index (Admin only)
- `!listcustominsults` - List all custom insults by tier (Admin only)
- `!testinsult [tier] [@user]` - Test an insult of a specific tier (Admin only)

#### **Default Insult Management (All Users)**
- `!adddefaultinsult <tier> <text>` - Add an insult to the global default list (optional: include {user} tag)
- `!removedefaultinsult <tier> <index>` - Remove a default insult by index
- `!listdefaultinsults` - List all default insults by tier
- `!resetdefaultinsults` - Reset to original insult list (Admin only)
- `!insulthelp` - Show comprehensive help for the insult system
- `!insultexamples` - Show examples of different insult formats
- `!insultdebug [tier]` - Debug command to check available insults (Admin only)
- `!getemojiformat <emoji>` - Get the correct format for tracking emojis
- `!testinsulton <trigger> <user_or_tier> [tier]` - Test parameter parsing without setting up tracking
- `!testtier <tier>` - Test tier validation directly

## File Structure

```
discord-bot/
├── bot.py              # Main bot file
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── cogs/              # Bot modules
│   ├── games.py       # Game commands
│   ├── group_finder.py # Group finder system
│   ├── integrations.py # Fun integrations
│   ├── role_system.py # Role management system
│   └── insult_system.py # Insult system
└── data/              # Data storage (auto-created)
    ├── groups.json    # Group data
    ├── role_system.json # Role system data
    ├── insult_system.json # Insult system data
    └── default_insults.json # Default insult database
```

## Customization

- Edit `config.py` to change colors, timeouts, and other settings
- Add new commands to the appropriate cog files
- Modify the command prefix (default: `!`)

Enjoy your new Discord bot! 🚀