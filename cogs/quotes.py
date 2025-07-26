import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from config import COLORS

class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/quotes.json'
        self.quotes = self.load_quotes()

    def load_quotes(self):
        """Load quotes from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_quotes(self):
        """Save quotes to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.quotes, f, indent=2)

    def get_hof_channel(self, guild_id):
        """Get the Hall of Fame channel for a guild"""
        guild_key = str(guild_id)
        if guild_key in self.quotes and 'hof_channel' in self.quotes[guild_key]:
            return self.quotes[guild_key]['hof_channel']
        return None

    def set_hof_channel(self, guild_id, channel_id):
        """Set the Hall of Fame channel for a guild"""
        guild_key = str(guild_id)
        if guild_key not in self.quotes:
            self.quotes[guild_key] = {
                'quotes': [],
                'hof_channel': channel_id
            }
        else:
            self.quotes[guild_key]['hof_channel'] = channel_id
        self.save_quotes()

    def add_quote(self, guild_id, quote_data):
        """Add a quote to the database"""
        guild_key = str(guild_id)
        if guild_key not in self.quotes:
            self.quotes[guild_key] = {
                'quotes': [],
                'hof_channel': None
            }
        
        # Add unique ID
        quote_data['id'] = len(self.quotes[guild_key]['quotes']) + 1
        quote_data['added_at'] = datetime.now().isoformat()
        
        self.quotes[guild_key]['quotes'].append(quote_data)
        self.save_quotes()
        return quote_data['id']

    @commands.command(name='hof')
    async def hall_of_fame(self, ctx):
        """Add a message to Hall of Fame (reply to a message to quote it)"""
        # Check if this is a reply
        if not ctx.message.reference or not ctx.message.reference.message_id:
            await ctx.send("❌ You need to reply to a message to add it to Hall of Fame!")
            return

        # Get the referenced message
        try:
            channel = ctx.bot.get_channel(ctx.message.reference.channel_id)
            quoted_message = await channel.fetch_message(ctx.message.reference.message_id)
        except:
            await ctx.send("❌ Could not find the message you're trying to quote!")
            return

        # Check if Hall of Fame channel is set
        hof_channel_id = self.get_hof_channel(ctx.guild.id)
        print(f"DEBUG: HOF channel lookup for guild {ctx.guild.id}: {hof_channel_id}")
        print(f"DEBUG: Current quotes data: {self.quotes}")
        
        if not hof_channel_id:
            await ctx.send("❌ Hall of Fame channel not set! Use `!sethofchannel` first.")
            return

        hof_channel = ctx.guild.get_channel(hof_channel_id)
        if not hof_channel:
            await ctx.send("❌ Hall of Fame channel no longer exists!")
            return

        # Create quote data
        quote_data = {
            'message_id': quoted_message.id,
            'channel_id': quoted_message.channel.id,
            'channel_name': quoted_message.channel.name,
            'author_id': quoted_message.author.id,
            'author_name': quoted_message.author.display_name,
            'author_username': str(quoted_message.author),
            'content': quoted_message.content,
            'timestamp': quoted_message.created_at.isoformat(),
            'added_by': ctx.author.id,
            'added_by_name': str(ctx.author),
            'attachments': [],
            'embeds': []
        }

        # Handle attachments
        for attachment in quoted_message.attachments:
            quote_data['attachments'].append({
                'filename': attachment.filename,
                'url': attachment.url,
                'size': attachment.size,
                'content_type': attachment.content_type
            })

        # Handle embeds
        for embed in quoted_message.embeds:
            embed_data = {
                'title': embed.title,
                'description': embed.description,
                'url': embed.url,
                'color': embed.color.value if embed.color else None,
                'image': embed.image.url if embed.image else None,
                'thumbnail': embed.thumbnail.url if embed.thumbnail else None
            }
            quote_data['embeds'].append(embed_data)

        # Add to database
        quote_id = self.add_quote(ctx.guild.id, quote_data)

        # Create Hall of Fame embed
        hof_embed = await self.create_quote_embed(quote_data, ctx.guild)
        
        # Post to Hall of Fame channel
        hof_message = await hof_channel.send(embed=hof_embed)

        # Add reactions for voting
        await hof_message.add_reaction("⭐")
        await hof_message.add_reaction("❤️")
        await hof_message.add_reaction("😂")

        # Confirm to user
        confirm_embed = discord.Embed(
            title="✅ Added to Hall of Fame",
            description=f"Quote #{quote_id} has been added to {hof_channel.mention}!",
            color=COLORS['success']
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

    async def create_quote_embed(self, quote_data, guild):
        """Create a fancy quote embed"""
        # Main embed
        embed = discord.Embed(
            color=COLORS['primary']
        )

        # Author info with styled name (preserved even if user leaves)
        author_display = f"**{quote_data['author_name']}**"
        embed.set_author(
            name=author_display,
            icon_url=self.get_user_avatar(quote_data['author_id'])
        )

        # Message content
        if quote_data['content']:
            # Limit content length
            content = quote_data['content']
            if len(content) > 1000:
                content = content[:997] + "..."
            embed.description = f"*\"{content}\"*"

        # Channel and timestamp info
        original_time = datetime.fromisoformat(quote_data['timestamp'])
        embed.add_field(
            name="📍 Original Message",
            value=f"**Channel:** #{quote_data['channel_name']}\n**Posted:** {original_time.strftime('%B %d, %Y at %I:%M %p')}",
            inline=True
        )

        # Added by info
        added_time = datetime.fromisoformat(quote_data['added_at'])
        embed.add_field(
            name="⭐ Added to Hall of Fame",
            value=f"**By:** {quote_data['added_by_name']}\n**On:** {added_time.strftime('%B %d, %Y at %I:%M %p')}",
            inline=True
        )

        # Quote ID
        embed.add_field(
            name="🆔 Quote ID",
            value=f"#{quote_data['id']}",
            inline=True
        )

        # Handle attachments
        if quote_data['attachments']:
            attachment_info = []
            for i, attachment in enumerate(quote_data['attachments'][:3]):  # Max 3 attachments
                if attachment['content_type'] and attachment['content_type'].startswith('image/'):
                    # Set first image as embed image
                    if i == 0:
                        embed.set_image(url=attachment['url'])
                    attachment_info.append(f"🖼️ {attachment['filename']}")
                else:
                    attachment_info.append(f"📎 {attachment['filename']}")
            
            if attachment_info:
                embed.add_field(
                    name="📎 Attachments",
                    value="\n".join(attachment_info),
                    inline=False
                )

        # Handle embeds from original message
        if quote_data['embeds']:
            embed_info = []
            for orig_embed in quote_data['embeds'][:2]:  # Max 2 embeds
                if orig_embed['title']:
                    embed_info.append(f"📋 {orig_embed['title']}")
                elif orig_embed['description']:
                    desc = orig_embed['description'][:50] + "..." if len(orig_embed['description']) > 50 else orig_embed['description']
                    embed_info.append(f"📋 {desc}")
            
            if embed_info:
                embed.add_field(
                    name="📋 Embedded Content",
                    value="\n".join(embed_info),
                    inline=False
                )

        embed.set_footer(
            text=f"Hall of Fame • React to show appreciation!",
            icon_url=guild.icon.url if guild.icon else None
        )

        return embed

    def get_user_avatar(self, user_id):
        """Get user avatar URL, with fallback"""
        user = self.bot.get_user(user_id)
        if user and user.avatar:
            return user.avatar.url
        elif user:
            return user.default_avatar.url
        else:
            # Fallback for users who left the server
            return "https://cdn.discordapp.com/embed/avatars/0.png"

    @commands.command(name='sethofchannel')
    @commands.has_permissions(manage_channels=True)
    async def set_hof_channel_command(self, ctx, channel: discord.TextChannel = None):
        """Set the Hall of Fame channel (Manage Channels permission required)"""
        if channel is None:
            channel = ctx.channel
        
        self.set_hof_channel(ctx.guild.id, channel.id)
        
        # Debug: Check if it was saved correctly
        saved_channel_id = self.get_hof_channel(ctx.guild.id)
        print(f"DEBUG: Set HOF channel {channel.id}, retrieved: {saved_channel_id}")
        
        embed = discord.Embed(
            title="✅ Hall of Fame Channel Set",
            description=f"Hall of Fame quotes will now be posted to {channel.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="📋 Usage",
            value="Reply to any message and use `!hof` to add it to Hall of Fame!",
            inline=False
        )
        embed.add_field(
            name="🔧 Debug Info",
            value=f"Channel ID: {channel.id}\nSaved: {saved_channel_id}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='removehofchannel')
    @commands.has_permissions(manage_channels=True)
    async def remove_hof_channel(self, ctx):
        """Remove Hall of Fame channel setting (Manage Channels permission required)"""
        guild_key = str(ctx.guild.id)
        
        if guild_key in self.quotes:
            self.quotes[guild_key]['hof_channel'] = None
            self.save_quotes()
        
        embed = discord.Embed(
            title="✅ Hall of Fame Channel Removed",
            description="Hall of Fame functionality has been disabled.",
            color=COLORS['success']
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='hofstats')
    async def hof_stats(self, ctx):
        """Show Hall of Fame statistics"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.quotes or not self.quotes[guild_key]['quotes']:
            await ctx.send("❌ No quotes found in Hall of Fame!")
            return
        
        quotes = self.quotes[guild_key]['quotes']
        
        # Calculate stats
        total_quotes = len(quotes)
        unique_authors = len(set(quote['author_id'] for quote in quotes))
        
        # Most quoted user
        author_counts = {}
        for quote in quotes:
            author_id = quote['author_id']
            author_counts[author_id] = author_counts.get(author_id, 0) + 1
        
        most_quoted_id = max(author_counts, key=author_counts.get)
        most_quoted_count = author_counts[most_quoted_id]
        most_quoted_name = next(quote['author_name'] for quote in quotes if quote['author_id'] == most_quoted_id)
        
        embed = discord.Embed(
            title="📊 Hall of Fame Statistics",
            color=COLORS['info']
        )
        
        embed.add_field(name="📝 Total Quotes", value=f"{total_quotes:,}", inline=True)
        embed.add_field(name="👥 Unique Authors", value=f"{unique_authors:,}", inline=True)
        embed.add_field(name="⭐ Most Quoted", value=f"{most_quoted_name}\n({most_quoted_count} quotes)", inline=True)
        
        # Recent activity
        recent_quotes = sorted(quotes, key=lambda x: x['added_at'], reverse=True)[:5]
        recent_text = []
        for quote in recent_quotes:
            added_time = datetime.fromisoformat(quote['added_at'])
            recent_text.append(f"#{quote['id']} by {quote['author_name']} ({added_time.strftime('%m/%d')})")
        
        embed.add_field(
            name="🕒 Recent Quotes",
            value="\n".join(recent_text),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='hofquote', aliases=['hq'])
    async def get_quote(self, ctx, quote_id: int = None):
        """Get a specific quote or random quote from Hall of Fame"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.quotes or not self.quotes[guild_key]['quotes']:
            await ctx.send("❌ No quotes found in Hall of Fame!")
            return
        
        quotes = self.quotes[guild_key]['quotes']
        
        if quote_id:
            # Find specific quote
            quote = next((q for q in quotes if q['id'] == quote_id), None)
            if not quote:
                await ctx.send(f"❌ Quote #{quote_id} not found!")
                return
        else:
            # Random quote
            import random
            quote = random.choice(quotes)
        
        embed = await self.create_quote_embed(quote, ctx.guild)
        await ctx.send(embed=embed)

    @commands.command(name='hofinfo')
    async def hof_info(self, ctx):
        """Show Hall of Fame channel information and debug data"""
        guild_key = str(ctx.guild.id)
        
        embed = discord.Embed(
            title="🔧 Hall of Fame Debug Info",
            color=COLORS['info']
        )
        
        # Current channel setting
        hof_channel_id = self.get_hof_channel(ctx.guild.id)
        if hof_channel_id:
            hof_channel = ctx.guild.get_channel(hof_channel_id)
            if hof_channel:
                embed.add_field(
                    name="📍 Current HOF Channel",
                    value=f"{hof_channel.mention} (ID: {hof_channel_id})",
                    inline=False
                )
            else:
                embed.add_field(
                    name="❌ HOF Channel Issue",
                    value=f"Channel ID {hof_channel_id} not found (deleted?)",
                    inline=False
                )
        else:
            embed.add_field(
                name="❌ No HOF Channel",
                value="Hall of Fame channel not set",
                inline=False
            )
        
        # Debug data
        embed.add_field(
            name="🔧 Debug Data",
            value=f"Guild Key: {guild_key}\nData exists: {guild_key in self.quotes}\nChannel ID: {hof_channel_id}",
            inline=False
        )
        
        # Quote count
        if guild_key in self.quotes and 'quotes' in self.quotes[guild_key]:
            quote_count = len(self.quotes[guild_key]['quotes'])
            embed.add_field(
                name="📊 Quote Count",
                value=f"{quote_count} quotes in database",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @set_hof_channel_command.error
    @remove_hof_channel.error
    async def hof_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Channels' permission to use this command!")

async def setup(bot):
    await bot.add_cog(Quotes(bot))