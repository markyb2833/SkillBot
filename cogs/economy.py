import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta
from config import COLORS, CURRENCY_NAME, DAILY_REWARD, STARTING_BALANCE

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/economy.json'
        self.users = self.load_users()

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
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
                
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

async def setup(bot):
    await bot.add_cog(Economy(bot))