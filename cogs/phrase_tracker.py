import discord
from discord.ext import commands
import json
import os
from config import COLORS

class PhraseTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/phrase_tracker.json'
        self.tracked_phrases = self.load_tracked_phrases()

    def load_tracked_phrases(self):
        """Load tracked phrases from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_tracked_phrases(self):
        """Save tracked phrases to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.tracked_phrases, f, indent=2)

    @commands.command(name='trackphrase')
    @commands.has_permissions(manage_messages=True)
    async def track_phrase(self, ctx, user: discord.Member, *, phrase: str):
        """Track how many times a user says a specific phrase (Admin only)
        Usage: !trackphrase @user hello i am jeff"""
        
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        
        # Initialize guild data if it doesn't exist
        if guild_id not in self.tracked_phrases:
            self.tracked_phrases[guild_id] = {}
        
        # Initialize user data if it doesn't exist
        if user_id not in self.tracked_phrases[guild_id]:
            self.tracked_phrases[guild_id][user_id] = {
                'username': str(user),
                'display_name': user.display_name,
                'phrases': {}
            }
        
        # Add or reset the phrase
        phrase_lower = phrase.lower()
        self.tracked_phrases[guild_id][user_id]['phrases'][phrase_lower] = {
            'original_phrase': phrase,
            'count': 0,
            'added_by': str(ctx.author),
            'added_by_id': ctx.author.id
        }
        
        self.save_tracked_phrases()
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Phrase Tracking Started",
            description=f"Now tracking phrase for {user.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="👤 User",
            value=user.display_name,
            inline=True
        )
        embed.add_field(
            name="💬 Phrase",
            value=f'"{phrase}"',
            inline=True
        )
        embed.add_field(
            name="📊 Current Count",
            value="0",
            inline=True
        )
        embed.set_footer(text=f"Added by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

    @commands.command(name='untrackphrase')
    @commands.has_permissions(manage_messages=True)
    async def untrack_phrase(self, ctx, user: discord.Member, *, phrase: str):
        """Stop tracking a phrase for a user (Admin only)
        Usage: !untrackphrase @user hello i am jeff"""
        
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        phrase_lower = phrase.lower()
        
        # Check if tracking exists
        if (guild_id not in self.tracked_phrases or 
            user_id not in self.tracked_phrases[guild_id] or 
            phrase_lower not in self.tracked_phrases[guild_id][user_id]['phrases']):
            await ctx.send("❌ That phrase is not being tracked for this user!")
            return
        
        # Get the count before removing
        count = self.tracked_phrases[guild_id][user_id]['phrases'][phrase_lower]['count']
        
        # Remove the phrase
        del self.tracked_phrases[guild_id][user_id]['phrases'][phrase_lower]
        
        # Clean up empty user data
        if not self.tracked_phrases[guild_id][user_id]['phrases']:
            del self.tracked_phrases[guild_id][user_id]
        
        # Clean up empty guild data
        if not self.tracked_phrases[guild_id]:
            del self.tracked_phrases[guild_id]
        
        self.save_tracked_phrases()
        
        # Create confirmation embed
        embed = discord.Embed(
            title="✅ Phrase Tracking Stopped",
            description=f"Stopped tracking phrase for {user.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="👤 User",
            value=user.display_name,
            inline=True
        )
        embed.add_field(
            name="💬 Phrase",
            value=f'"{phrase}"',
            inline=True
        )
        embed.add_field(
            name="📊 Final Count",
            value=str(count),
            inline=True
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='phrasestats')
    async def phrase_stats(self, ctx, user: discord.Member = None):
        """Show phrase tracking statistics for a user or all users
        Usage: !phrasestats [@user]"""
        
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.tracked_phrases or not self.tracked_phrases[guild_id]:
            await ctx.send("❌ No phrases are being tracked in this server!")
            return
        
        if user:
            # Show stats for specific user
            user_id = str(user.id)
            if user_id not in self.tracked_phrases[guild_id]:
                await ctx.send(f"❌ No phrases are being tracked for {user.mention}!")
                return
            
            user_data = self.tracked_phrases[guild_id][user_id]
            
            embed = discord.Embed(
                title=f"📊 Phrase Stats for {user.display_name}",
                color=COLORS['info']
            )
            
            if not user_data['phrases']:
                embed.description = "No phrases being tracked"
            else:
                phrase_list = []
                for phrase_lower, data in user_data['phrases'].items():
                    phrase_list.append(f'"{data["original_phrase"]}" - **{data["count"]}** times')
                
                embed.description = "\n".join(phrase_list)
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            
        else:
            # Show stats for all users
            embed = discord.Embed(
                title="📊 All Phrase Tracking Stats",
                color=COLORS['info']
            )
            
            total_phrases = 0
            total_counts = 0
            user_summaries = []
            
            for user_id, user_data in self.tracked_phrases[guild_id].items():
                user_obj = ctx.guild.get_member(int(user_id))
                username = user_obj.display_name if user_obj else user_data['display_name']
                
                phrase_count = len(user_data['phrases'])
                total_phrase_uses = sum(data['count'] for data in user_data['phrases'].values())
                
                if phrase_count > 0:
                    user_summaries.append(f"**{username}**: {phrase_count} phrases, {total_phrase_uses} total uses")
                    total_phrases += phrase_count
                    total_counts += total_phrase_uses
            
            if user_summaries:
                embed.description = "\n".join(user_summaries)
                embed.add_field(
                    name="📈 Server Totals",
                    value=f"**{total_phrases}** phrases tracked\n**{total_counts}** total phrase uses",
                    inline=False
                )
            else:
                embed.description = "No phrases being tracked"
        
        await ctx.send(embed=embed)

    @commands.command(name='listphrases')
    async def list_phrases(self, ctx, user: discord.Member = None):
        """List all tracked phrases with detailed information
        Usage: !listphrases [@user]"""
        
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.tracked_phrases or not self.tracked_phrases[guild_id]:
            await ctx.send("❌ No phrases are being tracked in this server!")
            return
        
        if user:
            # List phrases for specific user
            user_id = str(user.id)
            if user_id not in self.tracked_phrases[guild_id]:
                await ctx.send(f"❌ No phrases are being tracked for {user.mention}!")
                return
            
            user_data = self.tracked_phrases[guild_id][user_id]
            
            embed = discord.Embed(
                title=f"📝 Tracked Phrases for {user.display_name}",
                color=COLORS['info']
            )
            
            if not user_data['phrases']:
                embed.description = "No phrases being tracked"
            else:
                for phrase_lower, data in user_data['phrases'].items():
                    embed.add_field(
                        name=f'"{data["original_phrase"]}"',
                        value=f"**Count:** {data['count']}\n**Added by:** {data['added_by']}",
                        inline=False
                    )
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            
        else:
            # List all phrases for all users
            embed = discord.Embed(
                title="📝 All Tracked Phrases",
                color=COLORS['info']
            )
            
            phrase_entries = []
            for user_id, user_data in self.tracked_phrases[guild_id].items():
                user_obj = ctx.guild.get_member(int(user_id))
                username = user_obj.display_name if user_obj else user_data['display_name']
                
                for phrase_lower, data in user_data['phrases'].items():
                    phrase_entries.append(
                        f"**{username}**: \"{data['original_phrase']}\" ({data['count']} times)"
                    )
            
            if phrase_entries:
                # Split into chunks if too long
                description = "\n".join(phrase_entries)
                if len(description) > 2000:
                    embed.description = description[:1997] + "..."
                else:
                    embed.description = description
            else:
                embed.description = "No phrases being tracked"
        
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages and check for tracked phrases"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        # Check if this guild has any tracked phrases
        if guild_id not in self.tracked_phrases:
            return
        
        # Check if this user has any tracked phrases
        if user_id not in self.tracked_phrases[guild_id]:
            return
        
        message_content = message.content.lower()
        user_data = self.tracked_phrases[guild_id][user_id]
        
        # Check each tracked phrase for this user
        for phrase_lower, phrase_data in user_data['phrases'].items():
            if phrase_lower in message_content:
                # Increment the count
                phrase_data['count'] += 1
                self.save_tracked_phrases()
                
                # Create and send the tracking embed
                embed = discord.Embed(
                    title="🎯 Phrase Detected!",
                    color=COLORS['primary']
                )
                
                embed.add_field(
                    name="👤 User",
                    value=message.author.mention,
                    inline=True
                )
                embed.add_field(
                    name="💬 Phrase",
                    value=f'"{phrase_data["original_phrase"]}"',
                    inline=True
                )
                embed.add_field(
                    name="📊 Count",
                    value=f"**{phrase_data['count']}** times",
                    inline=True
                )
                
                embed.set_footer(
                    text=f"Phrase tracking by {phrase_data['added_by']}",
                    icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
                )
                
                # Add some fun reactions based on count milestones
                if phrase_data['count'] == 1:
                    embed.add_field(
                        name="🎉 Milestone",
                        value="First time saying this phrase!",
                        inline=False
                    )
                elif phrase_data['count'] == 10:
                    embed.add_field(
                        name="🔥 Milestone",
                        value="10th time! Getting consistent!",
                        inline=False
                    )
                elif phrase_data['count'] == 50:
                    embed.add_field(
                        name="⭐ Milestone",
                        value="50 times! This is becoming a habit!",
                        inline=False
                    )
                elif phrase_data['count'] == 100:
                    embed.add_field(
                        name="🏆 Milestone",
                        value="100 times! Legendary status achieved!",
                        inline=False
                    )
                elif phrase_data['count'] % 25 == 0 and phrase_data['count'] > 100:
                    embed.add_field(
                        name="💎 Milestone",
                        value=f"{phrase_data['count']} times! Still going strong!",
                        inline=False
                    )
                
                await message.channel.send(embed=embed, delete_after=30)
                
                # Only trigger once per message even if multiple phrases match
                break

    @track_phrase.error
    @untrack_phrase.error
    async def phrase_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need 'Manage Messages' permission to use phrase tracking commands!",
                color=COLORS['error']
            )
            embed.add_field(
                name="💡 Info",
                value="Only server administrators can track phrases to prevent abuse.",
                inline=False
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PhraseTracker(bot))