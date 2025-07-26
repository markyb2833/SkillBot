import discord
from discord.ext import commands
import json
import os
import aiohttp
import asyncio
from datetime import datetime
from config import COLORS

class GameSearchView(discord.ui.View):
    def __init__(self, games, user_id):
        super().__init__(timeout=60)
        self.games = games
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Choose a game to add to your roles...",
        min_values=1,
        max_values=1
    )
    async def game_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your game search!", ephemeral=True, delete_after=10)
            return

        selected_game = next(game for game in self.games if str(game['id']) == select.values[0])
        
        # Get or create the game role
        role_name = f"🎮 {selected_game['name']}"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        
        if not role:
            try:
                # Create new role
                role = await interaction.guild.create_role(
                    name=role_name,
                    color=discord.Color.blue(),
                    mentionable=True,
                    reason=f"Game role created for {selected_game['name']}"
                )
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to create roles!", ephemeral=True, delete_after=15)
                return
        
        # Add role to user
        if role in interaction.user.roles:
            await interaction.response.send_message(f"❌ You already have the **{selected_game['name']}** role!", ephemeral=True, delete_after=15)
            return
        
        try:
            await interaction.user.add_roles(role)
            
            # Save game data
            cog = interaction.client.get_cog('GroupFinder')
            if cog:
                cog.save_game_role(interaction.guild.id, selected_game, role.id)
            
            embed = discord.Embed(
                title="✅ Game Role Added!",
                description=f"You now have the **{selected_game['name']}** role!",
                color=COLORS['success']
            )
            embed.add_field(
                name="🔔 LFG Usage", 
                value=f"Use `!lfg {selected_game['name']}` to find other players!", 
                inline=False
            )
            embed.set_thumbnail(url=selected_game.get('background_image', ''))
            
            embed.set_footer(text="Auto-deletes in 15s")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
            
            # Delete the original search message after successful role assignment
            try:
                await interaction.message.delete()
            except:
                pass
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign roles!", ephemeral=True, delete_after=15)

class LFGPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog

    @discord.ui.button(label='🔍 Search Games', style=discord.ButtonStyle.primary, emoji='🔍', custom_id='lfg_search_games')
    async def search_games_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = GameSearchModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='📢 Looking for Group', style=discord.ButtonStyle.success, emoji='📢', custom_id='lfg_looking_for_group')
    async def lfg_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_key = str(interaction.guild.id)
        
        if guild_key not in self.cog.game_roles or 'games' not in self.cog.game_roles[guild_key]:
            await interaction.response.send_message("❌ No game roles found! Use the Search Games button first!", ephemeral=True, delete_after=15)
            return

        # Get user's game roles
        user_game_roles = []
        for game_name_key, game_data in self.cog.game_roles[guild_key]['games'].items():
            role = interaction.guild.get_role(game_data['role_id'])
            if role and role in interaction.user.roles:
                user_game_roles.append(game_data)

        if not user_game_roles:
            await interaction.response.send_message("❌ You don't have any game roles! Use the Search Games button to add some!", ephemeral=True, delete_after=15)
            return

        # Create LFG selection embed
        embed = discord.Embed(
            title="🎮 Select Game for LFG",
            description=f"Choose from your {len(user_game_roles)} game roles:",
            color=COLORS['primary']
        )

        # Create select menu options
        options = []
        for game_data in user_game_roles[:25]:  # Discord limit is 25 options
            role = interaction.guild.get_role(game_data['role_id'])
            member_count = len(role.members) if role else 0
            
            options.append(discord.SelectOption(
                label=game_data['name'],
                description=f"👥 {member_count} members with this role",
                value=game_data['name'],
                emoji="🎮"
            ))

        view = LFGSelectView(user_game_roles, interaction.user.id, self.cog)
        view.game_select.options = options

        embed.set_footer(text="🔒 Only you can select • Auto-deletes in 60s")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=60)

    @discord.ui.button(label='📋 My Games', style=discord.ButtonStyle.secondary, emoji='📋', custom_id='lfg_my_games')
    async def my_games_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_key = str(interaction.guild.id)
        user_game_roles = []
        
        if guild_key in self.cog.game_roles and 'games' in self.cog.game_roles[guild_key]:
            for game_name, game_data in self.cog.game_roles[guild_key]['games'].items():
                role = interaction.guild.get_role(game_data['role_id'])
                if role and role in interaction.user.roles:
                    user_game_roles.append(game_data)

        if not user_game_roles:
            embed = discord.Embed(
                title="🎮 Your Game Roles",
                description="You don't have any game roles yet!\nUse the Search Games button to add some!",
                color=COLORS['info']
            )
            embed.set_footer(text="Auto-deletes in 20s")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
            return

        embed = discord.Embed(
            title="🎮 Your Game Roles",
            description=f"You have {len(user_game_roles)} game roles:",
            color=COLORS['primary']
        )

        for game_data in user_game_roles[:10]:  # Limit to 10
            role = interaction.guild.get_role(game_data['role_id'])
            member_count = len(role.members) if role else 0
            embed.add_field(
                name=game_data['name'],
                value=f"👥 {member_count} members",
                inline=True
            )

        embed.set_footer(text="Use the LFG button to find other players! • Auto-deletes in 30s")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)

class GameSearchModal(discord.ui.Modal, title='Search for Games'):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    search_term = discord.ui.TextInput(
        label='Game Name',
        placeholder='Enter game name (e.g., Rocket League, Valorant)',
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        query = self.search_term.value.strip()
        
        if len(query) < 2:
            await interaction.response.send_message("❌ Search query must be at least 2 characters!", ephemeral=True, delete_after=10)
            return

        # Defer the response since search might take time
        await interaction.response.defer(ephemeral=True)

        # Search for games
        games = await self.cog.search_games(query)
        
        if not games:
            embed = discord.Embed(
                title="❌ No Games Found",
                description=f"No games found for: **{query}**\nTry a different search term!",
                color=COLORS['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True, delete_after=20)
            return

        # Create embed with results
        embed = discord.Embed(
            title="🎮 Game Search Results",
            description=f"Found {len(games)} games for: **{query}**\n🔒 Only you can select from this list:",
            color=COLORS['primary']
        )

        # Create select menu options
        options = []
        for game in games[:10]:  # Limit to 10 results
            # Truncate long names
            name = game['name']
            if len(name) > 50:
                name = name[:47] + "..."
            
            # Get platforms
            platforms = []
            if game.get('platforms'):
                platforms = [p['platform']['name'] for p in game['platforms'][:3]]
            platform_text = f" ({', '.join(platforms)})" if platforms else ""
            
            description = f"Rating: {game.get('rating', 'N/A')}/5{platform_text}"
            if len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=name,
                description=description,
                value=str(game['id']),
                emoji="🎮"
            ))

        # Create view with select menu
        view = GameSearchView(games, interaction.user.id)
        view.game_select.options = options

        # Send the followup message (followup doesn't support delete_after)
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        # Schedule deletion using our persistent system
        self.cog.schedule_message_deletion(message, 60)

class LFGSelectView(discord.ui.View):
    def __init__(self, user_games, user_id, cog):
        super().__init__(timeout=60)
        self.user_games = user_games
        self.user_id = user_id
        self.cog = cog

    @discord.ui.select(
        placeholder="Choose a game to look for group...",
        min_values=1,
        max_values=1
    )
    async def game_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your LFG selection!", ephemeral=True, delete_after=10)
            return

        selected_game_name = select.values[0]
        selected_game = next(game for game in self.user_games if game['name'] == selected_game_name)
        
        # Get the role
        role = interaction.guild.get_role(selected_game['role_id'])
        if not role:
            await interaction.response.send_message(f"❌ Role for **{selected_game['name']}** no longer exists!", ephemeral=True, delete_after=15)
            return

        # Determine target channel for LFG posting
        lfg_channel_id = self.cog.get_lfg_channel(interaction.guild.id)
        target_channel = interaction.channel  # Default to current channel
        
        if lfg_channel_id:
            lfg_channel = interaction.guild.get_channel(lfg_channel_id)
            if lfg_channel:
                target_channel = lfg_channel
            else:
                # LFG channel was deleted, use current channel
                target_channel = interaction.channel

        # Create LFG embed
        embed = discord.Embed(
            title="🔍 Looking for Group!",
            description=f"{interaction.user.mention} is looking for players!",
            color=COLORS['primary']
        )
        embed.add_field(name="Game", value=selected_game['name'], inline=True)
        embed.add_field(name="Players with Role", value=f"{len(role.members)}", inline=True)
        embed.add_field(name="React to Join!", value="👋 React to show interest!", inline=False)
        
        if selected_game.get('image'):
            embed.set_thumbnail(url=selected_game['image'])
        
        embed.set_footer(text=f"LFG by {interaction.user.display_name}")

        # Send the LFG message with role ping
        content = f"🎮 **LFG Alert!** {role.mention}"
        message = await target_channel.send(content=content, embed=embed)
        
        # Add reaction for people to join
        await message.add_reaction("👋")
        
        # Respond to the interaction
        if target_channel != interaction.channel:
            await interaction.response.send_message(f"✅ LFG posted in {target_channel.mention}!", ephemeral=True, delete_after=10)
        else:
            await interaction.response.send_message("✅ LFG posted!", ephemeral=True, delete_after=5)

class GroupFinder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/game_roles.json'
        self.game_roles = self.load_game_roles()
        self.pending_deletions_file = 'data/pending_deletions.json'
        self.pending_deletions = self.load_pending_deletions()
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        # Schedule startup tasks to run after bot is ready
        asyncio.create_task(self.startup_tasks())

    def load_game_roles(self):
        """Load game roles from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_game_roles(self):
        """Save game roles to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.game_roles, f, indent=2)
    
    def load_pending_deletions(self):
        """Load pending deletions from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.pending_deletions_file):
            try:
                with open(self.pending_deletions_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_pending_deletions(self):
        """Save pending deletions to JSON file"""
        with open(self.pending_deletions_file, 'w') as f:
            json.dump(self.pending_deletions, f, indent=2)
    
    def schedule_message_deletion(self, message, delay):
        """Schedule a message for deletion with persistence"""
        # Check if this is an ephemeral message (no guild context)
        if not hasattr(message, 'guild') or message.guild is None:
            # For ephemeral messages, just use regular auto-deletion
            # Ephemeral messages are automatically cleaned up by Discord
            asyncio.create_task(self.auto_delete_search(message, delay))
            return
        
        # For regular messages, use persistent deletion system
        import time
        deletion_time = time.time() + delay
        
        key = f"{message.guild.id}_{message.channel.id}_{message.id}"
        self.pending_deletions[key] = {
            'guild_id': message.guild.id,
            'channel_id': message.channel.id,
            'message_id': message.id,
            'deletion_time': deletion_time
        }
        self.save_pending_deletions()
        
        # Also create the async task for immediate handling
        asyncio.create_task(self.auto_delete_search(message, delay))
    
    async def cleanup_pending_deletions(self):
        """Clean up messages that should have been deleted during bot downtime"""
        await self.bot.wait_until_ready()
        import time
        
        current_time = time.time()
        to_delete = []
        
        for key, deletion_data in self.pending_deletions.items():
            if deletion_data['deletion_time'] <= current_time:
                # This message should have been deleted
                try:
                    guild = self.bot.get_guild(deletion_data['guild_id'])
                    if guild:
                        channel = guild.get_channel(deletion_data['channel_id'])
                        if channel:
                            message = await channel.fetch_message(deletion_data['message_id'])
                            await message.delete()
                except:
                    pass  # Message might already be deleted or channel/guild gone
                
                to_delete.append(key)
        
        # Remove processed deletions
        for key in to_delete:
            del self.pending_deletions[key]
        
        if to_delete:
            self.save_pending_deletions()
        
        # Start continuous cleanup task
        asyncio.create_task(self.continuous_cleanup())

    def save_game_role(self, guild_id, game_data, role_id):
        """Save a game role mapping"""
        guild_key = str(guild_id)
        if guild_key not in self.game_roles:
            self.game_roles[guild_key] = {
                'games': {},
                'lfg_channel': None
            }
        
        if 'games' not in self.game_roles[guild_key]:
            self.game_roles[guild_key]['games'] = {}
        
        self.game_roles[guild_key]['games'][game_data['name'].lower()] = {
            'name': game_data['name'],
            'role_id': role_id,
            'game_id': game_data['id'],
            'image': game_data.get('background_image', ''),
            'created_at': datetime.now().isoformat()
        }
        self.save_game_roles()

    def get_lfg_channel(self, guild_id):
        """Get the LFG channel for a guild"""
        guild_key = str(guild_id)
        if guild_key in self.game_roles and 'lfg_channel' in self.game_roles[guild_key]:
            return self.game_roles[guild_key]['lfg_channel']
        return None

    def set_lfg_channel(self, guild_id, channel_id):
        """Set the LFG channel for a guild"""
        guild_key = str(guild_id)
        if guild_key not in self.game_roles:
            self.game_roles[guild_key] = {
                'games': {},
                'lfg_channel': channel_id
            }
        else:
            self.game_roles[guild_key]['lfg_channel'] = channel_id
        self.save_game_roles()

    async def search_games(self, query):
        """Search for games using RAWG API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.rawg.io/api/games"
                from config import RAWG_API_KEY
                
                params = {
                    'search': f'"{query}"',  # Use quotes for exact phrase matching
                    'search_precise': 'true',
                    'page_size': 15,  # Get more results to filter better
                    'ordering': '-rating'
                }
                
                # Add API key if available
                if RAWG_API_KEY:
                    params['key'] = RAWG_API_KEY
                
                # Add timeout and proper headers
                headers = {
                    'User-Agent': 'Discord Bot Game Search'
                }
                
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.get(url, params=params, headers=headers, timeout=timeout) as response:
                    print(f"API Response Status: {response.status}")  # Debug
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        print(f"Found {len(results)} games from API")  # Debug
                        
                        # Filter and rank results for better matching
                        filtered_results = self.filter_and_rank_results(results, query)
                        return filtered_results[:10]  # Return top 10 matches
                    elif response.status == 401:
                        print("API Key required or invalid - using fallback")  # Debug
                        return self.get_mock_games(query)
                    else:
                        print(f"API Error: {response.status}")  # Debug
                        return self.get_mock_games(query)
        except Exception as e:
            print(f"Search error: {e}")  # Debug
            # Fallback to mock data
            return self.get_mock_games(query)

    def get_mock_games(self, query):
        """Fallback mock games for testing when API fails"""
        mock_games = [
            {'id': 1, 'name': 'Rocket League', 'rating': 4.5, 'background_image': 'https://media.rawg.io/media/games/8cc/8cce7c0e99dcc43d66c8efd42f9d03e3.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}]},
            {'id': 2, 'name': 'Valorant', 'rating': 4.2, 'background_image': 'https://media.rawg.io/media/games/737/737ea5662211d2e0bbd6f5989189e4f1.jpg', 'platforms': [{'platform': {'name': 'PC'}}]},
            {'id': 3, 'name': 'Apex Legends', 'rating': 4.3, 'background_image': 'https://media.rawg.io/media/games/b72/b7233d5d5b1e75e86bb860ccc7aeca85.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}, {'platform': {'name': 'Xbox'}}]},
            {'id': 4, 'name': 'Counter-Strike 2', 'rating': 4.1, 'background_image': 'https://media.rawg.io/media/games/736/73619bd336c894d6941d926bfd563946.jpg', 'platforms': [{'platform': {'name': 'PC'}}]},
            {'id': 5, 'name': 'League of Legends', 'rating': 4.0, 'background_image': 'https://media.rawg.io/media/games/78d/78dfae12fb8c5b16cd78648553071e0a.jpg', 'platforms': [{'platform': {'name': 'PC'}}]},
            {'id': 6, 'name': 'Fortnite', 'rating': 3.8, 'background_image': 'https://media.rawg.io/media/games/1f4/1f47a270b8f241e4676b14d39ec620f7.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}, {'platform': {'name': 'Xbox'}}, {'platform': {'name': 'Nintendo Switch'}}]},
            {'id': 7, 'name': 'Overwatch 2', 'rating': 3.9, 'background_image': 'https://media.rawg.io/media/games/34b/34b1f1850a1c06fd971bc6ab3ac0ce0e.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}, {'platform': {'name': 'Xbox'}}, {'platform': {'name': 'Nintendo Switch'}}]},
            {'id': 8, 'name': 'Call of Duty: Modern Warfare', 'rating': 4.0, 'background_image': 'https://media.rawg.io/media/games/120/1201a40e4364557b124392ee50317b99.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}, {'platform': {'name': 'Xbox'}}]},
            {'id': 9, 'name': 'Minecraft', 'rating': 4.4, 'background_image': 'https://media.rawg.io/media/games/b4e/b4e4c73d5aa4ec66bbf75375c4847a2b.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}, {'platform': {'name': 'Xbox'}}, {'platform': {'name': 'Nintendo Switch'}}]},
            {'id': 10, 'name': 'Among Us', 'rating': 3.7, 'background_image': 'https://media.rawg.io/media/games/e74/e74458058b35e01c1ae3feeb39a3f724.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'Mobile'}}]},
            {'id': 11, 'name': 'Fall Guys', 'rating': 3.6, 'background_image': 'https://media.rawg.io/media/games/5eb/5eb49eb2fa0738fdb5bacea557b1bc57.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}, {'platform': {'name': 'Xbox'}}, {'platform': {'name': 'Nintendo Switch'}}]},
            {'id': 12, 'name': 'Dota 2', 'rating': 4.1, 'background_image': 'https://media.rawg.io/media/games/6fc/6fcf4cd3b17c288821388e6085bb0fc9.jpg', 'platforms': [{'platform': {'name': 'PC'}}]},
            {'id': 13, 'name': 'World of Warcraft', 'rating': 4.2, 'background_image': 'https://media.rawg.io/media/games/c4b/c4b0cab189e73432de3a250d8cf1c84e.jpg', 'platforms': [{'platform': {'name': 'PC'}}]},
            {'id': 14, 'name': 'Destiny 2', 'rating': 4.0, 'background_image': 'https://media.rawg.io/media/games/34b/34b1f1850a1c06fd971bc6ab3ac0ce0e.jpg', 'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'PlayStation'}}, {'platform': {'name': 'Xbox'}}]},
            {'id': 15, 'name': 'Valheim', 'rating': 4.3, 'background_image': 'https://media.rawg.io/media/games/b29/b294fdd866dcdb643e7bab370a552855.jpg', 'platforms': [{'platform': {'name': 'PC'}}]}
        ]
        
        # Use the same filtering logic for mock games
        filtered_results = self.filter_and_rank_results(mock_games, query)
        
        # If no good matches, return top rated mock games
        if not filtered_results:
            # Sort by rating and return top games
            sorted_games = sorted(mock_games, key=lambda x: x.get('rating', 0), reverse=True)
            return sorted_games[:10]
        
        return filtered_results[:10]

    def filter_and_rank_results(self, results, query):
        """Filter and rank search results for better matching"""
        if not results:
            return []
        
        query_lower = query.lower().strip()
        scored_results = []
        
        for game in results:
            game_name = game.get('name', '').lower()
            score = 0
            
            # Exact match gets highest score
            if game_name == query_lower:
                score = 100
            # Starts with query gets high score
            elif game_name.startswith(query_lower):
                score = 90
            # Contains exact phrase gets good score
            elif query_lower in game_name:
                score = 80
            # Contains all words gets medium score
            elif self.contains_all_words(game_name, query_lower):
                score = 60
            # Contains some words gets low score
            elif self.contains_some_words(game_name, query_lower):
                score = 30
            else:
                # Skip games that don't match well
                continue
            
            # Boost score for higher rated games
            rating = game.get('rating', 0)
            if rating:
                score += min(rating * 2, 10)  # Add up to 10 points for rating
            
            # Boost score for more popular games (more ratings count)
            ratings_count = game.get('ratings_count', 0)
            if ratings_count > 1000:
                score += 5
            
            scored_results.append((score, game))
        
        # Sort by score (highest first) and return games
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [game for score, game in scored_results]

    def contains_all_words(self, text, query):
        """Check if text contains all words from query"""
        query_words = query.split()
        return all(word in text for word in query_words)

    def contains_some_words(self, text, query):
        """Check if text contains some words from query"""
        query_words = query.split()
        if len(query_words) <= 1:
            return False
        return any(word in text for word in query_words)

    @commands.command(name='searchgame', aliases=['sg'])
    async def search_game(self, ctx, *, query: str):
        """Search for games and add their roles! Usage: !searchgame <game name>"""
        if len(query) < 2:
            await ctx.send("❌ Search query must be at least 2 characters!")
            return

        # Show searching message
        searching_embed = discord.Embed(
            title="🔍 Searching Games...",
            description=f"Looking for games matching: **{query}**",
            color=COLORS['info']
        )
        message = await ctx.send(embed=searching_embed)

        # Search for games
        games = await self.search_games(query)
        
        if not games:
            embed = discord.Embed(
                title="❌ No Games Found",
                description=f"No games found for: **{query}**\nTry a different search term!",
                color=COLORS['error']
            )
            await message.edit(embed=embed)
            return

        # Create embed with results
        embed = discord.Embed(
            title="🎮 Game Search Results",
            description=f"Found {len(games)} games for: **{query}**\n🔒 Only you can select from this list:",
            color=COLORS['primary']
        )

        # Create select menu options
        options = []
        for game in games[:10]:  # Limit to 10 results
            # Truncate long names
            name = game['name']
            if len(name) > 50:
                name = name[:47] + "..."
            
            # Get platforms
            platforms = []
            if game.get('platforms'):
                platforms = [p['platform']['name'] for p in game['platforms'][:3]]
            platform_text = f" ({', '.join(platforms)})" if platforms else ""
            
            description = f"Rating: {game.get('rating', 'N/A')}/5{platform_text}"
            if len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=name,
                description=description,
                value=str(game['id']),
                emoji="🎮"
            ))

        # Create view with select menu
        view = GameSearchView(games, ctx.author.id)
        view.game_select.options = options

        # Delete the searching message
        await message.delete()
        
        # Send search results that will auto-delete
        embed.set_footer(text=f"🔒 Only {ctx.author.display_name} can select • Auto-deletes in 60s")
        response_msg = await ctx.send(f"{ctx.author.mention}", embed=embed, view=view)
        
        # Schedule auto-deletion with persistence
        self.schedule_message_deletion(response_msg, 60)

    @commands.command(name='lfg')
    async def looking_for_group(self, ctx, *, game_name: str = None):
        """Look for group! Usage: !lfg [game name] or just !lfg to select from dropdown"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.game_roles or 'games' not in self.game_roles[guild_key]:
            await ctx.send("❌ No game roles found! Use `!searchgame <game>` to create some first!")
            return

        # Get user's game roles
        user_game_roles = []
        for game_name_key, game_data in self.game_roles[guild_key]['games'].items():
            role = ctx.guild.get_role(game_data['role_id'])
            if role and role in ctx.author.roles:
                user_game_roles.append(game_data)

        if not user_game_roles:
            embed = discord.Embed(
                title="❌ No Game Roles",
                description="You don't have any game roles to LFG with!",
                color=COLORS['warning']
            )
            embed.add_field(name="Get Game Roles", value="Use `!searchgame <game>` to add some!", inline=False)
            await ctx.send(embed=embed)
            return

        # If no game name provided, show dropdown selection
        if not game_name:
            embed = discord.Embed(
                title="🎮 Select Game for LFG",
                description=f"Choose from your {len(user_game_roles)} game roles:",
                color=COLORS['primary']
            )
            embed.set_footer(text=f"🔒 Only {ctx.author.display_name} can select • Auto-deletes in 60s")

            # Create select menu options
            options = []
            for game_data in user_game_roles[:25]:  # Discord limit is 25 options
                role = ctx.guild.get_role(game_data['role_id'])
                member_count = len(role.members) if role else 0
                
                options.append(discord.SelectOption(
                    label=game_data['name'],
                    description=f"👥 {member_count} members with this role",
                    value=game_data['name'],
                    emoji="🎮"
                ))

            view = LFGSelectView(user_game_roles, ctx.author.id, self)
            view.game_select.options = options

            message = await ctx.send(f"{ctx.author.mention}", embed=embed, view=view)
            
            # Schedule auto-deletion with persistence
            self.schedule_message_deletion(message, 60)
            return

        # Original text-based LFG (kept for backwards compatibility)
        # Check if LFG channel is set and if we're in the right channel
        lfg_channel_id = self.get_lfg_channel(ctx.guild.id)
        if lfg_channel_id and ctx.channel.id != lfg_channel_id:
            lfg_channel = ctx.guild.get_channel(lfg_channel_id)
            if lfg_channel:
                embed = discord.Embed(
                    title="❌ Wrong Channel",
                    description=f"LFG commands can only be used in {lfg_channel.mention}!",
                    color=COLORS['warning']
                )
                await ctx.send(embed=embed)
                return

        # Find matching game role
        game_name_lower = game_name.lower()
        matching_games = []
        
        for stored_name, game_data in self.game_roles[guild_key]['games'].items():
            if game_name_lower in stored_name or stored_name in game_name_lower:
                matching_games.append((stored_name, game_data))

        if not matching_games:
            # Show available games
            available_games = list(self.game_roles[guild_key]['games'].keys())
            embed = discord.Embed(
                title="❌ Game Not Found",
                description=f"No role found for: **{game_name}**",
                color=COLORS['error']
            )
            if available_games:
                games_list = '\n'.join([f"• {game.title()}" for game in available_games[:10]])
                embed.add_field(name="Available Games", value=games_list, inline=False)
            embed.add_field(name="💡 Tip", value="Use `!lfg` (without game name) for easy selection!", inline=False)
            embed.set_footer(text="Use !searchgame <name> to add new games!")
            await ctx.send(embed=embed)
            return

        # Use the best match (first one)
        game_data = matching_games[0][1]
        role = ctx.guild.get_role(game_data['role_id'])
        
        if not role:
            await ctx.send(f"❌ Role for **{game_data['name']}** no longer exists! Try searching for it again.")
            return

        # Check if user has the role
        if role not in ctx.author.roles:
            embed = discord.Embed(
                title="❌ Role Required",
                description=f"You need the **{game_data['name']}** role to use LFG for this game!",
                color=COLORS['warning']
            )
            embed.add_field(name="Get the Role", value=f"Use `!searchgame {game_data['name']}` to add it!", inline=False)
            await ctx.send(embed=embed)
            return

        # Create LFG embed
        embed = discord.Embed(
            title="🔍 Looking for Group!",
            description=f"{ctx.author.mention} is looking for players!",
            color=COLORS['primary']
        )
        embed.add_field(name="Game", value=game_data['name'], inline=True)
        embed.add_field(name="Players with Role", value=f"{len(role.members)}", inline=True)
        embed.add_field(name="React to Join!", value="👋 React to show interest!", inline=False)
        
        if game_data.get('image'):
            embed.set_thumbnail(url=game_data['image'])
        
        embed.set_footer(text=f"LFG by {ctx.author.display_name}")

        # Determine where to send the message
        target_channel = ctx.channel
        if lfg_channel_id:
            lfg_channel = ctx.guild.get_channel(lfg_channel_id)
            if lfg_channel:
                target_channel = lfg_channel

        # Send the LFG message with role ping
        content = f"🎮 **LFG Alert!** {role.mention}"
        message = await target_channel.send(content=content, embed=embed)
        
        # Add reaction for people to join
        await message.add_reaction("👋")
        
        # If we sent to a different channel, let the user know
        if target_channel != ctx.channel:
            await ctx.send(f"✅ LFG posted in {target_channel.mention}!")

    async def startup_tasks(self):
        """Run startup tasks after bot is ready"""
        await self.bot.wait_until_ready()
        
        # Add a small delay to ensure Discord is fully ready
        await asyncio.sleep(2)
        
        # Start cleanup task for pending deletions
        asyncio.create_task(self.cleanup_pending_deletions())
        
        # Re-register persistent views for LFG panels
        await self.restore_lfg_panels()

    async def restore_lfg_panels(self):
        """Restore LFG panel views after bot restart"""
        
        for guild_key, guild_data in self.game_roles.items():
            if 'panel_message_id' in guild_data:
                try:
                    guild_id = int(guild_key)
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        # Find the panel message in all channels
                        panel_message = None
                        for channel in guild.text_channels:
                            try:
                                panel_message = await channel.fetch_message(guild_data['panel_message_id'])
                                break
                            except discord.NotFound:
                                continue
                            except discord.Forbidden:
                                continue
                        
                        if panel_message:
                            # Re-attach the view to the message
                            view = LFGPanelView(self)
                            print(f"DEBUG: Creating view for guild {guild_id}, message {guild_data['panel_message_id']}")
                            print(f"DEBUG: View timeout: {view.timeout}, View children: {len(view.children)}")
                            
                            try:
                                # Try to edit the message to reattach the view
                                await panel_message.edit(view=view)
                                print(f"✅ Restored LFG panel for guild {guild_id} via message edit")
                            except Exception as edit_error:
                                print(f"DEBUG: Edit failed: {edit_error}")
                                try:
                                    # Fallback to add_view method
                                    self.bot.add_view(view, message_id=guild_data['panel_message_id'])
                                    print(f"✅ Restored LFG panel for guild {guild_id} via add_view")
                                except Exception as add_error:
                                    print(f"❌ Both methods failed for guild {guild_id}: {add_error}")
                        else:
                            # Panel message was deleted, clean up the reference
                            del self.game_roles[guild_key]['panel_message_id']
                            self.save_game_roles()
                            print(f"Cleaned up deleted LFG panel reference for guild {guild_id}")
                except Exception as e:
                    print(f"Error restoring LFG panel for guild {guild_key}: {e}")

    async def continuous_cleanup(self):
        """Continuously check for messages to delete"""
        import time
        
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                current_time = time.time()
                to_delete = []
                
                for key, deletion_data in self.pending_deletions.items():
                    if deletion_data['deletion_time'] <= current_time:
                        try:
                            guild = self.bot.get_guild(deletion_data['guild_id'])
                            if guild:
                                channel = guild.get_channel(deletion_data['channel_id'])
                                if channel:
                                    message = await channel.fetch_message(deletion_data['message_id'])
                                    await message.delete()
                        except:
                            pass  # Message might already be deleted
                        
                        to_delete.append(key)
                
                # Also clean up very old entries (older than 1 hour) that might be stuck
                one_hour_ago = current_time - 3600
                for key, deletion_data in self.pending_deletions.items():
                    if deletion_data['deletion_time'] < one_hour_ago:
                        to_delete.append(key)
                
                # Remove processed deletions
                for key in to_delete:
                    if key in self.pending_deletions:
                        del self.pending_deletions[key]
                
                if to_delete:
                    self.save_pending_deletions()
                    
            except Exception as e:
                print(f"Error in continuous cleanup: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def auto_delete_search(self, message, delay):
        """Auto-delete search message after delay"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
            
            # Remove from pending deletions if successful
            key = f"{message.guild.id}_{message.channel.id}_{message.id}"
            if key in self.pending_deletions:
                del self.pending_deletions[key]
                self.save_pending_deletions()
        except:
            pass  # Message might already be deleted

    @commands.command(name='mygames')
    async def my_games(self, ctx):
        """Show all your game roles"""
        user_game_roles = []
        guild_key = str(ctx.guild.id)
        
        if guild_key in self.game_roles and 'games' in self.game_roles[guild_key]:
            for game_name, game_data in self.game_roles[guild_key]['games'].items():
                role = ctx.guild.get_role(game_data['role_id'])
                if role and role in ctx.author.roles:
                    user_game_roles.append(game_data)

        if not user_game_roles:
            embed = discord.Embed(
                title="🎮 Your Game Roles",
                description="You don't have any game roles yet!\nUse `!searchgame <game>` to add some!",
                color=COLORS['info']
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🎮 Your Game Roles",
            description=f"You have {len(user_game_roles)} game roles:",
            color=COLORS['primary']
        )

        for game_data in user_game_roles[:10]:  # Limit to 10
            role = ctx.guild.get_role(game_data['role_id'])
            member_count = len(role.members) if role else 0
            embed.add_field(
                name=game_data['name'],
                value=f"👥 {member_count} members\n🔔 `!lfg {game_data['name']}`",
                inline=True
            )

        embed.set_footer(text="Use !lfg <game> to find other players!")
        await ctx.send(embed=embed)

    @commands.command(name='removegame', aliases=['rg'])
    async def remove_game(self, ctx, *, game_name: str):
        """Remove a game role from yourself"""
        guild_key = str(ctx.guild.id)
        
        if guild_key not in self.game_roles or 'games' not in self.game_roles[guild_key]:
            await ctx.send("❌ No game roles found!")
            return

        # Find matching game role
        game_name_lower = game_name.lower()
        matching_game = None
        
        for stored_name, game_data in self.game_roles[guild_key]['games'].items():
            if game_name_lower in stored_name or stored_name in game_name_lower:
                matching_game = game_data
                break

        if not matching_game:
            await ctx.send(f"❌ No role found for: **{game_name}**")
            return

        role = ctx.guild.get_role(matching_game['role_id'])
        if not role:
            await ctx.send(f"❌ Role for **{matching_game['name']}** no longer exists!")
            return

        if role not in ctx.author.roles:
            await ctx.send(f"❌ You don't have the **{matching_game['name']}** role!")
            return

        try:
            await ctx.author.remove_roles(role)
            embed = discord.Embed(
                title="✅ Game Role Removed",
                description=f"Removed the **{matching_game['name']}** role!",
                color=COLORS['success']
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to remove roles!")

    @commands.command(name='setlfgchannel')
    @commands.has_permissions(manage_channels=True)
    async def set_lfg_channel_command(self, ctx, channel: discord.TextChannel = None):
        """Set the LFG channel for this server (Manage Channels permission required)"""
        if channel is None:
            channel = ctx.channel
        
        self.set_lfg_channel(ctx.guild.id, channel.id)
        
        embed = discord.Embed(
            title="✅ LFG Channel Set",
            description=f"LFG commands will now be restricted to {channel.mention}",
            color=COLORS['success']
        )
        embed.add_field(
            name="📋 Info",
            value="• Users can still search for games anywhere\n• Only `!lfg` commands are restricted\n• LFG pings will be sent to this channel",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='removelfgchannel')
    @commands.has_permissions(manage_channels=True)
    async def remove_lfg_channel(self, ctx):
        """Remove LFG channel restriction (Manage Channels permission required)"""
        guild_key = str(ctx.guild.id)
        
        if guild_key in self.game_roles:
            self.game_roles[guild_key]['lfg_channel'] = None
            self.save_game_roles()
        
        embed = discord.Embed(
            title="✅ LFG Channel Restriction Removed",
            description="LFG commands can now be used in any channel",
            color=COLORS['success']
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='lfginfo')
    async def lfg_info(self, ctx):
        """Show LFG system information and settings"""
        guild_key = str(ctx.guild.id)
        
        embed = discord.Embed(
            title="🎮 LFG System Info",
            color=COLORS['info']
        )
        
        # LFG Channel info
        lfg_channel_id = self.get_lfg_channel(ctx.guild.id)
        if lfg_channel_id:
            lfg_channel = ctx.guild.get_channel(lfg_channel_id)
            if lfg_channel:
                embed.add_field(
                    name="📍 LFG Channel",
                    value=f"{lfg_channel.mention}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📍 LFG Channel",
                    value="❌ Channel deleted",
                    inline=True
                )
        else:
            embed.add_field(
                name="📍 LFG Channel",
                value="Any channel",
                inline=True
            )
        
        # Game count
        game_count = 0
        if guild_key in self.game_roles and 'games' in self.game_roles[guild_key]:
            game_count = len(self.game_roles[guild_key]['games'])
        
        embed.add_field(
            name="🎮 Games Available",
            value=f"{game_count} games",
            inline=True
        )
        
        # Commands info
        embed.add_field(
            name="📋 Commands",
            value="• `!searchgame <name>` - Find & add games\n• `!lfg <game>` - Look for group\n• `!mygames` - View your games\n• `!removegame <name>` - Remove game role",
            inline=False
        )
        
        # Admin commands
        if ctx.author.guild_permissions.manage_channels:
            embed.add_field(
                name="⚙️ Admin Commands",
                value="• `!setlfgchannel [#channel]` - Set LFG channel\n• `!removelfgchannel` - Remove restriction",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @set_lfg_channel_command.error
    @remove_lfg_channel.error
    async def lfg_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Channels' permission to use this command!")

    @commands.command(name='setuplfgpanel')
    @commands.has_permissions(manage_channels=True)
    async def setup_lfg_panel(self, ctx):
        """Set up the persistent LFG control panel (Manage Channels permission required)"""
        embed = discord.Embed(
            title="🎮 LFG Control Panel",
            description="Welcome to the Looking for Group system! Use the buttons below:",
            color=COLORS['primary']
        )
        
        embed.add_field(
            name="🔍 Search Games",
            value="Find and add new game roles to your profile",
            inline=False
        )
        
        embed.add_field(
            name="📢 Looking for Group",
            value="Ping other players for your games",
            inline=False
        )
        
        embed.add_field(
            name="📋 My Games",
            value="View all your current game roles",
            inline=False
        )
        
        embed.set_footer(text="🔄 This panel stays active • Responses auto-delete after 60s")
        
        view = LFGPanelView(self)
        message = await ctx.send(embed=embed, view=view)
        
        # Don't automatically set this as LFG channel - let admin choose
        
        # Save the panel message ID for potential future use
        guild_key = str(ctx.guild.id)
        if guild_key not in self.game_roles:
            self.game_roles[guild_key] = {'games': {}, 'lfg_channel': None}
        
        self.game_roles[guild_key]['panel_message_id'] = message.id
        self.save_game_roles()
        
        # Send confirmation
        confirm_embed = discord.Embed(
            title="✅ LFG Panel Created",
            description=f"LFG control panel is now active in {ctx.channel.mention}",
            color=COLORS['success']
        )
        confirm_embed.add_field(
            name="📋 Features",
            value="• Persistent control panel\n• Auto-deleting responses\n• Clean channel management\n• Easy game search & LFG",
            inline=False
        )
        confirm_embed.add_field(
            name="⚙️ Next Steps",
            value=f"• Use `!setlfgchannel #channel` to set where LFG pings go\n• Or LFG pings will post in {ctx.channel.mention} by default",
            inline=False
        )
        
        confirm_msg = await ctx.send(embed=confirm_embed)
        
        # Schedule auto-deletion with persistence
        self.schedule_message_deletion(confirm_msg, 10)

    @setup_lfg_panel.error
    async def setup_lfg_panel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need 'Manage Channels' permission to set up the LFG panel!")

async def setup(bot):
    await bot.add_cog(GroupFinder(bot))