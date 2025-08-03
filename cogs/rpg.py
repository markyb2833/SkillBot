import discord
from discord.ext import commands
import json
import os
from config import COLORS, STARTING_GOLD


class Rpg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/rpg/rpg.json'
        self.equipment_file = 'data/rpg/equipment.json'
        self.users = self.load_users()

    def load_users(self):
        """Load user rpg data from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')

        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_users(self):
        """Save user rpg data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.users, f, indent=2)


    def get_user_data(self, user_id):
        """Get or create user data"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'gold': STARTING_GOLD,
                'hp': 100,
                'mp': 10,
                'equipment': [1]
            }
            self.save_users()
        return self.users[user_id]

    @commands.command(name='stats', aliases=['stat'])
    async def check_balance(self, ctx, member: discord.Member = None):
        """Check your or someone else's balance"""
        target = member or ctx.author
        user_data = self.get_user_data(target.id)

        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Stats",
            color=COLORS['primary']
        )
        embed.add_field(name="Level", value=f"{user_data['level']:,}", inline=True)
        embed.add_field(name="HP", value=f"{user_data['hp']:,}", inline=True)
        embed.add_field(name="MP", value=f"{user_data['mp']:,}", inline=True)
        embed.add_field(name="Gold", value=f"{user_data['gold']:,} Gold", inline=True)

        for equipment in user_data['equipment']:
            equipmentText = str(self.equipment_file[equipment]['name']) #BANG

        embed.add_field(name="Equipment", value=f"{equipmentText:,}", inline=True)
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Rpg(bot))