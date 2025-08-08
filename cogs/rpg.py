import discord
from discord.ext import commands
import json
import os
from config import COLORS, STARTING_GOLD
from rpg.equipment_renderer import create_equipment_file
from rpg.rpgService import RpgService


class Rpg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/rpg/rpg.json'
        self.equipment_file = 'data/rpg/equipment.json'
        self.rpg_service = RpgService()

    @commands.command(name='stats', aliases=['stat'])
    async def check_stats(self, ctx, member: discord.Member = None):
        """Check your or someone else's balance"""
        target = member or ctx.author
        user_data = self.rpg_service.get_user_data(target.id)

        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Stats",
            color=COLORS['primary']
        )

        embed.add_field(name="Level", value=f"{user_data['level']:,}", inline=True)
        embed.add_field(name="HP", value=f"{user_data['hp']:,}", inline=True)
        embed.add_field(name="MP", value=f"{user_data['mp']:,}", inline=True)
        embed.add_field(name="Gold", value=f"{user_data['gold']:,} Gold", inline=True)
        embed.add_field(name="Equipment", value=f"{self.rpg_service.get_equipment_string(user_data['equipment'])}", inline=True)

        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)

        await ctx.send(embed=embed)

    @commands.command(name='equipment', aliases=['eq'])
    async def show_equipment(self, ctx, member: discord.Member = None):
        """show an image of the equipment"""
        target = member or ctx.author
        user_data = self.rpg_service.get_user_data(target.id)

        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Equipment",
            color=COLORS['primary'],
            type='image'
        )

        equipment = self.rpg_service.load_equipment_data()[str(user_data['equipment'][0])]
        image = create_equipment_file(equipment)


        await ctx.send(embed=embed, file=image)


async def setup(bot):
    await bot.add_cog(Rpg(bot))