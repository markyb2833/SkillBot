import discord
from discord.ext import commands
import json
import os
import random
import aiohttp
from datetime import datetime
from config import COLORS

class InsultSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/insult_system.json'
        self.tracked_triggers = self.load_tracked_triggers()
        self.custom_insults = self.load_custom_insults()
        
        # Default insult lists by tier
        self.default_insults = self.load_default_insults()

    def load_tracked_triggers(self):
        """Load tracked triggers from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    return data.get('tracked_triggers', {})
            except:
                return {}
        return {}

    def load_custom_insults(self):
        """Load custom insults from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    return data.get('custom_insults', {})
            except:
                return {}
        return {}

    def load_default_insults(self):
        """Load default insults from JSON file"""
        default_file = 'data/default_insults.json'
        if os.path.exists(default_file):
            try:
                with open(default_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Fallback to hardcoded insults if file doesn't exist
        return {
            'mild': ["Oh look, it's {user} trying to be clever again!"],
            'strong': ["Listen here, {user}, you absolute walnut!"],
            'cruel': ["I hope {user} steps on a Lego every day!"]
        }

    def save_default_insults(self):
        """Save default insults to JSON file"""
        default_file = 'data/default_insults.json'
        with open(default_file, 'w') as f:
            json.dump(self.default_insults, f, indent=2)

    def save_data(self):
        """Save all data to JSON file"""
        data = {
            'tracked_triggers': self.tracked_triggers,
            'custom_insults': self.custom_insults,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_guild_triggers(self, guild_id):
        """Get tracked triggers for a specific guild"""
        guild_key = str(guild_id)
        if guild_key not in self.tracked_triggers:
            self.tracked_triggers[guild_key] = {}
        return self.tracked_triggers[guild_key]

    def get_guild_insults(self, guild_id):
        """Get custom insults for a specific guild"""
        guild_key = str(guild_id)
        if guild_key not in self.custom_insults:
            self.custom_insults[guild_key] = {
                'mild': [],
                'strong': [],
                'cruel': []
            }
        return self.custom_insults[guild_key]

    async def get_insult_from_api(self, tier):
        """Get an insult from the Evil Insult Generator API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://evilinsult.com/generate_insult.php?lang=en&type={tier}"
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        insult = await response.text()
                        # Clean up the insult (remove HTML tags if any)
                        insult = insult.replace('<br>', ' ').replace('<br/>', ' ').strip()
                        return insult
        except:
            pass
        return None

    def generate_insult(self, user_mention, tier, guild_id=None):
        """Generate an insult for a user"""
        # Try custom insults first
        if guild_id:
            guild_insults = self.get_guild_insults(guild_id)
            if guild_insults[tier]:
                insult = random.choice(guild_insults[tier])
                # Check if insult has {user} tag, if so format it, otherwise return as-is
                if '{user}' in insult:
                    return insult.format(user=user_mention)
                else:
                    return insult
        
        # Fall back to default insults
        if tier in self.default_insults and self.default_insults[tier]:
            # Ensure we have multiple insults to choose from
            available_insults = self.default_insults[tier]
            if len(available_insults) > 1:
                # Use random.choice for variety
                insult = random.choice(available_insults)
                print(f"DEBUG: Selected insult from {len(available_insults)} options: {insult[:50]}...")
            else:
                # If only one insult, use it
                insult = available_insults[0]
                print(f"DEBUG: Only one insult available for {tier} tier: {insult[:50]}...")
            
            # Check if insult has {user} tag, if so format it, otherwise return as-is
            if '{user}' in insult:
                return insult.format(user=user_mention)
            else:
                return insult
        
        # Final fallback
        return f"Hey {user_mention}, you're not very bright, are you?"

    @commands.command(name='insulton')
    @commands.has_permissions(manage_messages=True)
    async def insult_on(self, ctx, trigger: str, user_or_tier, tier: str = None):
        """Set up insult tracking for a phrase/emoji. Usage: !insulton "trigger" @user [tier] OR !insulton "trigger" [tier] for everyone"""
        # Determine if second parameter is a user or tier
        if isinstance(user_or_tier, discord.Member):
            # Format: !insulton "trigger" @user [tier]
            user = user_or_tier
            if tier is None:
                tier = 'mild'
        else:
            # Format: !insulton "trigger" [tier] (for everyone)
            user = None
            tier = user_or_tier
        
        if tier.lower() not in ['mild', 'strong', 'cruel']:
            await ctx.send("❌ Invalid tier! Use: mild, strong, or cruel")
            return
        
        guild_key = str(ctx.guild.id)
        if guild_key not in self.tracked_triggers:
            self.tracked_triggers[guild_key] = {}
        
        # Store the trigger
        self.tracked_triggers[guild_key][trigger.lower()] = {
            'user_id': user.id if user else None,  # None means everyone
            'tier': tier.lower(),
            'added_by': ctx.author.id,
            'added_at': datetime.now().isoformat(),
            'trigger_count': 0
        }
        
        self.save_data()
        
        if user:
            # Specific user tracking
            embed = discord.Embed(
                title="🎯 Insult Tracking Activated!",
                description=f"Now tracking **{trigger}** for {user.mention}",
                color=COLORS['success']
            )
            embed.add_field(name="Tier", value=tier.title(), inline=True)
            embed.add_field(name="Added By", value=ctx.author.mention, inline=True)
            embed.add_field(name="Next Steps", value="The user will be insulted whenever they use this trigger!", inline=False)
        else:
            # Everyone tracking
            embed = discord.Embed(
                title="🎯 Insult Tracking Activated!",
                description=f"Now tracking **{trigger}** for everyone",
                color=COLORS['success']
            )
            embed.add_field(name="Tier", value=tier.title(), inline=True)
            embed.add_field(name="Added By", value=ctx.author.mention, inline=True)
            embed.add_field(name="Next Steps", value="Anyone will be insulted whenever they use this trigger!", inline=False)
        
        await ctx.send(embed=embed, delete_after=15)

    @commands.command(name='insultoff')
    @commands.has_permissions(manage_messages=True)
    async def insult_off(self, ctx, trigger: str):
        """Remove insult tracking for a phrase/emoji"""
        guild_key = str(ctx.guild.id)
        if guild_key in self.tracked_triggers and trigger.lower() in self.tracked_triggers[guild_key]:
            removed_trigger = self.tracked_triggers[guild_key].pop(trigger.lower())
            self.save_data()
            
            embed = discord.Embed(
                title="🎯 Insult Tracking Deactivated!",
                description=f"Stopped tracking **{trigger}**",
                color=COLORS['warning']
            )
            embed.add_field(name="Was Tracking", value=f"<@{removed_trigger['user_id']}>", inline=True)
            embed.add_field(name="Tier", value=removed_trigger['tier'].title(), inline=True)
            
            await ctx.send(embed=embed, delete_after=15)
        else:
            await ctx.send(f"❌ No tracking found for **{trigger}**", delete_after=10)

    @commands.command(name='listinsults')
    @commands.has_permissions(manage_messages=True)
    async def list_insults(self, ctx):
        """List all tracked insult triggers"""
        guild_key = str(ctx.guild.id)
        triggers = self.tracked_triggers.get(guild_key, {})
        
        if not triggers:
            embed = discord.Embed(
                title="🎯 Insult Triggers",
                description="No insult triggers are currently active.",
                color=COLORS['info']
            )
        else:
            embed = discord.Embed(
                title="🎯 Active Insult Triggers",
                description=f"Found {len(triggers)} active trigger(s):",
                color=COLORS['primary']
            )
            
            for trigger, data in triggers.items():
                if data['user_id'] is None:
                    # Trigger for everyone
                    target_info = "Everyone"
                else:
                    # Trigger for specific user
                    user = ctx.guild.get_member(data['user_id'])
                    target_info = user.mention if user else f"<@{data['user_id']}>"
                
                embed.add_field(
                    name=f"🎯 {trigger}",
                    value=f"Target: {target_info}\nTier: {data['tier'].title()}\nTriggers: {data['trigger_count']}",
                    inline=True
                )
        
        embed.set_footer(text="Use !insultoff <trigger> to remove tracking")
        await ctx.send(embed=embed, delete_after=60)

    @commands.command(name='addinsult')
    @commands.has_permissions(manage_messages=True)
    async def add_insult(self, ctx, tier: str, *, insult_text: str):
        """Add a custom insult to a tier. Usage: !addinsult mild Your insult here"""
        if tier.lower() not in ['mild', 'strong', 'cruel']:
            await ctx.send("❌ Invalid tier! Use: mild, strong, or cruel")
            return
        
        guild_key = str(ctx.guild.id)
        guild_insults = self.get_guild_insults(guild_key)
        
        # Add the insult
        guild_insults[tier.lower()].append(insult_text)
        self.save_data()
        
        embed = discord.Embed(
            title="💬 Custom Insult Added!",
            description=f"Added to **{tier.title()}** tier:",
            color=COLORS['success']
        )
        embed.add_field(name="Insult", value=insult_text, inline=False)
        embed.add_field(name="Total Insults", value=f"{len(guild_insults[tier.lower()])} in {tier.title()} tier", inline=True)
        
        await ctx.send(embed=embed, delete_after=15)

    @commands.command(name='removeinsult')
    @commands.has_permissions(manage_messages=True)
    async def remove_insult(self, ctx, tier: str, index: int):
        """Remove a custom insult by index. Usage: !removeinsult mild 1"""
        if tier.lower() not in ['mild', 'strong', 'cruel']:
            await ctx.send("❌ Invalid tier! Use: mild, strong, or cruel")
            return
        
        guild_key = str(ctx.guild.id)
        guild_insults = self.get_guild_insults(guild_key)
        
        try:
            index = int(index) - 1  # Convert to 0-based index
            if 0 <= index < len(guild_insults[tier.lower()]):
                removed_insult = guild_insults[tier.lower()].pop(index)
                self.save_data()
                
                embed = discord.Embed(
                    title="💬 Custom Insult Removed!",
                    description=f"Removed from **{tier.title()}** tier:",
                    color=COLORS['warning']
                )
                embed.add_field(name="Removed Insult", value=removed_insult, inline=False)
                
                await ctx.send(embed=embed, delete_after=15)
            else:
                await ctx.send(f"❌ Invalid index! Use 1-{len(guild_insults[tier.lower()])}", delete_after=10)
        except ValueError:
            await ctx.send("❌ Invalid index! Please provide a number", delete_after=10)

    @commands.command(name='listcustominsults')
    @commands.has_permissions(manage_messages=True)
    async def list_custom_insults(self, ctx):
        """List all custom insults by tier"""
        guild_key = str(ctx.guild.id)
        guild_insults = self.get_guild_insults(guild_key)
        
        embed = discord.Embed(
            title="💬 Custom Insults",
            color=COLORS['primary']
        )
        
        for tier in ['mild', 'strong', 'cruel']:
            insults = guild_insults[tier]
            if insults:
                # Truncate long lists
                if len(insults) > 10:
                    display_insults = insults[:10] + [f"... and {len(insults) - 10} more"]
                else:
                    display_insults = insults
                
                embed.add_field(
                    name=f"🎭 {tier.title()} Tier ({len(insults)})",
                    value="\n".join([f"{i+1}. {insult}" for i, insult in enumerate(display_insults)]),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"🎭 {tier.title()} Tier (0)",
                    value="No custom insults added yet",
                    inline=False
                )
        
        embed.set_footer(text="Use !addinsult <tier> <text> to add more (optional: include {user} tag)")
        await ctx.send(embed=embed, delete_after=120)

    @commands.command(name='testinsult')
    @commands.has_permissions(manage_messages=True)
    async def test_insult(self, ctx, tier: str = 'mild', user: discord.Member = None):
        """Test an insult of a specific tier"""
        if tier.lower() not in ['mild', 'strong', 'cruel']:
            await ctx.send("❌ Invalid tier! Use: mild, strong, or cruel")
            return
        
        target_user = user or ctx.author
        insult = self.generate_insult(target_user.mention, tier.lower(), ctx.guild.id)
        
        embed = discord.Embed(
            title="🧪 Insult Test",
            description=f"Testing **{tier.title()}** tier insult:",
            color=COLORS['info']
        )
        embed.add_field(name="Target", value=target_user.mention, inline=True)
        embed.add_field(name="Tier", value=tier.title(), inline=True)
        embed.add_field(name="Insult", value=insult, inline=False)
        
        await ctx.send(embed=embed, delete_after=20)

    @commands.command(name='adddefaultinsult')
    async def add_default_insult(self, ctx, tier: str, *, insult_text: str):
        """Add an insult to the default list for a tier. Usage: !adddefaultinsult mild Your insult (optional: include {user} tag)"""
        if tier.lower() not in ['mild', 'strong', 'cruel']:
            await ctx.send("❌ Invalid tier! Use: mild, strong, or cruel")
            return
        
        # Add to default insults
        if tier.lower() not in self.default_insults:
            self.default_insults[tier.lower()] = []
        
        self.default_insults[tier.lower()].append(insult_text)
        self.save_default_insults()
        
        embed = discord.Embed(
            title="💬 Default Insult Added!",
            description=f"Added to **{tier.title()}** tier:",
            color=COLORS['success']
        )
        embed.add_field(name="Insult", value=insult_text, inline=False)
        embed.add_field(name="Total Insults", value=f"{len(self.default_insults[tier.lower()])} in {tier.title()} tier", inline=True)
        embed.add_field(name="Note", value="This insult will be available to all servers!", inline=False)
        
        # Show info about {user} tag
        if '{user}' in insult_text:
            embed.add_field(name="Format", value="✅ Includes {user} tag - will be personalized", inline=True)
        else:
            embed.add_field(name="Format", value="ℹ️ No {user} tag - will be sent as-is", inline=True)
        
        await ctx.send(embed=embed, delete_after=20)

    @commands.command(name='removedefaultinsult')
    async def remove_default_insult(self, ctx, tier: str, index: int):
        """Remove a default insult by index. Usage: !removedefaultinsult mild 1"""
        if tier.lower() not in ['mild', 'strong', 'cruel']:
            await ctx.send("❌ Invalid tier! Use: mild, strong, or cruel")
            return
        
        if tier.lower() not in self.default_insults or not self.default_insults[tier.lower()]:
            await ctx.send(f"❌ No insults found in {tier.title()} tier!", delete_after=10)
            return
        
        try:
            index = int(index) - 1  # Convert to 0-based index
            if 0 <= index < len(self.default_insults[tier.lower()]):
                removed_insult = self.default_insults[tier.lower()].pop(index)
                self.save_default_insults()
                
                embed = discord.Embed(
                    title="💬 Default Insult Removed!",
                    description=f"Removed from **{tier.title()}** tier:",
                    color=COLORS['warning']
                )
                embed.add_field(name="Removed Insult", value=removed_insult, inline=False)
                
                await ctx.send(embed=embed, delete_after=15)
            else:
                await ctx.send(f"❌ Invalid index! Use 1-{len(self.default_insults[tier.lower()])}", delete_after=10)
        except ValueError:
            await ctx.send("❌ Invalid index! Please provide a number", delete_after=10)

    @commands.command(name='listdefaultinsults')
    async def list_default_insults(self, ctx):
        """List all default insults by tier"""
        embed = discord.Embed(
            title="💬 Default Insults",
            description="These insults are available to all servers:",
            color=COLORS['primary']
        )
        
        for tier in ['mild', 'strong', 'cruel']:
            insults = self.default_insults.get(tier, [])
            if insults:
                # Truncate long lists
                if len(insults) > 8:
                    display_insults = insults[:8] + [f"... and {len(insults) - 8} more"]
                else:
                    display_insults = insults
                
                embed.add_field(
                    name=f"🎭 {tier.title()} Tier ({len(insults)})",
                    value="\n".join([f"{i+1}. {insult}" for i, insult in enumerate(display_insults)]),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"🎭 {tier.title()} Tier (0)",
                    value="No default insults available",
                    inline=False
                )
        
        embed.set_footer(text="Use !adddefaultinsult <tier> <text> to add more (optional: include {user} tag)")
        await ctx.send(embed=embed, delete_after=120)

    @commands.command(name='resetdefaultinsults')
    @commands.has_permissions(administrator=True)
    async def reset_default_insults(self, ctx):
        """Reset default insults to original list (Admin only)"""
        # Recreate the original default insults
        self.default_insults = {
            'mild': [
                "Oh look, it's {user} trying to be clever again!",
                "I've seen better ideas from a broken calculator, {user}.",
                "Well, {user}, that's certainly one way to waste everyone's time.",
                "Congratulations {user}, you've achieved the impossible - making me question human intelligence.",
                "I'm not saying {user} is slow, but they make glaciers look speedy.",
                "If brains were dynamite, {user} wouldn't have enough to blow their nose.",
                "Some people have a way with words, {user} has a way with... well, let's just say it's unique.",
                "I'd agree with {user}, but then we'd both be wrong.",
                "Bless {user}'s heart, they're doing their best with what they've got.",
                "I'm not insulting {user}, I'm describing them accurately."
            ],
            'strong': [
                "Listen here, {user}, you absolute walnut. Your existence is a cosmic joke.",
                "I've met rocks with more personality than you, {user}. At least rocks don't make me lose faith in humanity.",
                "If stupidity was a sport, {user} would be a gold medalist. Actually, they'd probably lose that too.",
                "I'm starting to think {user} was dropped on their head as a baby. Multiple times. From a great height.",
                "The fact that {user} can operate a keyboard is proof that evolution can go backwards.",
                "I've seen better decision-making from a drunk penguin than from {user}.",
                "If {user} had a brain, it would be lonely in there.",
                "I'm not saying {user} is the dumbest person alive, but they're definitely in the running.",
                "The world would be a better place if {user} had been a stillbirth.",
                "I'd call {user} an idiot, but that would be an insult to idiots everywhere."
            ],
            'cruel': [
                "I hope {user} steps on a Lego every day for the rest of their miserable existence.",
                "If I had a dollar for every brain cell {user} has, I'd be broke.",
                "I'd rather be trapped in a room with a rabid honey badger than spend another second listening to {user}.",
                "The only thing {user} is good for is being a bad example to others.",
                "I'm convinced {user} was conceived by two people who shouldn't have been allowed to reproduce.",
                "If {user} was any dumber, they'd need to be watered twice a week.",
                "I'd insult {user}'s intelligence, but I'm not sure they'd understand it.",
                "The fact that {user} hasn't been eaten by a bear yet is proof that even nature has standards.",
                "I hope {user} gets exactly what they deserve in life - nothing good.",
                "I'm not saying {user} is worthless, but they're definitely not worth my time."
            ]
        }
        
        self.save_default_insults()
        
        embed = discord.Embed(
            title="🔄 Default Insults Reset!",
            description="All default insults have been reset to the original list.",
            color=COLORS['success']
        )
        embed.add_field(name="Note", value="This affects all servers using the bot.", inline=False)
        
        await ctx.send(embed=embed, delete_after=15)

    @commands.command(name='insulthelp')
    async def insult_help(self, ctx):
        """Show help for the insult system"""
        embed = discord.Embed(
            title="🎯 Insult System Help",
            description="Welcome to the insult system! Here's how to use it:",
            color=COLORS['primary']
        )
        
        embed.add_field(
            name="🚀 Getting Started",
            value="1. Use `!insulton \"phrase\" @user [tier]` to track a specific user\n2. Use `!insulton \"phrase\" [tier]` to track everyone\n3. The bot will automatically insult when the phrase is used\n4. Choose from: mild, strong, or cruel tiers",
            inline=False
        )
        
        embed.add_field(
            name="📝 Adding Insults",
            value="• **Server-specific**: `!addinsult <tier> <text>` (Admin only)\n• **Global defaults**: `!adddefaultinsult <tier> <text>` (optional: include {user} tag)\n• **Examples**:\n  - `!adddefaultinsult mild Oh look, it's {user} being silly again!`\n  - `!adddefaultinsult strong What a complete disaster!`",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Management Commands",
            value="• `!listinsults` - Show active triggers\n• `!listcustominsults` - Show server insults\n• `!listdefaultinsults` - Show global insults\n• `!testinsult [tier] [@user]` - Test insults",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Important Notes",
            value="• The {user} tag is optional - use it for personalized insults\n• Tiers: mild (friendly), strong (mean), cruel (vicious)\n• Only admins can set up triggers\n• Anyone can add to the global insult database",
            inline=False
        )
        
        embed.set_footer(text="Use !insulthelp for this message again")
        await ctx.send(embed=embed, delete_after=120)

    @commands.command(name='insultexamples')
    async def insult_examples(self, ctx):
        """Show examples of different insult formats"""
        embed = discord.Embed(
            title="💬 Insult Format Examples",
            description="Here are examples of how to format insults:",
            color=COLORS['info']
        )
        
        embed.add_field(
            name="🎯 With {user} Tag (Personalized)",
            value="• `!adddefaultinsult mild Oh look, it's {user} being silly again!`\n• `!adddefaultinsult strong Listen here {user}, you absolute walnut!`\n• `!adddefaultinsult cruel I hope {user} steps on a Lego every day!`",
            inline=False
        )
        
        embed.add_field(
            name="💥 Without {user} Tag (General)",
            value="• `!adddefaultinsult mild What a brilliant display of mediocrity!`\n• `!adddefaultinsult strong This is a new level of stupidity!`\n• `!adddefaultinsult cruel The world would be better off without this level of incompetence.`",
            inline=False
        )
        
        embed.add_field(
            name="📝 How It Works",
            value="• **With {user}**: Gets personalized for the target user\n• **Without {user}**: Sent exactly as written\n• **Both types**: Can be mixed in the same tier",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Trigger Examples",
            value="• `!insulton \"hello\" @user mild` - Track specific user\n• `!insulton \"hello\" mild` - Track everyone\n• `!insulton \"😀\" strong` - Track emoji for everyone",
            inline=False
        )
        
        embed.set_footer(text="Use !adddefaultinsult to add your own insults!")
        await ctx.send(embed=embed, delete_after=90)

    @commands.command(name='insultdebug')
    async def insult_debug(self, ctx, tier: str = None):
        """Debug command to check available insults for a tier"""
        if tier and tier.lower() not in ['mild', 'strong', 'cruel']:
            await ctx.send("❌ Invalid tier! Use: mild, strong, or cruel")
            return
        
        embed = discord.Embed(
            title="🐛 Insult Debug Information",
            color=COLORS['info']
        )
        
        if tier:
            # Show specific tier
            tier = tier.lower()
            default_count = len(self.default_insults.get(tier, []))
            guild_insults = self.get_guild_insults(ctx.guild.id)
            custom_count = len(guild_insults.get(tier, []))
            
            embed.add_field(
                name=f"🎭 {tier.title()} Tier",
                value=f"**Default Insults:** {default_count}\n**Custom Insults:** {custom_count}\n**Total Available:** {default_count + custom_count}",
                inline=False
            )
            
            if default_count > 0:
                embed.add_field(
                    name="📝 Default Insults",
                    value="\n".join([f"• {insult}" for insult in self.default_insults[tier][:5]]),
                    inline=False
                )
                if default_count > 5:
                    embed.add_field(name="...", value=f"And {default_count - 5} more", inline=False)
        else:
            # Show all tiers
            for tier_name in ['mild', 'strong', 'cruel']:
                default_count = len(self.default_insults.get(tier_name, []))
                guild_insults = self.get_guild_insults(ctx.guild.id)
                custom_count = len(guild_insults.get(tier_name, []))
                
                embed.add_field(
                    name=f"🎭 {tier_name.title()} Tier",
                    value=f"Default: {default_count} | Custom: {custom_count} | Total: {default_count + custom_count}",
                    inline=True
                )
        
        embed.add_field(
            name="🔍 Random Selection",
            value=f"Random seed: {random.getrandbits(32)}",
            inline=False
        )
        
        await ctx.send(embed=embed, delete_after=60)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check messages for tracked triggers and respond with insults"""
        # Ignore bot messages and commands
        if message.author.bot or message.content.startswith('!'):
            return
        
        guild_key = str(message.guild.id)
        if guild_key not in self.tracked_triggers:
            return
        
        # Check each trigger
        for trigger, data in self.tracked_triggers[guild_key].items():
            if trigger.lower() in message.content.lower():
                # Check if this trigger applies to this user
                should_trigger = False
                
                if data['user_id'] is None:
                    # Trigger for everyone
                    should_trigger = True
                elif message.author.id == data['user_id']:
                    # Trigger for specific user
                    should_trigger = True
                
                if should_trigger:
                    # Increment trigger count
                    data['trigger_count'] += 1
                    self.save_data()
                    
                    # Generate and send insult
                    insult = self.generate_insult(message.author.mention, data['tier'], message.guild.id)
                    
                    # Send the insult as plain text
                    try:
                        await message.channel.send(insult)
                    except discord.Forbidden:
                        # Bot doesn't have permission to send messages
                        pass
                    
                    # Only trigger once per message
                    break

async def setup(bot):
    await bot.add_cog(InsultSystem(bot))
