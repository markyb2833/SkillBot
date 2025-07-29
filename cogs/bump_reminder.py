import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
import asyncio
from config import COLORS

class BumpReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/bump_reminder.json'
        self.settings = self.load_settings()
        self.bump_reminder_task.start()

    def load_settings(self):
        """Load bump reminder settings from JSON file"""
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
        """Save bump reminder settings to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def get_guild_settings(self, guild_id):
        """Get settings for a specific guild"""
        guild_key = str(guild_id)
        if guild_key not in self.settings:
            self.settings[guild_key] = {
                'bump_channel': None,
                'reminder_enabled': False,
                'last_bump': None,
                'bump_count': 0,
                'reward_coins': 100,
                'reminder_role': None,
                'last_bumper': None
            }
            self.save_settings()
        return self.settings[guild_key]

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for successful bump messages from Disboard"""
        if message.author.id != 302050872383242240:  # Disboard bot ID
            return
        
        if not message.embeds:
            return
        
        embed = message.embeds[0]
        
        # Check if this is a successful bump message
        if embed.description and "Bump done!" in embed.description:
            # Find who used the bump command by looking at recent messages
            bumper = None
            try:
                async for msg in message.channel.history(limit=10, before=message):
                    if msg.content.lower().strip() in ['/bump', '!d bump']:
                        bumper = msg.author
                        break
            except:
                pass
            
            await self.handle_successful_bump(message.guild, message.channel, bumper)

    async def handle_successful_bump(self, guild, channel, bumper):
        """Handle a successful bump"""
        settings = self.get_guild_settings(guild.id)
        
        # Update bump data
        settings['last_bump'] = datetime.now().isoformat()
        settings['bump_count'] += 1
        if bumper:
            settings['last_bumper'] = {
                'id': bumper.id,
                'name': str(bumper),
                'display_name': bumper.display_name
            }
        self.save_settings()
        
        # Reward the bumper with coins if economy system is available
        if bumper:
            economy_cog = self.bot.get_cog('Economy')
            if economy_cog and settings['reward_coins'] > 0:
                economy_cog.update_balance(bumper.id, settings['reward_coins'])
                
                # Send reward notification
                reward_embed = discord.Embed(
                    title="🎉 Bump Reward!",
                    description=f"Thanks for bumping the server, {bumper.mention}!",
                    color=COLORS['success']
                )
                reward_embed.add_field(
                    name="💰 Reward",
                    value=f"+{settings['reward_coins']} coins",
                    inline=True
                )
                reward_embed.add_field(
                    name="📊 Server Bumps",
                    value=f"Total: {settings['bump_count']}",
                    inline=True
                )
                reward_embed.set_footer(text="Keep helping our server grow! 🚀")
                
                try:
                    await channel.send(embed=reward_embed, delete_after=30)
                except:
                    pass

    @tasks.loop(minutes=30)  # Check every 30 minutes
    async def bump_reminder_task(self):
        """Check if any servers need bump reminders"""
        for guild_id, settings in self.settings.items():
            if not settings['reminder_enabled'] or not settings['bump_channel']:
                continue
            
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            
            channel = guild.get_channel(settings['bump_channel'])
            if not channel:
                continue
            
            # Check if it's time for a reminder
            if settings['last_bump']:
                last_bump = datetime.fromisoformat(settings['last_bump'])
                time_since_bump = datetime.now() - last_bump
                
                # Disboard allows bumping every 2 hours
                if time_since_bump >= timedelta(hours=2):
                    await self.send_bump_reminder(channel, settings, guild)

    async def send_bump_reminder(self, channel, settings, guild):
        """Send a bump reminder to the channel"""
        embed = discord.Embed(
            title="⏰ Time to Bump!",
            description="It's been 2+ hours since the last bump. Help grow our server!",
            color=COLORS['primary']
        )
        
        embed.add_field(
            name="🚀 How to Bump",
            value="Type `/bump` to bump our server on Disboard!",
            inline=False
        )
        
        embed.add_field(
            name="💰 Reward",
            value=f"Get **{settings['reward_coins']} coins** for bumping!",
            inline=True
        )
        
        embed.add_field(
            name="📊 Total Bumps",
            value=f"{settings['bump_count']} bumps so far",
            inline=True
        )
        
        # Add last bumper info if available
        if settings['last_bumper']:
            last_bumper = settings['last_bumper']
            embed.add_field(
                name="👤 Last Bumper",
                value=f"{last_bumper['display_name']} - Thanks! 🎉",
                inline=True
            )
        
        embed.set_footer(text="Bumping helps new members find our gaming community!")
        
        # Mention role if set
        mention_text = ""
        if settings['reminder_role']:
            role = guild.get_role(settings['reminder_role'])
            if role:
                mention_text = f"{role.mention} "
        
        try:
            await channel.send(mention_text, embed=embed)
        except:
            pass

    @bump_reminder_task.before_loop
    async def before_bump_reminder_task(self):
        """Wait until bot is ready before starting the task"""
        await self.bot.wait_until_ready()

    @commands.command(name='setbumpchannel', aliases=['sbc'])
    @commands.has_permissions(manage_channels=True)
    async def set_bump_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the bump reminder channel (Manage Channels permission required)"""
        if channel is None:
            channel = ctx.channel
        
        settings = self.get_guild_settings(ctx.guild.id)
        settings['bump_channel'] = channel.id
        self.save_settings()
        
        embed = discord.Embed(
            title="✅ Bump Channel Set",
            description=f"Bump reminders will be sent to {channel.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="📋 Next Steps",
            value="Use `!togglebumpreminder` to enable reminders",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='togglebumpreminder', aliases=['tbr'])
    @commands.has_permissions(manage_channels=True)
    async def toggle_bump_reminder(self, ctx):
        """Toggle bump reminders on/off (Manage Channels permission required)"""
        settings = self.get_guild_settings(ctx.guild.id)
        settings['reminder_enabled'] = not settings['reminder_enabled']
        self.save_settings()
        
        status = "enabled" if settings['reminder_enabled'] else "disabled"
        color = COLORS['success'] if settings['reminder_enabled'] else COLORS['warning']
        
        embed = discord.Embed(
            title=f"✅ Bump Reminders {status.title()}",
            description=f"Bump reminders are now **{status}**",
            color=color
        )
        
        if settings['reminder_enabled'] and not settings['bump_channel']:
            embed.add_field(
                name="⚠️ Setup Required",
                value="Set a bump channel with `!setbumpchannel` first!",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='setbumpreward', aliases=['sbr'])
    @commands.has_permissions(manage_channels=True)
    async def set_bump_reward(self, ctx, coins: int):
        """Set coin reward for bumping (Manage Channels permission required)"""
        if coins < 0:
            await ctx.send("❌ Reward must be 0 or positive!")
            return
        
        settings = self.get_guild_settings(ctx.guild.id)
        settings['reward_coins'] = coins
        self.save_settings()
        
        embed = discord.Embed(
            title="✅ Bump Reward Set",
            description=f"Users will now receive **{coins} coins** for bumping",
            color=COLORS['success']
        )
        
        if coins == 0:
            embed.description = "Bump rewards have been **disabled**"
            embed.color = COLORS['warning']
        
        await ctx.send(embed=embed)

    @commands.command(name='setbumprole', aliases=['sbro'])
    @commands.has_permissions(manage_channels=True)
    async def set_bump_role(self, ctx, role: discord.Role = None):
        """Set role to mention for bump reminders (Manage Channels permission required)"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        if role is None:
            settings['reminder_role'] = None
            embed = discord.Embed(
                title="✅ Bump Role Removed",
                description="No role will be mentioned in bump reminders",
                color=COLORS['success']
            )
        else:
            settings['reminder_role'] = role.id
            embed = discord.Embed(
                title="✅ Bump Role Set",
                description=f"{role.mention} will be mentioned in bump reminders",
                color=COLORS['success']
            )
        
        self.save_settings()
        await ctx.send(embed=embed)

    @commands.command(name='bumpstats', aliases=['bs'])
    async def bump_stats(self, ctx):
        """Show bump statistics for this server"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Bump Statistics",
            color=COLORS['info']
        )
        
        # Basic stats
        embed.add_field(
            name="🚀 Total Bumps",
            value=f"{settings['bump_count']} bumps",
            inline=True
        )
        
        # Last bump info
        if settings['last_bump']:
            last_bump = datetime.fromisoformat(settings['last_bump'])
            time_ago = datetime.now() - last_bump
            
            if time_ago.days > 0:
                time_str = f"{time_ago.days} day{'s' if time_ago.days != 1 else ''} ago"
            elif time_ago.seconds > 3600:
                hours = time_ago.seconds // 3600
                time_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                minutes = time_ago.seconds // 60
                time_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            
            embed.add_field(
                name="⏰ Last Bump",
                value=time_str,
                inline=True
            )
            
            # Next bump availability
            next_bump = last_bump + timedelta(hours=2)
            if datetime.now() >= next_bump:
                embed.add_field(
                    name="✅ Next Bump",
                    value="Available now!",
                    inline=True
                )
            else:
                time_until = next_bump - datetime.now()
                minutes_left = time_until.seconds // 60
                embed.add_field(
                    name="⏳ Next Bump",
                    value=f"In {minutes_left} minutes",
                    inline=True
                )
        else:
            embed.add_field(
                name="⏰ Last Bump",
                value="Never",
                inline=True
            )
            embed.add_field(
                name="✅ Next Bump",
                value="Available now!",
                inline=True
            )
        
        # Last bumper
        if settings['last_bumper']:
            last_bumper = settings['last_bumper']
            embed.add_field(
                name="👤 Last Bumper",
                value=f"{last_bumper['display_name']} 🎉",
                inline=True
            )
        
        # Settings
        bump_channel = ctx.guild.get_channel(settings['bump_channel']) if settings['bump_channel'] else None
        reminder_status = "✅ Enabled" if settings['reminder_enabled'] else "❌ Disabled"
        
        embed.add_field(
            name="⚙️ Settings",
            value=f"**Reminders:** {reminder_status}\n**Channel:** {bump_channel.mention if bump_channel else 'Not set'}\n**Reward:** {settings['reward_coins']} coins",
            inline=False
        )
        
        embed.set_footer(text="Use /bump to help grow our server!")
        
        await ctx.send(embed=embed)

    @commands.command(name='manualbump', aliases=['mb'])
    @commands.has_permissions(manage_channels=True)
    async def manual_bump_record(self, ctx):
        """Manually record a bump (for testing or if auto-detection failed)"""
        await self.handle_successful_bump(ctx.guild, ctx.channel, ctx.author)
        
        embed = discord.Embed(
            title="✅ Bump Recorded",
            description="Manually recorded a bump for testing purposes",
            color=COLORS['success']
        )
        
        await ctx.send(embed=embed, delete_after=10)

    @set_bump_channel.error
    @toggle_bump_reminder.error
    @set_bump_reward.error
    @set_bump_role.error
    @manual_bump_record.error
    async def bump_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Channels' permission to use this command!")

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.bump_reminder_task.cancel()

async def setup(bot):
    await bot.add_cog(BumpReminder(bot))