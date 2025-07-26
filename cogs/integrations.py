import discord
from discord.ext import commands
import random
import aiohttp
from config import COLORS

class Integrations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='meme')
    async def random_meme(self, ctx):
        """Get a random meme from Reddit!"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://meme-api.com/gimme') as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        embed = discord.Embed(
                            title=data['title'],
                            color=COLORS['primary']
                        )
                        embed.set_image(url=data['url'])
                        embed.set_footer(text=f"👍 {data['ups']} | r/{data['subreddit']}")
                        
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("❌ Couldn't fetch a meme right now!")
        except:
            await ctx.send("❌ Meme service is unavailable!")

    @commands.command(name='joke')
    async def random_joke(self, ctx):
        """Get a random joke!"""
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "Why don't eggs tell jokes? They'd crack each other up!",
            "What do you call a fake noodle? An impasta!",
            "Why did the math book look so sad? Because it had too many problems!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why can't a bicycle stand up by itself? It's two tired!",
            "What do you call a sleeping bull? A bulldozer!",
            "Why did the cookie go to the doctor? Because it felt crumbly!",
            "What's the best thing about Switzerland? I don't know, but the flag is a big plus!"
        ]
        
        embed = discord.Embed(
            title="😂 Random Joke",
            description=random.choice(jokes),
            color=COLORS['primary']
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='quote')
    async def inspirational_quote(self, ctx):
        """Get an inspirational quote!"""
        quotes = [
            ("The only way to do great work is to love what you do.", "Steve Jobs"),
            ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
            ("Life is what happens to you while you're busy making other plans.", "John Lennon"),
            ("The future belongs to those who believe in the beauty of their dreams.", "Eleanor Roosevelt"),
            ("It is during our darkest moments that we must focus to see the light.", "Aristotle"),
            ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill"),
            ("The only impossible journey is the one you never begin.", "Tony Robbins"),
            ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
            ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
            ("The only person you are destined to become is the person you decide to be.", "Ralph Waldo Emerson")
        ]
        
        quote, author = random.choice(quotes)
        
        embed = discord.Embed(
            title="💭 Inspirational Quote",
            description=f'"{quote}"',
            color=COLORS['info']
        )
        embed.set_footer(text=f"— {author}")
        
        await ctx.send(embed=embed)

    @commands.command(name='poll')
    async def create_poll(self, ctx, question: str, *options):
        """Create a poll! Usage: !poll "Question?" "Option 1" "Option 2" ..."""
        if len(options) < 2:
            await ctx.send("❌ You need at least 2 options for a poll!")
            return
        
        if len(options) > 10:
            await ctx.send("❌ Maximum 10 options allowed!")
            return
        
        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        description = ""
        for i, option in enumerate(options):
            description += f"{reactions[i]} {option}\n"
        
        embed = discord.Embed(
            title=f"📊 {question}",
            description=description,
            color=COLORS['primary']
        )
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        
        message = await ctx.send(embed=embed)
        
        for i in range(len(options)):
            await message.add_reaction(reactions[i])



    @commands.command(name='choose')
    async def random_choice(self, ctx, *choices):
        """Let me choose for you! Usage: !choose option1 option2 option3"""
        if len(choices) < 2:
            await ctx.send("❌ Give me at least 2 options to choose from!")
            return
        
        choice = random.choice(choices)
        
        embed = discord.Embed(
            title="🎯 Random Choice",
            description=f"I choose: **{choice}**",
            color=COLORS['success']
        )
        embed.set_footer(text=f"From: {', '.join(choices)}")
        
        await ctx.send(embed=embed)

    @commands.command(name='remind')
    async def remind_me(self, ctx, time: int, *, message: str):
        """Set a reminder! Usage: !remind <minutes> <message>"""
        if time < 1 or time > 1440:  # Max 24 hours
            await ctx.send("❌ Reminder time must be between 1 and 1440 minutes (24 hours)!")
            return
        
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"I'll remind you in {time} minute(s): {message}",
            color=COLORS['success']
        )
        
        await ctx.send(embed=embed)
        
        # Wait and send reminder
        import asyncio
        await asyncio.sleep(time * 60)
        
        reminder_embed = discord.Embed(
            title="🔔 Reminder",
            description=f"{ctx.author.mention}, you asked me to remind you: {message}",
            color=COLORS['warning']
        )
        
        await ctx.send(embed=reminder_embed)

async def setup(bot):
    await bot.add_cog(Integrations(bot))