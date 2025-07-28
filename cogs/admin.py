import discord
from discord.ext import commands
import json
import os
import asyncio
from config import COLORS, CURRENCY_NAME

class AdminView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='💰 Economy Stats', style=discord.ButtonStyle.primary, emoji='📊', custom_id='admin_economy_stats')
    async def economy_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Load economy data
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system not loaded!", ephemeral=True)
            return
        
        users = economy_cog.users
        if not users:
            await interaction.response.send_message("📊 No economy data found!", ephemeral=True)
            return
        
        # Calculate stats
        total_users = len(users)
        total_currency = sum(user['balance'] for user in users.values())
        avg_balance = total_currency / total_users
        richest_balance = max(user['balance'] for user in users.values())
        poorest_balance = min(user['balance'] for user in users.values())
        
        # Gambling stats
        total_wins = sum(user.get('gambling_wins', 0) for user in users.values())
        total_losses = sum(user.get('gambling_losses', 0) for user in users.values())
        total_games = total_wins + total_losses
        
        embed = discord.Embed(
            title="📊 Economy Statistics",
            color=COLORS['info']
        )
        embed.add_field(name="👥 Users", value=f"{total_users:,}", inline=True)
        embed.add_field(name="💰 Total Currency", value=f"{total_currency:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="📈 Average Balance", value=f"{avg_balance:,.0f} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="🏆 Richest User", value=f"{richest_balance:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="💸 Poorest User", value=f"{poorest_balance:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="🎲 Total Games", value=f"{total_games:,}", inline=True)
        
        if total_games > 0:
            win_rate = (total_wins / total_games) * 100
            embed.add_field(name="📊 Global Win Rate", value=f"{win_rate:.1f}%", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='🎁 Give Currency', style=discord.ButtonStyle.success, emoji='💸', custom_id='admin_give_currency')
    async def give_currency(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GiveCurrencyModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🗑️ Reset User', style=discord.ButtonStyle.danger, emoji='⚠️', custom_id='admin_reset_user')
    async def reset_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ResetUserModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='📋 User Lookup', style=discord.ButtonStyle.secondary, emoji='🔍', custom_id='admin_user_lookup')
    async def user_lookup(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = UserLookupModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🔄 Refresh Panel', style=discord.ButtonStyle.secondary, emoji='🔄', custom_id='admin_refresh_panel')
    async def refresh_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛠️ Bot Management Panel",
            description="Use the buttons below to manage the bot:",
            color=COLORS['primary']
        )
        embed.add_field(
            name="📊 Economy Stats", 
            value="View server economy statistics", 
            inline=False
        )
        embed.add_field(
            name="💸 Give Currency", 
            value="Give coins to a specific user", 
            inline=False
        )
        embed.add_field(
            name="🗑️ Reset User", 
            value="Reset a user's economy data", 
            inline=False
        )
        embed.add_field(
            name="🔍 User Lookup", 
            value="Look up detailed user information", 
            inline=False
        )
        embed.set_footer(text="Admin Panel • Only visible to administrators")
        
        await interaction.response.edit_message(embed=embed, view=self)

class GiveCurrencyModal(discord.ui.Modal, title='Give Currency to User'):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    user_id = discord.ui.TextInput(
        label='User ID or @mention',
        placeholder='123456789012345678 or @username',
        required=True,
        max_length=100
    )

    amount = discord.ui.TextInput(
        label='Amount',
        placeholder='1000',
        required=True,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse user
            user_input = self.user_id.value.strip()
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = int(user_input[2:-1].replace('!', ''))
            else:
                user_id = int(user_input)
            
            # Parse amount
            amount_value = int(self.amount.value)
            
            # Get user
            user = self.bot.get_user(user_id)
            if not user:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
                return
            
            # Update balance
            economy_cog = self.bot.get_cog('Economy')
            if not economy_cog:
                await interaction.response.send_message("❌ Economy system not loaded!", ephemeral=True)
                return
            
            new_balance = economy_cog.update_balance(user_id, amount_value)
            
            embed = discord.Embed(
                title="✅ Currency Given",
                description=f"Gave **{amount_value:,} {CURRENCY_NAME}** to {user.mention}",
                color=COLORS['success']
            )
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID or amount!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class ResetUserModal(discord.ui.Modal, title='Reset User Data'):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    user_id = discord.ui.TextInput(
        label='User ID or @mention',
        placeholder='123456789012345678 or @username',
        required=True,
        max_length=100
    )

    confirm = discord.ui.TextInput(
        label='Type "CONFIRM" to reset',
        placeholder='CONFIRM',
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value != "CONFIRM":
            await interaction.response.send_message("❌ You must type CONFIRM to reset user data!", ephemeral=True)
            return
        
        try:
            # Parse user
            user_input = self.user_id.value.strip()
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = int(user_input[2:-1].replace('!', ''))
            else:
                user_id = int(user_input)
            
            # Get user
            user = self.bot.get_user(user_id)
            if not user:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
                return
            
            # Reset user data
            economy_cog = self.bot.get_cog('Economy')
            if not economy_cog:
                await interaction.response.send_message("❌ Economy system not loaded!", ephemeral=True)
                return
            
            user_id_str = str(user_id)
            if user_id_str in economy_cog.users:
                del economy_cog.users[user_id_str]
                economy_cog.save_users()
            
            embed = discord.Embed(
                title="✅ User Reset",
                description=f"Reset all data for {user.mention}",
                color=COLORS['warning']
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class UserLookupModal(discord.ui.Modal, title='User Lookup'):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    user_id = discord.ui.TextInput(
        label='User ID or @mention',
        placeholder='123456789012345678 or @username',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse user
            user_input = self.user_id.value.strip()
            if user_input.startswith('<@') and user_input.endswith('>'):
                user_id = int(user_input[2:-1].replace('!', ''))
            else:
                user_id = int(user_input)
            
            # Get user
            user = self.bot.get_user(user_id)
            if not user:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
                return
            
            # Get user data
            economy_cog = self.bot.get_cog('Economy')
            if not economy_cog:
                await interaction.response.send_message("❌ Economy system not loaded!", ephemeral=True)
                return
            
            user_data = economy_cog.get_user_data(user_id)
            
            embed = discord.Embed(
                title=f"🔍 User Lookup: {user.display_name}",
                color=COLORS['info']
            )
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            
            embed.add_field(name="💰 Balance", value=f"{user_data['balance']:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="📈 Total Earned", value=f"{user_data['total_earned']:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="📉 Total Spent", value=f"{user_data['total_spent']:,} {CURRENCY_NAME}", inline=True)
            
            # Gambling stats
            wins = user_data.get('gambling_wins', 0)
            losses = user_data.get('gambling_losses', 0)
            total_games = wins + losses
            
            if total_games > 0:
                win_rate = (wins / total_games) * 100
                embed.add_field(name="🎲 Games Played", value=f"{total_games:,}", inline=True)
                embed.add_field(name="🏆 Win Rate", value=f"{win_rate:.1f}%", inline=True)
                embed.add_field(name="📊 W/L Ratio", value=f"{wins}/{losses}", inline=True)
            
            # Last daily
            last_daily = user_data.get('last_daily')
            if last_daily:
                from datetime import datetime
                last_daily_date = datetime.fromisoformat(last_daily)
                embed.add_field(name="🎁 Last Daily", value=last_daily_date.strftime("%Y-%m-%d %H:%M"), inline=True)
            
            embed.add_field(name="🆔 User ID", value=f"`{user_id}`", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/admin_panels.json'
        self.panel_data = self.load_panel_data()
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        # Schedule restoration tasks to run after bot is ready
        asyncio.create_task(self.startup_tasks())
    
    def load_panel_data(self):
        """Load panel data from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_panel_data(self):
        """Save panel data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.panel_data, f, indent=2)
    
    async def startup_tasks(self):
        """Run startup tasks after bot is ready"""
        await self.bot.wait_until_ready()
        
        # Add a small delay to ensure Discord is fully ready
        await asyncio.sleep(2)
        
        # Restart leaderboard update loops
        await self.restart_leaderboard_loops()
        
        # Restore admin panel views
        await self.restore_admin_panels()

    async def restore_admin_panels(self):
        """Restore admin panel views after bot restart"""
        
        if 'admin_panels' in self.panel_data:
            for guild_key, panel_info in list(self.panel_data['admin_panels'].items()):
                try:
                    guild_id = int(guild_key)
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        channel = guild.get_channel(panel_info['channel_id'])
                        if channel:
                            try:
                                # Try to fetch the message to verify it exists
                                await channel.fetch_message(panel_info['message_id'])
                                # Re-attach the view to the message
                                view = AdminView(self.bot)
                                self.bot.add_view(view, message_id=panel_info['message_id'])
                                print(f"Restored admin panel for guild {guild_id}")
                            except discord.NotFound:
                                # Message was deleted, remove from storage
                                del self.panel_data['admin_panels'][guild_key]
                                self.save_panel_data()
                                print(f"Cleaned up deleted admin panel reference for guild {guild_id}")
                        else:
                            # Channel was deleted, remove from storage
                            del self.panel_data['admin_panels'][guild_key]
                            self.save_panel_data()
                    else:
                        # Guild no longer accessible, remove from storage
                        del self.panel_data['admin_panels'][guild_key]
                        self.save_panel_data()
                except Exception as e:
                    print(f"Error restoring admin panel for guild {guild_key}: {e}")

    async def restart_leaderboard_loops(self):
        """Restart leaderboard update loops for all stored leaderboards"""
        
        if 'leaderboard_panels' in self.panel_data:
            # Create a copy of keys to avoid modification during iteration
            guild_ids = list(self.panel_data['leaderboard_panels'].keys())
            for guild_id_str in guild_ids:
                try:
                    guild_id = int(guild_id_str)
                    # Verify the guild and channel still exist
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        panel_info = self.panel_data['leaderboard_panels'][guild_id_str]
                        channel = self.bot.get_channel(panel_info['channel_id'])
                        if channel:
                            # Try to fetch the message to verify it exists
                            try:
                                await channel.fetch_message(panel_info['message_id'])
                                # If successful, start the update loop
                                asyncio.create_task(self.update_leaderboard_loop(guild_id))
                                print(f"🔄 Restarted leaderboard loop for guild {guild_id}")
                            except discord.NotFound:
                                # Message was deleted, remove from storage
                                print(f"❌ Leaderboard message deleted for guild {guild_id}, cleaning up")
                                del self.panel_data['leaderboard_panels'][guild_id_str]
                                self.save_panel_data()
                        else:
                            # Channel was deleted, remove from storage
                            print(f"❌ Leaderboard channel deleted for guild {guild_id}, cleaning up")
                            del self.panel_data['leaderboard_panels'][guild_id_str]
                            self.save_panel_data()
                    else:
                        # Guild no longer accessible, remove from storage
                        print(f"❌ Guild {guild_id} no longer accessible, cleaning up leaderboard")
                        del self.panel_data['leaderboard_panels'][guild_id_str]
                        self.save_panel_data()
                except Exception as e:
                    print(f"❌ Error restarting leaderboard loop for guild {guild_id_str}: {e}")
                    # Remove problematic entry
                    if guild_id_str in self.panel_data['leaderboard_panels']:
                        del self.panel_data['leaderboard_panels'][guild_id_str]
                        self.save_panel_data()
        else:
            print("ℹ️ No leaderboard panels found to restart")
    
    async def auto_delete_message(self, message, delay):
        """Auto-delete a message after a delay"""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except discord.NotFound:
            pass  # Message already deleted

    @commands.command(name='adminpanel')
    @commands.has_permissions(administrator=True)
    async def admin_panel(self, ctx):
        """Create the admin management panel (Admin only)"""
        embed = discord.Embed(
            title="🛠️ Bot Management Panel",
            description="Use the buttons below to manage the bot:",
            color=COLORS['primary']
        )
        embed.add_field(
            name="📊 Economy Stats", 
            value="View server economy statistics", 
            inline=False
        )
        embed.add_field(
            name="💸 Give Currency", 
            value="Give coins to a specific user", 
            inline=False
        )
        embed.add_field(
            name="🗑️ Reset User", 
            value="Reset a user's economy data", 
            inline=False
        )
        embed.add_field(
            name="🔍 User Lookup", 
            value="Look up detailed user information", 
            inline=False
        )
        embed.set_footer(text="Admin Panel • Only visible to administrators")
        
        view = AdminView(self.bot)
        message = await ctx.send(embed=embed, view=view)
        
        # Save admin panel message ID for persistence
        guild_key = str(ctx.guild.id)
        if 'admin_panels' not in self.panel_data:
            self.panel_data['admin_panels'] = {}
        
        self.panel_data['admin_panels'][guild_key] = {
            'channel_id': ctx.channel.id,
            'message_id': message.id
        }
        self.save_panel_data()

    @commands.command(name='setbalance')
    @commands.has_permissions(administrator=True)
    async def set_balance(self, ctx, member: discord.Member, amount: int):
        """Set a user's balance directly (Admin only)"""
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        # Get current balance and calculate difference
        user_data = economy_cog.get_user_data(member.id)
        current_balance = user_data['balance']
        difference = amount - current_balance
        
        # Update balance
        economy_cog.update_balance(member.id, difference)
        
        embed = discord.Embed(
            title="✅ Balance Updated",
            description=f"Set {member.mention}'s balance to **{amount:,} {CURRENCY_NAME}**",
            color=COLORS['success']
        )
        embed.add_field(name="Previous Balance", value=f"{current_balance:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="New Balance", value=f"{amount:,} {CURRENCY_NAME}", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='economyreset')
    @commands.has_permissions(administrator=True)
    async def economy_reset(self, ctx, confirm: str = None):
        """Reset the entire economy (Admin only) - Use 'CONFIRM' to execute"""
        if confirm != "CONFIRM":
            embed = discord.Embed(
                title="⚠️ Economy Reset",
                description="This will **permanently delete** all user economy data!\n\nTo confirm, use: `!economyreset CONFIRM`",
                color=COLORS['error']
            )
            await ctx.send(embed=embed)
            return
        
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        # Backup current data count
        user_count = len(economy_cog.users)
        
        # Reset economy
        economy_cog.users = {}
        economy_cog.save_users()
        
        embed = discord.Embed(
            title="🗑️ Economy Reset Complete",
            description=f"Deleted data for **{user_count}** users.\nAll balances have been reset.",
            color=COLORS['warning']
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='setgamblingchannel', aliases=['sgc'])
    @commands.has_permissions(administrator=True)
    async def set_gambling_channel(self, ctx, channel: discord.TextChannel = None):
        """Set a channel where gambling commands can be used (Admin only)"""
        if channel is None:
            channel = ctx.channel
        
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        guild_id = str(ctx.guild.id)
        if guild_id not in economy_cog.gambling_channels:
            economy_cog.gambling_channels[guild_id] = []
        
        if channel.id in economy_cog.gambling_channels[guild_id]:
            embed = discord.Embed(
                title="⚠️ Channel Already Set",
                description=f"{channel.mention} is already a gambling channel!",
                color=COLORS['warning']
            )
        else:
            economy_cog.gambling_channels[guild_id].append(channel.id)
            economy_cog.save_gambling_channels()
            
            embed = discord.Embed(
                title="✅ Gambling Channel Set",
                description=f"Gambling commands can now be used in {channel.mention}",
                color=COLORS['success']
            )
            embed.add_field(
                name="🎰 Affected Commands",
                value="• `!gamble` / `!bet`\n• `!roll`\n• `!blackjack` / `!bj`\n• `!slots` / `!slot`",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='removegamblingchannel', aliases=['rgc'])
    @commands.has_permissions(administrator=True)
    async def remove_gambling_channel(self, ctx, channel: discord.TextChannel = None):
        """Remove a gambling channel restriction (Admin only)"""
        if channel is None:
            channel = ctx.channel
        
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        guild_id = str(ctx.guild.id)
        if guild_id not in economy_cog.gambling_channels or channel.id not in economy_cog.gambling_channels[guild_id]:
            embed = discord.Embed(
                title="⚠️ Channel Not Set",
                description=f"{channel.mention} is not a gambling channel!",
                color=COLORS['warning']
            )
        else:
            economy_cog.gambling_channels[guild_id].remove(channel.id)
            if not economy_cog.gambling_channels[guild_id]:
                del economy_cog.gambling_channels[guild_id]
            economy_cog.save_gambling_channels()
            
            embed = discord.Embed(
                title="✅ Gambling Channel Removed",
                description=f"Gambling commands can no longer be used in {channel.mention}",
                color=COLORS['success']
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='cleargamblingchannels', aliases=['cgc'])
    @commands.has_permissions(administrator=True)
    async def clear_gambling_channels(self, ctx):
        """Remove all gambling channel restrictions (allows gambling everywhere) (Admin only)"""
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        guild_id = str(ctx.guild.id)
        if guild_id in economy_cog.gambling_channels:
            del economy_cog.gambling_channels[guild_id]
            economy_cog.save_gambling_channels()
        
        embed = discord.Embed(
            title="✅ All Gambling Restrictions Cleared",
            description="Gambling commands can now be used in any channel",
            color=COLORS['success']
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='listgamblingchannels', aliases=['lgc'])
    @commands.has_permissions(administrator=True)
    async def list_gambling_channels(self, ctx):
        """List all gambling channels (Admin only)"""
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        guild_id = str(ctx.guild.id)
        if guild_id not in economy_cog.gambling_channels or not economy_cog.gambling_channels[guild_id]:
            embed = discord.Embed(
                title="🎰 Gambling Channels",
                description="No gambling channel restrictions set.\nGambling is allowed in all channels.",
                color=COLORS['info']
            )
        else:
            channels = []
            for channel_id in economy_cog.gambling_channels[guild_id]:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channels.append(f"• {channel.mention}")
                else:
                    # Clean up deleted channels
                    economy_cog.gambling_channels[guild_id].remove(channel_id)
            
            if channels:
                embed = discord.Embed(
                    title="🎰 Gambling Channels",
                    description="Gambling commands are restricted to:\n" + "\n".join(channels),
                    color=COLORS['info']
                )
            else:
                embed = discord.Embed(
                    title="🎰 Gambling Channels",
                    description="No valid gambling channels found.\nAll restrictions have been cleared.",
                    color=COLORS['warning']
                )
                del economy_cog.gambling_channels[guild_id]
            
            economy_cog.save_gambling_channels()
        
        await ctx.send(embed=embed)

    @admin_panel.error
    @set_balance.error
    @economy_reset.error
    @set_gambling_channel.error
    @remove_gambling_channel.error
    @clear_gambling_channels.error
    @list_gambling_channels.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permissions to use this command!")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")

    def get_command_categories(self):
        """Automatically categorize commands from all loaded cogs"""
        categories = {
            "💰 Economy Commands": [],
            "🎰 Gambling Commands": [],
            "🎮 Game Finder Commands": [],
            "🎉 Fun Commands": [],
            "⚙️ Admin Commands": []
        }
        
        # Define command categorization
        economy_commands = ['balance', 'bal', 'daily', 'gift', 'pay', 'leaderboard', 'lb', 'top']
        gambling_commands = ['gamble', 'bet', 'roll', 'coinflip', 'cf', 'blackjack', 'bj', 'slots', 'slot', 'gamblingchannels', 'gc']
        game_finder_commands = ['searchgame', 'sg', 'lfg', 'mygames', 'removegame', 'rg', 'lfginfo']
        admin_commands = [
            # Administrator permission commands
            'adminpanel', 'give', 'setbalance', 'economyreset',
            'setupcommandspanel', 'setupadmincommandspanel', 'updatecommandspanel',
            'setgamblingchannel', 'sgc', 'removegamblingchannel', 'rgc', 
            'cleargamblingchannels', 'cgc', 'listgamblingchannels', 'lgc',
            # Manage channels permission commands  
            'setuplfgpanel', 'setlfgchannel', 'removelfgchannel',
            'setupleaderboard', 'sethofchannel', 'removehofchannel'
        ]
        
        # Get all commands from all cogs
        for cog_name, cog in self.bot.cogs.items():
            for command in cog.get_commands():
                if command.hidden:
                    continue
                
                # Check if command requires admin permissions
                is_admin_command = False
                
                # Check if command has permission checks
                if hasattr(command, 'checks') and command.checks:
                    for check in command.checks:
                        check_str = str(check)
                        # Check for administrator permission requirement
                        if 'administrator=True' in check_str:
                            is_admin_command = True
                            break
                        # Check for manage_channels permission requirement (also admin-level)
                        if 'manage_channels=True' in check_str:
                            is_admin_command = True
                            break
                
                # Also check by command name/alias as fallback
                if (command.name in admin_commands or 
                    any(alias in admin_commands for alias in command.aliases)):
                    is_admin_command = True
                
                # Create command signature
                signature = f"!{command.name}"
                if command.signature:
                    signature += f" {command.signature}"
                
                # Get description and truncate if too long
                description = command.help or command.brief or "No description available"
                if description.endswith('"""') or description.endswith("'''"):
                    description = description.split('\n')[0]  # Take first line only
                
                # Truncate long descriptions - increased limit
                if len(description) > 100:
                    description = description[:97] + "..."
                
                command_line = f"`{signature}` - {description}"
                
                # Add aliases if they exist (but limit them and make more compact)
                if command.aliases:
                    aliases = ', '.join([f'!{alias}' for alias in command.aliases[:2]])  # Max 2 aliases for space
                    if len(command.aliases) > 2:
                        aliases += f" +{len(command.aliases) - 2}"
                    command_line += f" ({aliases})"
                
                # Categorize command - admin commands first
                if is_admin_command:
                    categories["⚙️ Admin Commands"].append(command_line)
                elif command.name in economy_commands or any(alias in economy_commands for alias in command.aliases):
                    categories["💰 Economy Commands"].append(command_line)
                elif command.name in gambling_commands or any(alias in gambling_commands for alias in command.aliases):
                    categories["🎰 Gambling Commands"].append(command_line)
                elif command.name in game_finder_commands or any(alias in game_finder_commands for alias in command.aliases):
                    categories["🎮 Game Finder Commands"].append(command_line)
                else:
                    categories["🎉 Fun Commands"].append(command_line)
        
        return categories

    @commands.command(name='setupcommandspanel')
    @commands.has_permissions(administrator=True)
    async def setup_commands_panel(self, ctx):
        """Set up the persistent commands help panel (non-admin commands only) (Admin only)"""
        embeds = await self.create_commands_embeds(ctx.author, include_admin=False)
        messages = []
        
        # Send all embeds as separate messages
        for embed in embeds:
            message = await ctx.send(embed=embed)
            messages.append(message.id)
        
        # Store message info for potential updates
        guild_key = str(ctx.guild.id)
        if 'command_panels' not in self.panel_data:
            self.panel_data['command_panels'] = {}
        
        self.panel_data['command_panels'][guild_key] = {
            'channel_id': ctx.channel.id,
            'message_ids': messages,
            'include_admin': False
        }
        self.save_panel_data()
        
        # Send confirmation
        confirm_embed = discord.Embed(
            title="✅ Public Commands Panel Created",
            description=f"Public commands panel ({len(embeds)} messages) is now active in {ctx.channel.mention}",
            color=COLORS['success']
        )
        confirm_embed.add_field(
            name="� Panel Type",
            value="This panel shows non-admin commands only - safe for public channels.",
            inline=False
        )
        confirm_embed.add_field(
            name="💡 Tip",
            value="Pin these messages so users can always find the commands!\nUse `!setupadmincommandspanel` for a panel with admin commands.",
            inline=False
        )
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        
        # Auto-delete confirmation after 10 seconds
        asyncio.create_task(self.auto_delete_message(confirm_msg, 10))

    async def create_commands_embeds(self, user, include_admin=False):
        """Create multiple command embeds to avoid truncation"""
        categories = self.get_command_categories()
        embeds = []
        
        # Filter categories based on include_admin parameter
        filtered_categories = {}
        for category_name, commands in categories.items():
            if not commands:
                continue
            # Skip admin commands unless specifically requested
            if category_name == "⚙️ Admin Commands" and not include_admin:
                continue
            filtered_categories[category_name] = commands
        
        if not filtered_categories:
            embed = discord.Embed(
                title="📋 Bot Commands Guide",
                description="No commands available for your permission level.",
                color=COLORS['info']
            )
            return [embed]
        
        # Create main header embed
        title = "📋 Bot Commands Guide" + (" (Including Admin)" if include_admin else "")
        description = "Here are all available commands organized by category:"
        if not include_admin:
            description += "\n\n*Admin commands are hidden. Use `!setupadmincommandspanel` to see all commands.*"
        
        header_embed = discord.Embed(
            title=title,
            description=description,
            color=COLORS['info']
        )
        header_embed.add_field(
            name="📚 Categories Available",
            value="\n".join([f"• {category}" for category in filtered_categories.keys()]),
            inline=False
        )
        header_embed.set_footer(text="🔄 This panel stays active • Use commands anywhere in the server")
        embeds.append(header_embed)
        
        # Create separate embeds for each category or group of categories
        current_embed = None
        current_embed_size = 0
        
        for category_name, commands in filtered_categories.items():
            # Build full command text for this category
            command_text = "\n".join(commands)
            category_field_size = len(category_name) + len(command_text) + 50  # Buffer for formatting
            
            # If this category is too big for one embed or would make current embed too big
            if category_field_size > 900 or (current_embed and current_embed_size + category_field_size > 5000):
                # Finish current embed if it exists
                if current_embed:
                    embeds.append(current_embed)
                
                # Start new embed
                current_embed = discord.Embed(
                    title=f"📋 Commands - {category_name}",
                    color=COLORS['info']
                )
                current_embed_size = 0
            
            # If no current embed, create one
            if not current_embed:
                current_embed = discord.Embed(
                    title="📋 Bot Commands",
                    color=COLORS['info']
                )
                current_embed_size = 0
            
            # If category is too big for one field, split it
            if len(command_text) > 1000:
                command_chunks = []
                current_chunk = ""
                
                for command in commands:
                    if len(current_chunk) + len(command) + 1 > 1000:
                        if current_chunk:
                            command_chunks.append(current_chunk)
                        current_chunk = command
                    else:
                        if current_chunk:
                            current_chunk += "\n" + command
                        else:
                            current_chunk = command
                
                if current_chunk:
                    command_chunks.append(current_chunk)
                
                # Add chunks as separate fields
                for i, chunk in enumerate(command_chunks):
                    field_name = f"{category_name}" if i == 0 else f"{category_name} (cont.)"
                    current_embed.add_field(name=field_name, value=chunk, inline=False)
                    current_embed_size += len(field_name) + len(chunk)
            else:
                # Add as single field
                current_embed.add_field(name=category_name, value=command_text, inline=False)
                current_embed_size += len(category_name) + len(command_text)
        
        # Add final embed if it exists
        if current_embed:
            embeds.append(current_embed)
        
        # Add footer to all embeds except header
        for i, embed in enumerate(embeds[1:], 1):
            embed.set_footer(text=f"Page {i}/{len(embeds)-1} • Use commands anywhere in the server")
        
        return embeds

    @commands.command(name='setupadmincommandspanel')
    @commands.has_permissions(administrator=True)
    async def setup_admin_commands_panel(self, ctx):
        """Set up the persistent commands help panel including admin commands (Admin only)"""
        embeds = await self.create_commands_embeds(ctx.author, include_admin=True)
        messages = []
        
        # Send all embeds as separate messages
        for embed in embeds:
            message = await ctx.send(embed=embed)
            messages.append(message.id)
        
        # Store message info for potential updates
        guild_key = str(ctx.guild.id)
        if 'command_panels' not in self.panel_data:
            self.panel_data['command_panels'] = {}
        
        self.panel_data['command_panels'][guild_key] = {
            'channel_id': ctx.channel.id,
            'message_ids': messages,
            'include_admin': True
        }
        self.save_panel_data()
        
        # Send confirmation
        confirm_embed = discord.Embed(
            title="✅ Admin Commands Panel Created",
            description=f"Complete commands panel with admin commands ({len(embeds)} messages) is now active in {ctx.channel.mention}",
            color=COLORS['success']
        )
        confirm_embed.add_field(
            name="⚠️ Note",
            value="This panel includes admin commands. Consider using this in admin-only channels.",
            inline=False
        )
        confirm_embed.add_field(
            name="💡 Tip",
            value="Pin these messages for easy reference!",
            inline=False
        )
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        
        # Auto-delete confirmation after 10 seconds
        asyncio.create_task(self.auto_delete_message(confirm_msg, 10))

    @commands.command(name='updatecommandspanel')
    @commands.has_permissions(administrator=True)
    async def update_commands_panel(self, ctx):
        """Update the commands panel with current commands (Admin only)"""
        guild_key = str(ctx.guild.id)
        if 'command_panels' not in self.panel_data or guild_key not in self.panel_data['command_panels']:
            await ctx.send("❌ No commands panel found! Use `!setupcommandspanel` first.")
            return
        
        msg_info = self.panel_data['command_panels'][guild_key]
        channel = self.bot.get_channel(msg_info['channel_id'])
        
        if not channel:
            await ctx.send("❌ Commands panel channel no longer exists!")
            del self.panel_data['command_panels'][guild_key]
            self.save_panel_data()
            return
        
        try:
            # Delete old messages
            for message_id in msg_info['message_ids']:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.delete()
                except discord.NotFound:
                    pass  # Message already deleted
            
            # Create new messages with the same admin setting as before
            include_admin = msg_info.get('include_admin', False)
            embeds = await self.create_commands_embeds(ctx.author, include_admin=include_admin)
            new_message_ids = []
            
            for embed in embeds:
                message = await channel.send(embed=embed)
                new_message_ids.append(message.id)
            
            # Update stored message IDs
            self.panel_data['command_panels'][guild_key]['message_ids'] = new_message_ids
            self.save_panel_data()
            
            panel_type = "Admin" if include_admin else "Public"
            confirm_embed = discord.Embed(
                title="✅ Commands Panel Updated",
                description=f"{panel_type} commands panel has been refreshed with {len(embeds)} messages!",
                color=COLORS['success']
            )
            confirm_msg = await ctx.send(embed=confirm_embed)
            
            # Auto-delete confirmation
            asyncio.create_task(self.auto_delete_message(confirm_msg, 5))
            
        except Exception as e:
            await ctx.send(f"❌ Error updating commands panel: {str(e)}\nUse `!setupcommandspanel` to create a new one.")
            if guild_key in self.panel_data.get('command_panels', {}):
                del self.panel_data['command_panels'][guild_key]
                self.save_panel_data()

    @commands.command(name='setupleaderboard')
    @commands.has_permissions(manage_channels=True)
    async def setup_leaderboard(self, ctx):
        """Set up the auto-updating leaderboard panel (Manage Channels permission required)"""
        economy_cog = self.bot.get_cog('Economy')
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        # Create initial leaderboard
        embed = await self.create_leaderboard_embed(economy_cog)
        message = await ctx.send(embed=embed)
        
        # Store message info for updates
        guild_key = str(ctx.guild.id)
        if 'leaderboard_panels' not in self.panel_data:
            self.panel_data['leaderboard_panels'] = {}
        
        self.panel_data['leaderboard_panels'][guild_key] = {
            'channel_id': ctx.channel.id,
            'message_id': message.id
        }
        self.save_panel_data()
        
        # Start auto-update task
        asyncio.create_task(self.update_leaderboard_loop(ctx.guild.id))
        
        # Send confirmation
        confirm_embed = discord.Embed(
            title="✅ Leaderboard Panel Created",
            description=f"Auto-updating leaderboard is now active in {ctx.channel.mention}",
            color=COLORS['success']
        )
        confirm_embed.add_field(
            name="🔄 Auto-Update",
            value="Updates every 5 minutes automatically",
            inline=False
        )
        confirm_embed.add_field(
            name="💡 Tip",
            value="Pin this message so users can always see the rankings!",
            inline=False
        )
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        
        # Auto-delete confirmation after 10 seconds
        asyncio.create_task(self.auto_delete_message(confirm_msg, 10))

    async def create_leaderboard_embed(self, economy_cog):
        """Create the leaderboard embed"""
        users = economy_cog.users
        
        if not users:
            embed = discord.Embed(
                title="🏆 Economy Leaderboard",
                description="No users found in the economy system yet!",
                color=COLORS['info']
            )
            embed.set_footer(text="🔄 Auto-updates every 5 minutes")
            return embed
        
        # Sort users by balance
        sorted_users = sorted(users.items(), key=lambda x: x[1]['balance'], reverse=True)
        
        embed = discord.Embed(
            title="🏆 Economy Leaderboard",
            description="Top richest users in the server:",
            color=COLORS['primary']
        )
        
        # Show top 10 users
        leaderboard_text = ""
        for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):
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
            else:
                title = ""
            
            leaderboard_text += f"**{i}.** {username} {title}\n💰 {user_data['balance']:,} {CURRENCY_NAME}\n\n"
        
        embed.description = f"Top richest users in the server:\n\n{leaderboard_text}"
        
        # Add stats
        total_users = len(users)
        total_currency = sum(user['balance'] for user in users.values())
        avg_balance = total_currency / total_users if total_users > 0 else 0
        
        embed.add_field(
            name="📊 Server Stats",
            value=f"👥 {total_users} users\n💰 {total_currency:,} total {CURRENCY_NAME}\n📈 {avg_balance:,.0f} average balance",
            inline=True
        )
        
        # Gambling stats
        total_wins = sum(user.get('gambling_wins', 0) for user in users.values())
        total_losses = sum(user.get('gambling_losses', 0) for user in users.values())
        total_games = total_wins + total_losses
        
        if total_games > 0:
            win_rate = (total_wins / total_games) * 100
            embed.add_field(
                name="🎲 Gambling Stats",
                value=f"🎮 {total_games:,} games played\n🏆 {win_rate:.1f}% global win rate",
                inline=True
            )
        
        from datetime import datetime
        embed.set_footer(text=f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')} • Updates every 5 minutes")
        
        return embed

    async def update_leaderboard_loop(self, guild_id):
        """Auto-update leaderboard every 5 minutes"""
        print(f"🔄 Starting leaderboard update loop for guild {guild_id}")
        
        while True:
            try:
                print(f"💤 Leaderboard loop sleeping for 5 minutes (guild {guild_id})")
                await asyncio.sleep(300)  # 5 minutes
                print(f"⏰ Leaderboard loop waking up to update (guild {guild_id})")
                
                guild_key = str(guild_id)
                if 'leaderboard_panels' not in self.panel_data or guild_key not in self.panel_data['leaderboard_panels']:
                    print(f"❌ Leaderboard panel removed for guild {guild_id}, stopping loop")
                    break  # Stop if leaderboard was removed
                
                economy_cog = self.bot.get_cog('Economy')
                if not economy_cog:
                    print(f"⚠️ Economy cog not found for guild {guild_id}, retrying in 5 minutes")
                    continue
                
                # Get message info
                msg_info = self.panel_data['leaderboard_panels'][guild_key]
                channel = self.bot.get_channel(msg_info['channel_id'])
                
                if not channel:
                    print(f"❌ Channel deleted for leaderboard guild {guild_id}, stopping loop")
                    del self.panel_data['leaderboard_panels'][guild_key]
                    self.save_panel_data()
                    break
                
                try:
                    message = await channel.fetch_message(msg_info['message_id'])
                    embed = await self.create_leaderboard_embed(economy_cog)
                    await message.edit(embed=embed)
                    print(f"✅ Updated leaderboard for guild {guild_id}")
                except discord.NotFound:
                    # Message was deleted, stop updating
                    print(f"❌ Leaderboard message deleted for guild {guild_id}, stopping loop")
                    del self.panel_data['leaderboard_panels'][guild_key]
                    self.save_panel_data()
                    break
                except Exception as e:
                    print(f"⚠️ Temporary error updating leaderboard for guild {guild_id}: {e}")
                    # Continue the loop instead of breaking - temporary errors shouldn't stop the loop
                    continue
                    
            except Exception as e:
                print(f"⚠️ Error in leaderboard update loop for guild {guild_id}: {e}")
                # Wait a bit longer before retrying on major errors
                await asyncio.sleep(60)
                continue  # Don't break - keep trying
        
        print(f"🛑 Leaderboard update loop stopped for guild {guild_id}")

    async def auto_delete_message(self, message, delay):
        """Auto-delete message after delay"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except:
            pass

    @setup_commands_panel.error
    @setup_leaderboard.error
    async def panel_setup_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Channels' permission to set up panels!")

async def setup(bot):
    await bot.add_cog(Admin(bot))