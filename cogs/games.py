import discord
from discord.ext import commands
import random
import asyncio
from config import COLORS, GAME_TIMEOUT

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @commands.command(name='rps')
    async def rock_paper_scissors(self, ctx, choice: str = None):
        """Play Rock Paper Scissors! Usage: !rps rock/paper/scissors"""
        if not choice:
            await ctx.send("🎮 Choose: `!rps rock`, `!rps paper`, or `!rps scissors`")
            return
        
        choices = ['rock', 'paper', 'scissors']
        choice = choice.lower()
        
        if choice not in choices:
            await ctx.send("❌ Invalid choice! Use rock, paper, or scissors.")
            return
        
        bot_choice = random.choice(choices)
        
        # Determine winner
        if choice == bot_choice:
            result = "It's a tie!"
            color = COLORS['warning']
        elif (choice == 'rock' and bot_choice == 'scissors') or \
             (choice == 'paper' and bot_choice == 'rock') or \
             (choice == 'scissors' and bot_choice == 'paper'):
            result = "You win! 🎉"
            color = COLORS['success']
        else:
            result = "I win! 😎"
            color = COLORS['error']
        
        embed = discord.Embed(
            title="🎮 Rock Paper Scissors",
            description=f"You: {choice.capitalize()}\nMe: {bot_choice.capitalize()}\n\n**{result}**",
            color=color
        )
        await ctx.send(embed=embed)



    @commands.command(name='dice')
    async def roll_dice(self, ctx, sides: int = 6, count: int = 1):
        """Roll dice! Usage: !dice [sides] [count]"""
        if sides < 2 or sides > 100:
            await ctx.send("❌ Dice must have between 2 and 100 sides!")
            return
        
        if count < 1 or count > 10:
            await ctx.send("❌ You can roll between 1 and 10 dice!")
            return
        
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"**Rolls:** {', '.join(map(str, rolls))}\n**Total:** {total}",
            color=COLORS['primary']
        )
        embed.set_footer(text=f"{count}d{sides}")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))