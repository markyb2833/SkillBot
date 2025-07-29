import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from config import COLORS, CURRENCY_NAME, DAILY_REWARD, STARTING_BALANCE

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/economy.json'
        self.gambling_channels_file = 'data/gambling_channels.json'
        self.users = self.load_users()
        self.gambling_channels = self.load_gambling_channels()

    def load_users(self):
        """Load user economy data from JSON file"""
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
        """Save user economy data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def load_gambling_channels(self):
        """Load gambling channel restrictions from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.gambling_channels_file):
            try:
                with open(self.gambling_channels_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_gambling_channels(self):
        """Save gambling channel restrictions to JSON file"""
        with open(self.gambling_channels_file, 'w') as f:
            json.dump(self.gambling_channels, f, indent=2)
    
    def is_gambling_allowed(self, ctx):
        """Check if gambling is allowed in the current channel"""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.gambling_channels:
            return True  # No restrictions set, allow everywhere
        
        allowed_channels = self.gambling_channels[guild_id]
        return ctx.channel.id in allowed_channels
    
    def get_gambling_channels_mention(self, ctx):
        """Get formatted mention string for gambling channels"""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.gambling_channels:
            return "No gambling channels set"
        
        channels = []
        for channel_id in self.gambling_channels[guild_id]:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                channels.append(channel.mention)
        
        if not channels:
            return "No valid gambling channels found"
        
        if len(channels) == 1:
            return channels[0]
        elif len(channels) == 2:
            return f"{channels[0]} or {channels[1]}"
        else:
            return f"{', '.join(channels[:-1])}, or {channels[-1]}"
    
    async def auto_delete_message(self, message, delay):
        """Auto-delete a message after a delay"""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except discord.NotFound:
            pass  # Message already deleted
        except discord.Forbidden:
            pass  # No permission to delete
    
    async def send_gambling_error(self, ctx):
        """Send a gambling restriction error and delete both messages"""
        # Check if bot has permission to delete messages
        can_delete_messages = ctx.channel.permissions_for(ctx.guild.me).manage_messages
        
        # Create error embed
        embed = discord.Embed(
            title="🚫 Gambling Not Allowed Here",
            description=f"🎰 Gambling commands can only be used in {self.get_gambling_channels_mention(ctx)}",
            color=COLORS['error']
        )
        
        if can_delete_messages:
            embed.set_footer(text="💡 This message will be deleted in 30 seconds")
        else:
            embed.set_footer(text="💡 Bot needs 'Manage Messages' permission to auto-delete")
        
        # Send error message with mention
        error_message = await ctx.send(f"{ctx.author.mention}", embed=embed)
        
        # Delete both messages after 30 seconds (if we have permission)
        asyncio.create_task(self.delete_both_messages(ctx.message, error_message, 30))
    
    async def delete_both_messages(self, original_message, error_message, delay):
        """Delete both the original command and error message after a delay"""
        await asyncio.sleep(delay)
        
        # Delete original command message
        try:
            await original_message.delete()
        except discord.NotFound:
            pass  # Message already deleted
        except discord.Forbidden:
            # Bot doesn't have permission to delete user messages
            # This is expected if bot lacks "Manage Messages" permission
            pass
        except Exception as e:
            print(f"Unexpected error deleting original message: {e}")
        
        # Delete error message
        try:
            await error_message.delete()
        except discord.NotFound:
            pass  # Message already deleted
        except discord.Forbidden:
            # Bot doesn't have permission to delete its own message (very rare)
            pass
        except Exception as e:
            print(f"Unexpected error deleting error message: {e}")

    def get_user_data(self, user_id):
        """Get or create user data"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'balance': STARTING_BALANCE,
                'last_daily': None,
                'total_earned': STARTING_BALANCE,
                'total_spent': 0,
                'gambling_wins': 0,
                'gambling_losses': 0
            }
            self.save_users()
        return self.users[user_id]

    def update_balance(self, user_id, amount):
        """Update user balance and track earnings/spending"""
        user_data = self.get_user_data(user_id)
        user_data['balance'] += amount
        
        if amount > 0:
            user_data['total_earned'] += amount
        else:
            user_data['total_spent'] += abs(amount)
        
        self.save_users()
        return user_data['balance']

    @commands.command(name='balance', aliases=['bal'])
    async def check_balance(self, ctx, member: discord.Member = None):
        """Check your or someone else's balance"""
        target = member or ctx.author
        user_data = self.get_user_data(target.id)
        
        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Wallet",
            color=COLORS['primary']
        )
        embed.add_field(name="Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Total Earned", value=f"{user_data['total_earned']:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Total Spent", value=f"{user_data['total_spent']:,} {CURRENCY_NAME}", inline=True)
        
        # Gambling stats
        if user_data['gambling_wins'] > 0 or user_data['gambling_losses'] > 0:
            win_rate = user_data['gambling_wins'] / (user_data['gambling_wins'] + user_data['gambling_losses']) * 100
            embed.add_field(name="Gambling W/L", value=f"{user_data['gambling_wins']}/{user_data['gambling_losses']} ({win_rate:.1f}%)", inline=True)
        
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.command(name='daily')
    async def daily_reward(self, ctx):
        """Claim your daily reward!"""
        user_data = self.get_user_data(ctx.author.id)
        
        now = datetime.now()
        last_daily = user_data.get('last_daily')
        
        if last_daily:
            last_daily_date = datetime.fromisoformat(last_daily)
            if now - last_daily_date < timedelta(hours=24):
                time_left = timedelta(hours=24) - (now - last_daily_date)
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="⏰ Daily Already Claimed",
                    description=f"Come back in {hours}h {minutes}m for your next daily reward!",
                    color=COLORS['warning']
                )
                await ctx.send(embed=embed)
                return
        
        # Give daily reward
        reward = DAILY_REWARD + random.randint(-50, 100)  # Add some randomness
        self.update_balance(ctx.author.id, reward)
        user_data['last_daily'] = now.isoformat()
        self.save_users()
        
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You received **{reward:,} {CURRENCY_NAME}**!",
            color=COLORS['success']
        )
        embed.add_field(name="New Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='leaderboard', aliases=['lb', 'top'])
    async def leaderboard(self, ctx, page: int = 1):
        """View the richest users leaderboard"""
        if not self.users:
            await ctx.send("No users found in the economy system!")
            return
        
        # Sort users by balance
        sorted_users = sorted(self.users.items(), key=lambda x: x[1]['balance'], reverse=True)
        
        # Pagination
        per_page = 10
        total_pages = (len(sorted_users) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_users = sorted_users[start_idx:end_idx]
        
        embed = discord.Embed(
            title="🏆 Richest Users Leaderboard",
            color=COLORS['primary']
        )
        
        description = ""
        for i, (user_id, user_data) in enumerate(page_users, start=start_idx + 1):
            user = self.bot.get_user(int(user_id))
            username = user.display_name if user else f"User {user_id}"
            
            # Special titles for top users
            if i == 1:
                title = "👑 **RICHEST**"
            elif i == 2:
                title = "🥈 **2nd Place**"
            elif i == 3:
                title = "🥉 **3rd Place**"
            elif i <= 5:
                title = "💎 **Top 5**"
            elif i <= 10:
                title = "⭐ **Top 10**"
            else:
                title = ""
            
            description += f"**{i}.** {username} {title}\n💰 {user_data['balance']:,} {CURRENCY_NAME}\n\n"
        
        embed.description = description
        embed.set_footer(text=f"Page {page}/{total_pages} • Use !lb <page> to navigate")
        
        await ctx.send(embed=embed)

    @commands.command(name='gamble', aliases=['bet'])
    async def gamble(self, ctx, amount: str):
        """Gamble your coins! 50% chance to double your money! Usage: !gamble <amount|all|half>"""
        # Check if gambling is allowed in this channel
        if not self.is_gambling_allowed(ctx):
            await self.send_gambling_error(ctx)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        # Parse amount
        if amount.lower() == 'all':
            bet_amount = user_data['balance']
        elif amount.lower() == 'half':
            bet_amount = user_data['balance'] // 2
        else:
            try:
                bet_amount = int(amount)
            except ValueError:
                await ctx.send("❌ Invalid amount! Use a number, 'all', or 'half'")
                return
        
        if bet_amount <= 0:
            await ctx.send("❌ You need to bet a positive amount!")
            return
        
        if bet_amount > user_data['balance']:
            await ctx.send(f"❌ You don't have enough {CURRENCY_NAME}! Your balance: {user_data['balance']:,}")
            return
        
        # 50/50 gambling - fair odds
        won = random.random() < 0.5
        
        if won:
            # Win 2x the bet (double or nothing)
            winnings = bet_amount * 2
            self.update_balance(ctx.author.id, bet_amount)  # Net gain (bet amount back + profit)
            user_data['gambling_wins'] += 1
            
            embed = discord.Embed(
                title="🎉 You Won!",
                description=f"**Bet:** {bet_amount:,} {CURRENCY_NAME}\n**Won:** {winnings:,} {CURRENCY_NAME}\n**Profit:** +{bet_amount:,} {CURRENCY_NAME}",
                color=COLORS['success']
            )
        else:
            # Lose the bet
            self.update_balance(ctx.author.id, -bet_amount)
            user_data['gambling_losses'] += 1
            
            embed = discord.Embed(
                title="💸 You Lost!",
                description=f"**Lost:** {bet_amount:,} {CURRENCY_NAME}",
                color=COLORS['error']
            )
        
        self.save_users()
        
        embed.add_field(name="New Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=False)
        embed.set_footer(text=f"Win Rate: 50% • Double or Nothing!")
        
        await ctx.send(embed=embed)

    @commands.command(name='coinflip', aliases=['cf'])
    async def coinflip_gamble(self, ctx, choice: str, amount: str):
        """Bet on a coinflip! Usage: !coinflip heads/tails <amount>"""
        # Check if gambling is allowed in this channel
        if not self.is_gambling_allowed(ctx):
            await self.send_gambling_error(ctx)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        if choice.lower() not in ['heads', 'tails', 'h', 't']:
            await ctx.send("❌ Choose 'heads' or 'tails' (or 'h'/'t')")
            return
        
        # Parse amount
        if amount.lower() == 'all':
            bet_amount = user_data['balance']
        elif amount.lower() == 'half':
            bet_amount = user_data['balance'] // 2
        else:
            try:
                bet_amount = int(amount)
            except ValueError:
                await ctx.send("❌ Invalid amount! Use a number, 'all', or 'half'")
                return
        
        if bet_amount <= 0:
            await ctx.send("❌ You need to bet a positive amount!")
            return
        
        if bet_amount > user_data['balance']:
            await ctx.send(f"❌ You don't have enough {CURRENCY_NAME}! Your balance: {user_data['balance']:,}")
            return
        
        # Flip the coin
        result = random.choice(['heads', 'tails'])
        user_choice = choice.lower()
        if user_choice in ['h', 'heads']:
            user_choice = 'heads'
        else:
            user_choice = 'tails'
        
        won = result == user_choice
        
        embed = discord.Embed(
            title="🪙 Coinflip Results",
            color=COLORS['success'] if won else COLORS['error']
        )
        
        embed.add_field(name="Your Choice", value=user_choice.capitalize(), inline=True)
        embed.add_field(name="Result", value=f"🪙 {result.capitalize()}", inline=True)
        embed.add_field(name="Bet", value=f"{bet_amount:,} {CURRENCY_NAME}", inline=True)
        
        if won:
            winnings = bet_amount * 2  # Double or nothing
            self.update_balance(ctx.author.id, bet_amount)  # Net gain (already lost the bet, so add it back plus winnings)
            user_data['gambling_wins'] += 1
            
            embed.add_field(name="🎉 Result", value=f"**You Won!**\n+{bet_amount:,} {CURRENCY_NAME}", inline=False)
        else:
            self.update_balance(ctx.author.id, -bet_amount)
            user_data['gambling_losses'] += 1
            
            embed.add_field(name="💸 Result", value=f"**You Lost!**\n-{bet_amount:,} {CURRENCY_NAME}", inline=False)
        
        self.save_users()
        embed.add_field(name="New Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='gift', aliases=['pay'])
    async def gift_money(self, ctx, member: discord.Member, amount: int):
        """Gift money to another user from your balance"""
        if member == ctx.author:
            await ctx.send("❌ You can't gift money to yourself!")
            return
        
        if member.bot:
            await ctx.send("❌ You can't gift money to bots!")
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        if amount > user_data['balance']:
            await ctx.send(f"❌ You don't have enough {CURRENCY_NAME}! Your balance: {user_data['balance']:,}")
            return
        
        # Transfer money
        self.update_balance(ctx.author.id, -amount)
        self.update_balance(member.id, amount)
        
        embed = discord.Embed(
            title="🎁 Money Gifted",
            description=f"{ctx.author.mention} gifted {amount:,} {CURRENCY_NAME} to {member.mention}",
            color=COLORS['success']
        )
        embed.add_field(name="Your New Balance", value=f"{user_data['balance'] - amount:,} {CURRENCY_NAME}", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='give')
    @commands.has_permissions(administrator=True)
    async def admin_give_money(self, ctx, member: discord.Member, amount: int):
        """Admin command: Give money to any user (including yourself)"""
        if member.bot:
            await ctx.send("❌ You can't give money to bots!")
            return
        
        if amount == 0:
            await ctx.send("❌ Amount cannot be zero!")
            return
        
        # Admin can give positive or negative amounts
        old_balance = self.get_user_data(member.id)['balance']
        new_balance = self.update_balance(member.id, amount)
        
        embed = discord.Embed(
            title="💰 Admin Money Transfer",
            color=COLORS['success'] if amount > 0 else COLORS['warning']
        )
        
        if amount > 0:
            embed.description = f"**Admin {ctx.author.mention}** gave **{amount:,} {CURRENCY_NAME}** to {member.mention}"
        else:
            embed.description = f"**Admin {ctx.author.mention}** removed **{abs(amount):,} {CURRENCY_NAME}** from {member.mention}"
        
        embed.add_field(name="Previous Balance", value=f"{old_balance:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Change", value=f"{amount:+,} {CURRENCY_NAME}", inline=True)
        
        embed.set_footer(text="Admin Command")
        
        await ctx.send(embed=embed)

    @admin_give_money.error
    async def admin_give_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permissions to use the admin give command! Use `!gift` instead.")

    @commands.command(name='roll')
    async def roll_gamble(self, ctx, target: int, amount: str):
        """Roll 0-99! Higher targets = better payouts! Usage: !roll <target> <amount>"""
        # Check if gambling is allowed in this channel
        if not self.is_gambling_allowed(ctx):
            await self.send_gambling_error(ctx)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        if target < 1 or target > 99:
            await ctx.send("❌ Target must be between 1 and 99!")
            return
        
        # Parse amount
        if amount.lower() == 'all':
            bet_amount = user_data['balance']
        elif amount.lower() == 'half':
            bet_amount = user_data['balance'] // 2
        else:
            try:
                bet_amount = int(amount)
            except ValueError:
                await ctx.send("❌ Invalid amount! Use a number, 'all', or 'half'")
                return
        
        if bet_amount <= 0:
            await ctx.send("❌ You need to bet a positive amount!")
            return
        
        if bet_amount > user_data['balance']:
            await ctx.send(f"❌ You don't have enough {CURRENCY_NAME}! Your balance: {user_data['balance']:,}")
            return
        
        # Calculate payout multiplier based on target
        # Higher targets = lower win chance = higher payout
        # Formula: 99 / (100 - target) with house edge
        win_chance = (100 - target) / 100  # Chance to roll target or higher
        payout_multiplier = (99 / (100 - target)) * 0.98  # 2% house edge
        
        # Roll the dice
        roll_result = random.randint(0, 99)
        won = roll_result >= target
        
        embed = discord.Embed(
            title="🎲 Roll Results",
            color=COLORS['success'] if won else COLORS['error']
        )
        
        embed.add_field(name="Your Target", value=f"{target}+", inline=True)
        embed.add_field(name="Roll Result", value=f"🎲 {roll_result}", inline=True)
        embed.add_field(name="Win Chance", value=f"{win_chance:.1%}", inline=True)
        
        if won:
            winnings = int(bet_amount * payout_multiplier)
            profit = winnings - bet_amount
            self.update_balance(ctx.author.id, profit)
            user_data['gambling_wins'] += 1
            
            embed.add_field(name="🎉 You Won!", value=f"**Bet:** {bet_amount:,} {CURRENCY_NAME}\n**Won:** {winnings:,} {CURRENCY_NAME}\n**Profit:** +{profit:,} {CURRENCY_NAME}", inline=False)
        else:
            self.update_balance(ctx.author.id, -bet_amount)
            user_data['gambling_losses'] += 1
            
            embed.add_field(name="💸 You Lost!", value=f"**Lost:** {bet_amount:,} {CURRENCY_NAME}", inline=False)
        
        self.save_users()
        embed.add_field(name="New Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=False)
        embed.set_footer(text=f"Payout: {payout_multiplier:.2f}x • House Edge: 2%")
        
        await ctx.send(embed=embed)

    @commands.command(name='blackjack', aliases=['bj'])
    async def blackjack(self, ctx, amount: str):
        """Play Blackjack against the house! Usage: !blackjack <amount>"""
        # Check if gambling is allowed in this channel
        if not self.is_gambling_allowed(ctx):
            await self.send_gambling_error(ctx)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        # Parse amount
        if amount.lower() == 'all':
            bet_amount = user_data['balance']
        elif amount.lower() == 'half':
            bet_amount = user_data['balance'] // 2
        else:
            try:
                bet_amount = int(amount)
            except ValueError:
                await ctx.send("❌ Invalid amount! Use a number, 'all', or 'half'")
                return
        
        if bet_amount <= 0:
            await ctx.send("❌ You need to bet a positive amount!")
            return
        
        if bet_amount > user_data['balance']:
            await ctx.send(f"❌ You don't have enough {CURRENCY_NAME}! Your balance: {user_data['balance']:,}")
            return
        
        # Create deck
        suits = ['♠️', '♥️', '♦️', '♣️']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        deck = [(rank, suit) for suit in suits for rank in ranks]
        random.shuffle(deck)
        
        def card_value(card):
            rank = card[0]
            if rank in ['J', 'Q', 'K']:
                return 10
            elif rank == 'A':
                return 11  # We'll handle aces later
            else:
                return int(rank)
        
        def hand_value(hand):
            value = sum(card_value(card) for card in hand)
            aces = sum(1 for card in hand if card[0] == 'A')
            
            # Handle aces
            while value > 21 and aces > 0:
                value -= 10
                aces -= 1
            
            return value
        
        def format_hand(hand):
            return ' '.join([f"{card[0]}{card[1]}" for card in hand])
        
        # Deal initial cards
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        player_value = hand_value(player_hand)
        dealer_value = hand_value(dealer_hand)
        
        # Check for blackjack
        if player_value == 21:
            if dealer_value == 21:
                # Push (tie)
                embed = discord.Embed(
                    title="🃏 Blackjack - Push!",
                    description="Both got blackjack! It's a tie.",
                    color=COLORS['warning']
                )
                embed.add_field(name="Your Hand", value=f"{format_hand(player_hand)} = {player_value}", inline=True)
                embed.add_field(name="Dealer Hand", value=f"{format_hand(dealer_hand)} = {dealer_value}", inline=True)
                embed.add_field(name="Result", value="No money lost or gained", inline=False)
                await ctx.send(embed=embed)
                return
            else:
                # Player blackjack wins 1.5x
                winnings = int(bet_amount * 1.5)
                self.update_balance(ctx.author.id, winnings)
                user_data['gambling_wins'] += 1
                self.save_users()
                
                embed = discord.Embed(
                    title="🃏 Blackjack! You Win!",
                    color=COLORS['success']
                )
                embed.add_field(name="Your Hand", value=f"{format_hand(player_hand)} = {player_value}", inline=True)
                embed.add_field(name="Dealer Hand", value=f"{format_hand(dealer_hand)} = {dealer_value}", inline=True)
                embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME} (1.5x)", inline=False)
                embed.add_field(name="New Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=False)
                await ctx.send(embed=embed)
                return
        
        # Player's turn
        game_embed = discord.Embed(
            title="🃏 Blackjack Game",
            color=COLORS['primary']
        )
        game_embed.add_field(name="Your Hand", value=f"{format_hand(player_hand)} = {player_value}", inline=True)
        game_embed.add_field(name="Dealer Hand", value=f"{dealer_hand[0][0]}{dealer_hand[0][1]} ?", inline=True)
        game_embed.add_field(name="Options", value="React with 👊 to Hit or ✋ to Stand", inline=False)
        
        message = await ctx.send(embed=game_embed)
        await message.add_reaction('👊')  # Hit
        await message.add_reaction('✋')  # Stand
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['👊', '✋'] and reaction.message.id == message.id
        
        # Player hits/stands
        while player_value < 21:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=120, check=check)
                
                if str(reaction.emoji) == '👊':  # Hit
                    player_hand.append(deck.pop())
                    player_value = hand_value(player_hand)
                    
                    if player_value > 21:
                        break
                    
                    # Update embed
                    game_embed.set_field_at(0, name="Your Hand", value=f"{format_hand(player_hand)} = {player_value}", inline=True)
                    await message.edit(embed=game_embed)
                    
                elif str(reaction.emoji) == '✋':  # Stand
                    break
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Game timed out!")
                return
        
        # Check if player busted
        if player_value > 21:
            self.update_balance(ctx.author.id, -bet_amount)
            user_data['gambling_losses'] += 1
            self.save_users()
            
            embed = discord.Embed(
                title="💥 Bust! You Lose!",
                color=COLORS['error']
            )
            embed.add_field(name="Your Hand", value=f"{format_hand(player_hand)} = {player_value}", inline=True)
            embed.add_field(name="Dealer Hand", value=f"{format_hand(dealer_hand)} = {dealer_value}", inline=True)
            embed.add_field(name="Result", value=f"-{bet_amount:,} {CURRENCY_NAME}", inline=False)
            embed.add_field(name="New Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=False)
            await ctx.send(embed=embed)
            return
        
        # Dealer's turn
        while dealer_value < 17:
            dealer_hand.append(deck.pop())
            dealer_value = hand_value(dealer_hand)
        
        # Determine winner
        if dealer_value > 21:
            # Dealer busts, player wins
            self.update_balance(ctx.author.id, bet_amount)
            user_data['gambling_wins'] += 1
            result = "🎉 Dealer Busts! You Win!"
            result_value = f"+{bet_amount:,} {CURRENCY_NAME}"
            color = COLORS['success']
        elif player_value > dealer_value:
            # Player wins
            self.update_balance(ctx.author.id, bet_amount)
            user_data['gambling_wins'] += 1
            result = "🎉 You Win!"
            result_value = f"+{bet_amount:,} {CURRENCY_NAME}"
            color = COLORS['success']
        elif player_value < dealer_value:
            # Dealer wins
            self.update_balance(ctx.author.id, -bet_amount)
            user_data['gambling_losses'] += 1
            result = "💸 Dealer Wins!"
            result_value = f"-{bet_amount:,} {CURRENCY_NAME}"
            color = COLORS['error']
        else:
            # Push (tie)
            result = "🤝 Push! It's a Tie!"
            result_value = "No money lost or gained"
            color = COLORS['warning']
        
        self.save_users()
        
        final_embed = discord.Embed(
            title="🃏 Blackjack Results",
            color=color
        )
        final_embed.add_field(name="Your Hand", value=f"{format_hand(player_hand)} = {player_value}", inline=True)
        final_embed.add_field(name="Dealer Hand", value=f"{format_hand(dealer_hand)} = {dealer_value}", inline=True)
        final_embed.add_field(name="Result", value=f"{result}\n{result_value}", inline=False)
        final_embed.add_field(name="New Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=False)
        
        await ctx.send(embed=final_embed)

    @commands.command(name='slots', aliases=['slot'])
    async def slot_machine(self, ctx, amount: str):
        """Play the slot machine! Usage: !slots <amount>"""
        # Check if gambling is allowed in this channel
        if not self.is_gambling_allowed(ctx):
            await self.send_gambling_error(ctx)
            return
        
        user_data = self.get_user_data(ctx.author.id)
        
        # Parse amount
        if amount.lower() == 'all':
            bet_amount = user_data['balance']
        elif amount.lower() == 'half':
            bet_amount = user_data['balance'] // 2
        else:
            try:
                bet_amount = int(amount)
            except ValueError:
                await ctx.send("❌ Invalid amount! Use a number, 'all', or 'half'")
                return
        
        if bet_amount <= 0:
            await ctx.send("❌ You need to bet a positive amount!")
            return
        
        if bet_amount > user_data['balance']:
            await ctx.send(f"❌ You don't have enough {CURRENCY_NAME}! Your balance: {user_data['balance']:,}")
            return
        
        # Weighted reel system - each symbol has different probability
        # Higher weight = more likely to appear
        reel_weights = {
            '🍒': 35,   # Most common (35% chance)
            '🍋': 25,   # Common (25% chance)
            '🍊': 20,   # Common (20% chance)
            '🍇': 12,   # Uncommon (12% chance)
            '🔔': 5,    # Rare (5% chance)
            '7️⃣': 2,   # Very rare (2% chance)
            '💎': 1     # Ultra rare (1% chance)
        }
        
        # Pay table with realistic RTP (Return to Player) around 95%
        pay_table = (
            "**💰 PAY TABLE 💰**\n"
            "💎 💎 💎 = 500x 🎊\n"
            "7️⃣ 7️⃣ 7️⃣ = 100x 🔥\n"
            "🔔 🔔 🔔 = 50x ⭐\n"
            "🍇 🍇 🍇 = 25x 🍀\n"
            "🍊 🍊 🍊 = 15x 🎯\n"
            "🍋 🍋 🍋 = 10x 💫\n"
            "🍒 🍒 🍒 = 8x ❤️\n"
            "Any 2 Match = 2x 👍"
        )
        
        def spin_reel():
            """Spin a single reel using weighted probabilities"""
            symbols = list(reel_weights.keys())
            weights = list(reel_weights.values())
            return random.choices(symbols, weights=weights, k=1)[0]
        
        def generate_realistic_grid():
            """Generate a 3x3 grid with weighted probabilities"""
            return [[spin_reel() for _ in range(3)] for _ in range(3)]
        
        # Generate 3x3 grid (only middle row counts)
        def generate_grid():
            return generate_realistic_grid()
        
        def format_grid(grid):
            return (
                f"```\n"
                f"╔═══════════════════╗\n"
                f"║                   ║\n"
                f"║   {' '.join(grid[0])}   ║\n"
                f"║                   ║\n"
                f"║ ► {' '.join(grid[1])} ◄ ║ ← PAYLINE\n"
                f"║                   ║\n"
                f"║   {' '.join(grid[2])}   ║\n"
                f"║                   ║\n"
                f"╚═══════════════════╝\n"
                f"```"
            )
        
        # Create initial spinning embed with actual slot symbols
        spinning_grid = generate_grid()
        
        embed = discord.Embed(
            title="🎰 ═══ CLASSIC SLOT MACHINE ═══ 🎰",
            description=format_grid(spinning_grid),
            color=COLORS['primary']
        )
        embed.add_field(name="💰 Bet Amount", value=f"{bet_amount:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="🎲 Status", value="**SPINNING...**", inline=True)
        embed.add_field(name="Pay Table", value=pay_table, inline=False)
        
        message = await ctx.send(embed=embed)
        
        # Animation frames - gradually slow down
        animation_delays = [0.2, 0.3, 0.4, 0.5, 0.7, 0.9, 1.2]
        status_messages = [
            "**🌪️ SPINNING FAST...**",
            "**🔄 SPINNING...**", 
            "**� SPLOWING DOWN...**",
            "**🎯 ALMOST THERE...**",
            "**⏳ FINAL SPIN...**",
            "**🔥 STOPPING...**",
            "**✨ FINAL RESULT! ✨**"
        ]
        
        # Generate final result first
        final_grid = generate_grid()
        
        # Animate the spinning with only actual slot symbols
        for i, delay in enumerate(animation_delays):
            if i < len(animation_delays) - 1:
                # Show random combinations of actual slot symbols during spinning
                current_grid = generate_grid()
            else:
                current_grid = final_grid
            
            embed.description = format_grid(current_grid)
            embed.set_field_at(1, name="🎲 Status", value=status_messages[i], inline=True)
            await message.edit(embed=embed)
            await asyncio.sleep(delay)
        
        # Only the middle row (payline) counts for wins
        payline = final_grid[1]  # Middle row
        result1, result2, result3 = payline
        
        # Check for wins based on payline only
        if result1 == result2 == result3:
            # Three of a kind on payline
            if result1 == '💎':
                multiplier = 500  # Diamond mega jackpot
                result_text = "💎 MEGA JACKPOT! 💎"
            elif result1 == '7️⃣':
                multiplier = 100   # Lucky sevens
                result_text = "🔥 LUCKY SEVENS! 🔥"
            elif result1 == '🔔':
                multiplier = 50   # Bells
                result_text = "⭐ TRIPLE BELLS! ⭐"
            elif result1 == '🍇':
                multiplier = 25   # Grapes
                result_text = "�  TRIPLE GRAPES! �"
            elif result1 == '🍊':
                multiplier = 15   # Oranges
                result_text = "� TRIPLE  ORANGES! �"
            elif result1 == '🍋':
                multiplier = 10    # Lemons
                result_text = "💫 TRIPLE LEMONS! 💫"
            elif result1 == '🍒':
                multiplier = 8    # Cherries
                result_text = "❤️ TRIPLE CHERRIES! ❤️"
            
            winnings = bet_amount * multiplier
            self.update_balance(ctx.author.id, winnings - bet_amount)
            user_data['gambling_wins'] += 1
            color = COLORS['success']
            
        elif result1 == result2 or result2 == result3 or result1 == result3:
            # Two of a kind on payline
            multiplier = 2
            winnings = bet_amount * multiplier
            self.update_balance(ctx.author.id, winnings - bet_amount)
            user_data['gambling_wins'] += 1
            result_text = "🎊 DOUBLE MATCH! 🎊"
            color = COLORS['success']
            
        else:
            # No match - loss
            winnings = 0
            multiplier = 0
            self.update_balance(ctx.author.id, -bet_amount)
            user_data['gambling_losses'] += 1
            result_text = "💸 No Match"
            color = COLORS['error']
        
        self.save_users()
        
        # Final result embed with enhanced presentation
        if winnings > 0:
            if multiplier >= 100:
                title = f"🚨 ═══ MEGA JACKPOT! ═══ 🚨"
            elif multiplier >= 50:
                title = f"🔥 ═══ BIG WIN! ═══ 🔥"
            elif multiplier >= 10:
                title = f"⭐ ═══ NICE WIN! ═══ ⭐"
            else:
                title = f"🎉 ═══ WINNER! ═══ 🎉"
        else:
            title = f"🎰 ═══ SLOT RESULTS ═══ 🎰"
            
        final_embed = discord.Embed(
            title=title,
            description=format_grid(final_grid),
            color=color
        )
        
        # Enhanced payline display
        payline_display = f"**{' '.join(payline)}**"
        if winnings > 0:
            payline_display = f"🔥 **{' '.join(payline)}** 🔥"
            
        final_embed.add_field(name="🎯 Payline Result", value=payline_display, inline=True)
        final_embed.add_field(name="🏆 Result", value=result_text, inline=True)
        
        if winnings > 0:
            profit = winnings - bet_amount
            win_display = f"**+{profit:,} {CURRENCY_NAME}**\n({multiplier}x multiplier)"
            if multiplier >= 50:
                win_display = f"🎊 **+{profit:,} {CURRENCY_NAME}** 🎊\n🔥 {multiplier}x MEGA WIN! 🔥"
            final_embed.add_field(name="💰 Winnings", value=win_display, inline=True)
        else:
            final_embed.add_field(name="💸 Loss", value=f"**-{bet_amount:,} {CURRENCY_NAME}**", inline=True)
        
        final_embed.add_field(name="💳 New Balance", value=f"**{user_data['balance']:,} {CURRENCY_NAME}**", inline=True)
        final_embed.add_field(name="Pay Table", value=pay_table, inline=False)
        
        # Add footer with odds information
        if winnings > 0:
            if multiplier >= 100:
                # Calculate rough odds for the winning combination
                symbol_prob = reel_weights[result1] / sum(reel_weights.values())
                odds = int(1 / (symbol_prob ** 3))
                final_embed.set_footer(text=f"🎰 INCREDIBLE! Odds were roughly 1 in {odds:,}! 🎰")
            else:
                final_embed.set_footer(text="🎰 Congratulations! Play again for more chances to win! 🎰")
        else:
            final_embed.set_footer(text="🎰 Better luck next time! The jackpot is waiting! 🎰")
        
        await message.edit(embed=final_embed)
    
    @commands.command(name='gamblingchannels', aliases=['gc'])
    async def show_gambling_channels(self, ctx):
        """Show where gambling commands can be used"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.gambling_channels or not self.gambling_channels[guild_id]:
            embed = discord.Embed(
                title="🎰 Gambling Channels",
                description="Gambling is allowed in all channels!",
                color=COLORS['info']
            )
        else:
            channels = []
            for channel_id in self.gambling_channels[guild_id]:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channels.append(channel.mention)
            
            if channels:
                embed = discord.Embed(
                    title="🎰 Gambling Channels",
                    description=f"Gambling commands can be used in:\n" + "\n".join([f"• {ch}" for ch in channels]),
                    color=COLORS['info']
                )
                embed.add_field(
                    name="🎲 Gambling Commands",
                    value="• `!gamble` / `!bet`\n• `!roll`\n• `!blackjack` / `!bj`\n• `!slots` / `!slot`\n• `!coinflip` / `!cf`",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="🎰 Gambling Channels",
                    description="No valid gambling channels found.",
                    color=COLORS['warning']
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='slotodds', aliases=['odds'])
    async def slot_odds(self, ctx):
        """Show slot machine odds and probabilities"""
        # Weighted reel system (same as in slot machine)
        reel_weights = {
            '🍒': 35,   # Most common (35% chance)
            '🍋': 25,   # Common (25% chance)
            '🍊': 20,   # Common (20% chance)
            '🍇': 12,   # Uncommon (12% chance)
            '🔔': 5,    # Rare (5% chance)
            '7️⃣': 2,   # Very rare (2% chance)
            '💎': 1     # Ultra rare (1% chance)
        }
        
        total_weight = sum(reel_weights.values())
        
        embed = discord.Embed(
            title="🎰 Slot Machine Odds & Probabilities",
            description="Understanding your chances of winning:",
            color=COLORS['info']
        )
        
        # Symbol probabilities
        prob_text = ""
        for symbol, weight in reel_weights.items():
            prob = (weight / total_weight) * 100
            prob_text += f"{symbol} **{prob:.1f}%** chance per reel\n"
        
        embed.add_field(name="🎲 Symbol Probabilities", value=prob_text, inline=False)
        
        # Triple combinations odds
        odds_text = ""
        payouts = {
            '💎': (500, 1),
            '7️⃣': (100, 2),
            '🔔': (50, 5),
            '🍇': (25, 12),
            '🍊': (15, 20),
            '🍋': (10, 25),
            '🍒': (8, 35)
        }
        
        for symbol, (multiplier, weight) in payouts.items():
            prob = (weight / total_weight) ** 3 * 100
            odds = int(1 / ((weight / total_weight) ** 3))
            odds_text += f"{symbol} {symbol} {symbol} **{multiplier}x** - {prob:.3f}% (1 in {odds:,})\n"
        
        embed.add_field(name="🏆 Triple Combination Odds", value=odds_text, inline=False)
        
        # Two of a kind odds
        two_kind_prob = 0
        for symbol, weight in reel_weights.items():
            single_prob = weight / total_weight
            # Probability of exactly 2 matching (3 different combinations)
            two_kind_prob += 3 * (single_prob ** 2) * (1 - single_prob)
        
        embed.add_field(
            name="👍 Two of a Kind (2x payout)",
            value=f"**{two_kind_prob*100:.1f}%** chance (1 in {int(1/two_kind_prob):,})",
            inline=False
        )
        
        # Overall RTP estimate
        embed.add_field(
            name="📊 Return to Player (RTP)",
            value="Approximately **95%** - For every 100 coins bet, expect ~95 coins back over time",
            inline=False
        )
        
        embed.set_footer(text="🎰 Remember: Each spin is independent! Past results don't affect future spins.")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))