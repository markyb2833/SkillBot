import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from config import COLORS

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/welcome.json'
        self.settings = self.load_settings()

    def load_settings(self):
        """Load welcome settings from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_settings(self):
        """Save welcome settings to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def get_guild_settings(self, guild_id):
        """Get settings for a specific guild"""
        guild_key = str(guild_id)
        if guild_key not in self.settings:
            self.settings[guild_key] = {
                'welcome_channel': None,
                'leave_channel': None,
                'welcome_enabled': True,
                'leave_enabled': True,
                'welcome_message': None,
                'leave_message': None
            }
            self.save_settings()
        return self.settings[guild_key]

    def get_default_welcome_message(self, member):
        """Get the default welcome message"""
        return (
            f"🎮 **Welcome to the server, {member.mention}!** 🎮\n\n"
            f"🌟 **Gaming for all skill levels!** Whether you're a pro or just starting out, "
            f"you'll find your place here.\n\n"
            f"🎯 **Get started:**\n"
            f"• Check out our game roles with `!searchgame`\n"
            f"• Try your luck with `!daily` for free coins\n"
            f"• Find teammates with `!lfg`\n\n"
            f"🎉 **Have fun and game on!**"
        )

    def get_default_leave_message(self, member):
        """Get the default leave message"""
        return f"👋 **{member.display_name}** has left the server. Thanks for gaming with us!"

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events"""
        if member.bot:
            return  # Don't welcome bots
        
        settings = self.get_guild_settings(member.guild.id)
        
        if not settings['welcome_enabled']:
            return
        
        welcome_channel_id = settings['welcome_channel']
        if not welcome_channel_id:
            return
        
        welcome_channel = member.guild.get_channel(welcome_channel_id)
        if not welcome_channel:
            return
        
        # Get welcome message
        if settings['welcome_message']:
            message = settings['welcome_message'].replace('{user}', member.mention).replace('{username}', member.display_name)
        else:
            message = self.get_default_welcome_message(member)
        
        # Create welcome embed
        embed = discord.Embed(
            title="🎮 New Player Joined!",
            description=message,
            color=COLORS['success']
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(
            name="📊 Member Count",
            value=f"You're member #{member.guild.member_count}!",
            inline=True
        )
        embed.add_field(
            name="📅 Account Created",
            value=member.created_at.strftime("%B %d, %Y"),
            inline=True
        )
        embed.set_footer(
            text=f"Welcome to {member.guild.name}!",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        
        try:
            await welcome_channel.send(embed=embed)
        except discord.Forbidden:
            pass  # No permission to send messages

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave events"""
        if member.bot:
            return  # Don't announce bot leaves
        
        settings = self.get_guild_settings(member.guild.id)
        
        if not settings['leave_enabled']:
            return
        
        leave_channel_id = settings['leave_channel']
        if not leave_channel_id:
            return
        
        leave_channel = member.guild.get_channel(leave_channel_id)
        if not leave_channel:
            return
        
        # Get leave message
        if settings['leave_message']:
            message = settings['leave_message'].replace('{user}', member.mention).replace('{username}', member.display_name)
        else:
            message = self.get_default_leave_message(member)
        
        # Create leave embed
        embed = discord.Embed(
            title="👋 Player Left",
            description=message,
            color=COLORS['warning']
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(
            name="📊 Member Count",
            value=f"Now {member.guild.member_count} members",
            inline=True
        )
        embed.add_field(
            name="⏰ Time in Server",
            value=self.get_time_in_server(member),
            inline=True
        )
        embed.set_footer(
            text=f"Goodbye from {member.guild.name}",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        
        try:
            await leave_channel.send(embed=embed)
        except discord.Forbidden:
            pass  # No permission to send messages

    def get_time_in_server(self, member):
        """Calculate how long a member was in the server"""
        if not member.joined_at:
            return "Unknown"
        
        time_diff = datetime.now(member.joined_at.tzinfo) - member.joined_at
        days = time_diff.days
        
        if days < 1:
            hours = time_diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        elif days < 30:
            return f"{days} day{'s' if days != 1 else ''}"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months != 1 else ''}"
        else:
            years = days // 365
            return f"{years} year{'s' if years != 1 else ''}"

    @commands.command(name='setwelcomechannel', aliases=['swc'])
    @commands.has_permissions(manage_channels=True)
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the welcome channel (Manage Channels permission required)"""
        if channel is None:
            channel = ctx.channel
        
        settings = self.get_guild_settings(ctx.guild.id)
        settings['welcome_channel'] = channel.id
        self.save_settings()
        
        embed = discord.Embed(
            title="✅ Welcome Channel Set",
            description=f"Welcome messages will now be sent to {channel.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="📋 Current Settings",
            value=f"**Welcome:** {'Enabled' if settings['welcome_enabled'] else 'Disabled'}\n**Channel:** {channel.mention}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='setleavechannel', aliases=['slc'])
    @commands.has_permissions(manage_channels=True)
    async def set_leave_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the leave channel (Manage Channels permission required)"""
        if channel is None:
            channel = ctx.channel
        
        settings = self.get_guild_settings(ctx.guild.id)
        settings['leave_channel'] = channel.id
        self.save_settings()
        
        embed = discord.Embed(
            title="✅ Leave Channel Set",
            description=f"Leave messages will now be sent to {channel.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="📋 Current Settings",
            value=f"**Leave:** {'Enabled' if settings['leave_enabled'] else 'Disabled'}\n**Channel:** {channel.mention}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='welcometoggle', aliases=['wt'])
    @commands.has_permissions(manage_channels=True)
    async def toggle_welcome(self, ctx):
        """Toggle welcome messages on/off (Manage Channels permission required)"""
        settings = self.get_guild_settings(ctx.guild.id)
        settings['welcome_enabled'] = not settings['welcome_enabled']
        self.save_settings()
        
        status = "enabled" if settings['welcome_enabled'] else "disabled"
        color = COLORS['success'] if settings['welcome_enabled'] else COLORS['warning']
        
        embed = discord.Embed(
            title=f"✅ Welcome Messages {status.title()}",
            description=f"Welcome messages are now **{status}**",
            color=color
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='leavetoggle', aliases=['lt'])
    @commands.has_permissions(manage_channels=True)
    async def toggle_leave(self, ctx):
        """Toggle leave messages on/off (Manage Channels permission required)"""
        settings = self.get_guild_settings(ctx.guild.id)
        settings['leave_enabled'] = not settings['leave_enabled']
        self.save_settings()
        
        status = "enabled" if settings['leave_enabled'] else "disabled"
        color = COLORS['success'] if settings['leave_enabled'] else COLORS['warning']
        
        embed = discord.Embed(
            title=f"✅ Leave Messages {status.title()}",
            description=f"Leave messages are now **{status}**",
            color=color
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='welcomepreview', aliases=['wp'])
    @commands.has_permissions(manage_channels=True)
    async def preview_welcome(self, ctx, member: discord.Member = None):
        """Preview the welcome message (Manage Channels permission required)"""
        if member is None:
            member = ctx.author
        
        settings = self.get_guild_settings(ctx.guild.id)
        
        # Get welcome message
        if settings['welcome_message']:
            message = settings['welcome_message'].replace('{user}', member.mention).replace('{username}', member.display_name)
        else:
            message = self.get_default_welcome_message(member)
        
        # Create preview embed
        embed = discord.Embed(
            title="🎮 New Player Joined! (PREVIEW)",
            description=message,
            color=COLORS['info']
        )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(
            name="📊 Member Count",
            value=f"You're member #{ctx.guild.member_count}!",
            inline=True
        )
        embed.add_field(
            name="📅 Account Created",
            value=member.created_at.strftime("%B %d, %Y"),
            inline=True
        )
        embed.set_footer(
            text=f"Welcome to {ctx.guild.name}! (This is a preview)",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='welcomestatus', aliases=['ws'])
    async def welcome_status(self, ctx):
        """Show current welcome/leave settings"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="📋 Welcome & Leave Settings",
            color=COLORS['info']
        )
        
        # Welcome settings
        welcome_channel = ctx.guild.get_channel(settings['welcome_channel']) if settings['welcome_channel'] else None
        welcome_status = "✅ Enabled" if settings['welcome_enabled'] else "❌ Disabled"
        welcome_channel_text = welcome_channel.mention if welcome_channel else "Not set"
        
        embed.add_field(
            name="🎮 Welcome Messages",
            value=f"**Status:** {welcome_status}\n**Channel:** {welcome_channel_text}",
            inline=True
        )
        
        # Leave settings
        leave_channel = ctx.guild.get_channel(settings['leave_channel']) if settings['leave_channel'] else None
        leave_status = "✅ Enabled" if settings['leave_enabled'] else "❌ Disabled"
        leave_channel_text = leave_channel.mention if leave_channel else "Not set"
        
        embed.add_field(
            name="👋 Leave Messages",
            value=f"**Status:** {leave_status}\n**Channel:** {leave_channel_text}",
            inline=True
        )
        
        # Commands
        embed.add_field(
            name="🔧 Management Commands",
            value=(
                "`!setwelcomechannel` - Set welcome channel\n"
                "`!setleavechannel` - Set leave channel\n"
                "`!welcometoggle` - Toggle welcome messages\n"
                "`!leavetoggle` - Toggle leave messages\n"
                "`!welcomepreview` - Preview welcome message"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @set_welcome_channel.error
    @set_leave_channel.error
    @toggle_welcome.error
    @toggle_leave.error
    @preview_welcome.error
    async def welcome_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Channels' permission to use this command!")

async def setup(bot):
    await bot.add_cog(Welcome(bot))