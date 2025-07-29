import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from config import COLORS

class AuditLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/audit_log.json'
        self.settings = self.load_settings()

    def load_settings(self):
        """Load audit log settings from JSON file"""
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
        """Save audit log settings to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def get_guild_settings(self, guild_id):
        """Get settings for a specific guild"""
        guild_key = str(guild_id)
        if guild_key not in self.settings:
            self.settings[guild_key] = {
                'audit_channel': None,
                'enabled': False,
                'track_messages': True,
                'track_members': True,
                'track_roles': True,
                'track_channels': True,
                'track_voice': True
            }
            self.save_settings()
        return self.settings[guild_key]

    async def send_audit_log(self, guild, embed):
        """Send an audit log embed to the configured channel"""
        settings = self.get_guild_settings(guild.id)
        
        if not settings['enabled'] or not settings['audit_channel']:
            return
        
        channel = guild.get_channel(settings['audit_channel'])
        if not channel:
            return
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass  # No permission to send messages

    # Message Events
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Track deleted messages"""
        if message.author.bot or not message.guild:
            return
        
        settings = self.get_guild_settings(message.guild.id)
        if not settings['track_messages']:
            return
        
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=COLORS['error'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Author",
            value=f"{message.author.mention} ({message.author})",
            inline=True
        )
        
        embed.add_field(
            name="📍 Channel",
            value=f"{message.channel.mention}",
            inline=True
        )
        
        embed.add_field(
            name="🆔 Message ID",
            value=f"`{message.id}`",
            inline=True
        )
        
        # Message content (truncated if too long)
        content = message.content or "*No text content*"
        if len(content) > 1000:
            content = content[:997] + "..."
        
        embed.add_field(
            name="📝 Content",
            value=f"```{content}```",
            inline=False
        )
        
        # Attachments
        if message.attachments:
            attachment_info = []
            for attachment in message.attachments[:3]:  # Max 3 attachments
                attachment_info.append(f"📎 {attachment.filename} ({attachment.size} bytes)")
            embed.add_field(
                name="📎 Attachments",
                value="\n".join(attachment_info),
                inline=False
            )
        
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
        )
        
        await self.send_audit_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Track edited messages"""
        if before.author.bot or not before.guild or before.content == after.content:
            return
        
        settings = self.get_guild_settings(before.guild.id)
        if not settings['track_messages']:
            return
        
        embed = discord.Embed(
            title="✏️ Message Edited",
            color=COLORS['warning'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Author",
            value=f"{before.author.mention} ({before.author})",
            inline=True
        )
        
        embed.add_field(
            name="📍 Channel",
            value=f"{before.channel.mention}",
            inline=True
        )
        
        embed.add_field(
            name="🆔 Message ID",
            value=f"`{before.id}`",
            inline=True
        )
        
        # Before content
        before_content = before.content or "*No text content*"
        if len(before_content) > 500:
            before_content = before_content[:497] + "..."
        
        embed.add_field(
            name="📝 Before",
            value=f"```{before_content}```",
            inline=False
        )
        
        # After content
        after_content = after.content or "*No text content*"
        if len(after_content) > 500:
            after_content = after_content[:497] + "..."
        
        embed.add_field(
            name="📝 After",
            value=f"```{after_content}```",
            inline=False
        )
        
        embed.set_author(
            name=before.author.display_name,
            icon_url=before.author.avatar.url if before.author.avatar else before.author.default_avatar.url
        )
        
        await self.send_audit_log(before.guild, embed)

    # Member Events
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Track member joins"""
        settings = self.get_guild_settings(member.guild.id)
        if not settings['track_members']:
            return
        
        embed = discord.Embed(
            title="📥 Member Joined",
            color=COLORS['success'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Member",
            value=f"{member.mention} ({member})",
            inline=True
        )
        
        embed.add_field(
            name="🆔 User ID",
            value=f"`{member.id}`",
            inline=True
        )
        
        embed.add_field(
            name="📊 Member Count",
            value=f"{member.guild.member_count}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Account Created",
            value=f"{member.created_at.strftime('%B %d, %Y at %I:%M %p')}",
            inline=True
        )
        
        # Account age
        account_age = datetime.now(member.created_at.tzinfo) - member.created_at
        if account_age.days < 7:
            embed.add_field(
                name="⚠️ Account Age",
                value=f"**{account_age.days} days old** (New account)",
                inline=True
            )
        else:
            embed.add_field(
                name="📆 Account Age",
                value=f"{account_age.days} days old",
                inline=True
            )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await self.send_audit_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Track member leaves"""
        settings = self.get_guild_settings(member.guild.id)
        if not settings['track_members']:
            return
        
        embed = discord.Embed(
            title="📤 Member Left",
            color=COLORS['error'],
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👤 Member",
            value=f"{member.mention} ({member})",
            inline=True
        )
        
        embed.add_field(
            name="🆔 User ID",
            value=f"`{member.id}`",
            inline=True
        )
        
        embed.add_field(
            name="📊 Member Count",
            value=f"{member.guild.member_count}",
            inline=True
        )
        
        # Time in server
        if member.joined_at:
            time_in_server = datetime.now(member.joined_at.tzinfo) - member.joined_at
            if time_in_server.days > 0:
                time_str = f"{time_in_server.days} days"
            else:
                hours = time_in_server.seconds // 3600
                time_str = f"{hours} hours"
            
            embed.add_field(
                name="⏰ Time in Server",
                value=time_str,
                inline=True
            )
        
        # Roles they had
        if member.roles[1:]:  # Exclude @everyone
            roles = [role.mention for role in member.roles[1:][:10]]  # Max 10 roles
            embed.add_field(
                name="🎭 Roles",
                value=" ".join(roles),
                inline=False
            )
        
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await self.send_audit_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Track member updates (nickname, roles)"""
        settings = self.get_guild_settings(before.guild.id)
        if not settings['track_members']:
            return
        
        # Nickname change
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Nickname Changed",
                color=COLORS['info'],
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Member",
                value=f"{after.mention} ({after})",
                inline=True
            )
            
            embed.add_field(
                name="📝 Before",
                value=before.nick or "*No nickname*",
                inline=True
            )
            
            embed.add_field(
                name="📝 After",
                value=after.nick or "*No nickname*",
                inline=True
            )
            
            embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)
            
            await self.send_audit_log(before.guild, embed)
        
        # Role changes
        if settings['track_roles'] and before.roles != after.roles:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            if added_roles:
                embed = discord.Embed(
                    title="➕ Roles Added",
                    color=COLORS['success'],
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="👤 Member",
                    value=f"{after.mention} ({after})",
                    inline=True
                )
                
                embed.add_field(
                    name="🎭 Added Roles",
                    value=" ".join([role.mention for role in added_roles]),
                    inline=False
                )
                
                embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)
                
                await self.send_audit_log(before.guild, embed)
            
            if removed_roles:
                embed = discord.Embed(
                    title="➖ Roles Removed",
                    color=COLORS['warning'],
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="👤 Member",
                    value=f"{after.mention} ({after})",
                    inline=True
                )
                
                embed.add_field(
                    name="🎭 Removed Roles",
                    value=" ".join([role.mention for role in removed_roles]),
                    inline=False
                )
                
                embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)
                
                await self.send_audit_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        """Track user updates (username, avatar)"""
        # Check all mutual guilds
        for guild in self.bot.guilds:
            if guild.get_member(before.id):
                settings = self.get_guild_settings(guild.id)
                if not settings['track_members']:
                    continue
                
                # Username change
                if before.name != after.name:
                    embed = discord.Embed(
                        title="👤 Username Changed",
                        color=COLORS['info'],
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(
                        name="👤 User",
                        value=f"{after.mention} (`{after.id}`)",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="📝 Before",
                        value=f"`{before.name}`",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="📝 After",
                        value=f"`{after.name}`",
                        inline=True
                    )
                    
                    embed.set_thumbnail(url=after.avatar.url if after.avatar else after.default_avatar.url)
                    
                    await self.send_audit_log(guild, embed)
                
                # Avatar change
                if before.avatar != after.avatar:
                    embed = discord.Embed(
                        title="🖼️ Avatar Changed",
                        color=COLORS['info'],
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(
                        name="👤 User",
                        value=f"{after.mention} ({after})",
                        inline=True
                    )
                    
                    if before.avatar:
                        embed.set_image(url=after.avatar.url if after.avatar else after.default_avatar.url)
                        embed.set_thumbnail(url=before.avatar.url)
                        embed.add_field(
                            name="🖼️ Change",
                            value="New avatar shown above, old avatar in thumbnail",
                            inline=False
                        )
                    else:
                        embed.set_image(url=after.avatar.url if after.avatar else after.default_avatar.url)
                        embed.add_field(
                            name="🖼️ Change",
                            value="User set their first avatar",
                            inline=False
                        )
                    
                    await self.send_audit_log(guild, embed)

    # Voice Events
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track voice channel activity"""
        settings = self.get_guild_settings(member.guild.id)
        if not settings['track_voice']:
            return
        
        # Joined voice channel
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🔊 Joined Voice Channel",
                color=COLORS['success'],
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Member",
                value=f"{member.mention} ({member})",
                inline=True
            )
            
            embed.add_field(
                name="📍 Channel",
                value=f"🔊 {after.channel.name}",
                inline=True
            )
            
            await self.send_audit_log(member.guild, embed)
        
        # Left voice channel
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🔇 Left Voice Channel",
                color=COLORS['warning'],
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Member",
                value=f"{member.mention} ({member})",
                inline=True
            )
            
            embed.add_field(
                name="📍 Channel",
                value=f"🔊 {before.channel.name}",
                inline=True
            )
            
            await self.send_audit_log(member.guild, embed)
        
        # Moved between voice channels
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            embed = discord.Embed(
                title="🔄 Moved Voice Channels",
                color=COLORS['info'],
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Member",
                value=f"{member.mention} ({member})",
                inline=True
            )
            
            embed.add_field(
                name="📍 From",
                value=f"🔊 {before.channel.name}",
                inline=True
            )
            
            embed.add_field(
                name="📍 To",
                value=f"🔊 {after.channel.name}",
                inline=True
            )
            
            await self.send_audit_log(member.guild, embed)

    # Channel Events
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Track channel creation"""
        settings = self.get_guild_settings(channel.guild.id)
        if not settings['track_channels']:
            return
        
        embed = discord.Embed(
            title="➕ Channel Created",
            color=COLORS['success'],
            timestamp=datetime.now()
        )
        
        channel_type = "🔊 Voice" if isinstance(channel, discord.VoiceChannel) else "💬 Text"
        
        embed.add_field(
            name="📍 Channel",
            value=f"{channel_type} {channel.mention if hasattr(channel, 'mention') else channel.name}",
            inline=True
        )
        
        embed.add_field(
            name="🆔 Channel ID",
            value=f"`{channel.id}`",
            inline=True
        )
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(
                name="📁 Category",
                value=channel.category.name,
                inline=True
            )
        
        await self.send_audit_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Track channel deletion"""
        settings = self.get_guild_settings(channel.guild.id)
        if not settings['track_channels']:
            return
        
        embed = discord.Embed(
            title="🗑️ Channel Deleted",
            color=COLORS['error'],
            timestamp=datetime.now()
        )
        
        channel_type = "🔊 Voice" if isinstance(channel, discord.VoiceChannel) else "💬 Text"
        
        embed.add_field(
            name="📍 Channel",
            value=f"{channel_type} #{channel.name}",
            inline=True
        )
        
        embed.add_field(
            name="🆔 Channel ID",
            value=f"`{channel.id}`",
            inline=True
        )
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(
                name="📁 Category",
                value=channel.category.name,
                inline=True
            )
        
        await self.send_audit_log(channel.guild, embed)

    # Commands
    @commands.command(name='setauditchannel', aliases=['sac'])
    @commands.has_permissions(manage_guild=True)
    async def set_audit_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the audit log channel (Manage Server permission required)"""
        if channel is None:
            channel = ctx.channel
        
        settings = self.get_guild_settings(ctx.guild.id)
        settings['audit_channel'] = channel.id
        self.save_settings()
        
        embed = discord.Embed(
            title="✅ Audit Channel Set",
            description=f"Audit logs will be sent to {channel.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="📋 Next Steps",
            value="Use `!toggleaudit` to enable audit logging",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='toggleaudit', aliases=['ta'])
    @commands.has_permissions(manage_guild=True)
    async def toggle_audit(self, ctx):
        """Toggle audit logging on/off (Manage Server permission required)"""
        settings = self.get_guild_settings(ctx.guild.id)
        settings['enabled'] = not settings['enabled']
        self.save_settings()
        
        status = "enabled" if settings['enabled'] else "disabled"
        color = COLORS['success'] if settings['enabled'] else COLORS['warning']
        
        embed = discord.Embed(
            title=f"✅ Audit Logging {status.title()}",
            description=f"Audit logging is now **{status}**",
            color=color
        )
        
        if settings['enabled'] and not settings['audit_channel']:
            embed.add_field(
                name="⚠️ Setup Required",
                value="Set an audit channel with `!setauditchannel` first!",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='auditconfig', aliases=['ac'])
    @commands.has_permissions(manage_guild=True)
    async def audit_config(self, ctx, category: str = None, enabled: bool = None):
        """Configure what types of events to track (Manage Server permission required)"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        categories = {
            'messages': 'track_messages',
            'members': 'track_members', 
            'roles': 'track_roles',
            'channels': 'track_channels',
            'voice': 'track_voice'
        }
        
        if category is None or enabled is None:
            # Show current config
            embed = discord.Embed(
                title="⚙️ Audit Configuration",
                color=COLORS['info']
            )
            
            for cat_name, setting_key in categories.items():
                status = "✅ Enabled" if settings[setting_key] else "❌ Disabled"
                embed.add_field(
                    name=f"📋 {cat_name.title()}",
                    value=status,
                    inline=True
                )
            
            embed.add_field(
                name="💡 Usage",
                value="Use `!auditconfig <category> <true/false>` to change settings\nCategories: messages, members, roles, channels, voice",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        if category.lower() not in categories:
            await ctx.send("❌ Invalid category! Use: messages, members, roles, channels, voice")
            return
        
        setting_key = categories[category.lower()]
        settings[setting_key] = enabled
        self.save_settings()
        
        status = "enabled" if enabled else "disabled"
        color = COLORS['success'] if enabled else COLORS['warning']
        
        embed = discord.Embed(
            title=f"✅ {category.title()} Tracking {status.title()}",
            description=f"{category.title()} tracking is now **{status}**",
            color=color
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='auditstatus', aliases=['as'])
    async def audit_status(self, ctx):
        """Show current audit log settings"""
        settings = self.get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Audit Log Status",
            color=COLORS['info']
        )
        
        # Main status
        audit_channel = ctx.guild.get_channel(settings['audit_channel']) if settings['audit_channel'] else None
        main_status = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
        channel_text = audit_channel.mention if audit_channel else "Not set"
        
        embed.add_field(
            name="🔍 Audit Logging",
            value=f"**Status:** {main_status}\n**Channel:** {channel_text}",
            inline=False
        )
        
        # Tracking categories
        categories = {
            '💬 Messages': settings['track_messages'],
            '👥 Members': settings['track_members'],
            '🎭 Roles': settings['track_roles'],
            '📍 Channels': settings['track_channels'],
            '🔊 Voice': settings['track_voice']
        }
        
        enabled_cats = [name for name, enabled in categories.items() if enabled]
        disabled_cats = [name for name, enabled in categories.items() if not enabled]
        
        if enabled_cats:
            embed.add_field(
                name="✅ Tracking Enabled",
                value="\n".join(enabled_cats),
                inline=True
            )
        
        if disabled_cats:
            embed.add_field(
                name="❌ Tracking Disabled",
                value="\n".join(disabled_cats),
                inline=True
            )
        
        embed.add_field(
            name="🔧 Management Commands",
            value=(
                "`!setauditchannel` - Set audit channel\n"
                "`!toggleaudit` - Enable/disable logging\n"
                "`!auditconfig` - Configure tracking categories"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @set_audit_channel.error
    @toggle_audit.error
    @audit_config.error
    async def audit_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Server' permission to use this command!")

async def setup(bot):
    await bot.add_cog(AuditLog(bot))