#!/bin/bash

echo "🚀 Setting up Discord Bot..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your Discord bot token"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python bot.py"
echo ""
echo "To invite your bot to a server, use this URL:"
echo "https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=2147486720&scope=bot"
echo "(Replace YOUR_BOT_CLIENT_ID with your actual bot's client ID)"