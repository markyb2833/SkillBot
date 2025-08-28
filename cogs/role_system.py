import discord
from discord.ext import commands
import json
import os
from datetime import datetime
from config import COLORS

class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, emoji: str, style: discord.ButtonStyle, custom_id: str):
        super().__init__(
            label=label,
            emoji=emoji,
            style=style,
            custom_id=custom_id
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        # Get the role
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("❌ This role no longer exists!", ephemeral=True, delete_after=10)
            return

        # Check if user already has the role
        if role in interaction.user.roles:
            try:
                await interaction.user.remove_roles(role)
                embed = discord.Embed(
                    title="✅ Role Removed!",
                    description=f"**{role.name}** has been removed from you.",
                    color=COLORS['warning']
                )
                embed.set_footer(text="Auto-deletes in 10s")
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to remove roles!", ephemeral=True, delete_after=10)
            except discord.HTTPException:
                await interaction.response.send_message("❌ Failed to remove role. Please try again.", ephemeral=True, delete_after=10)
        else:
            try:
                await interaction.user.add_roles(role)
                embed = discord.Embed(
                    title="✅ Role Added!",
                    description=f"**{role.name}** has been added to you.",
                    color=COLORS['success']
                )
                embed.set_footer(text="Auto-deletes in 10s")
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to assign roles!", ephemeral=True, delete_after=10)
            except discord.HTTPException:
                await interaction.response.send_message("❌ Failed to assign role. Please try again.", ephemeral=True, delete_after=10)

class RolePanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog
        self.update_buttons()

    def update_buttons(self):
        """Update the view with current role buttons"""
        # Clear existing buttons
        self.clear_items()
        
        # Add role buttons
        guild_id = str(self.cog.bot.guilds[0].id) if self.cog.bot.guilds else None
        if guild_id and guild_id in self.cog.role_panels:
            for role_data in self.cog.role_panels[guild_id]:
                button = RoleButton(
                    role_id=role_data['role_id'],
                    label=role_data['label'],
                    emoji=role_data['emoji'],
                    style=discord.ButtonStyle.primary,
                    custom_id=f"role_{role_data['role_id']}"
                )
                self.add_item(button)

class AdminRoleView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog

    @discord.ui.button(label='➕ Add Role', style=discord.ButtonStyle.success, emoji='➕', custom_id='admin_add_role')
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddRoleModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='✏️ Edit Role', style=discord.ButtonStyle.primary, emoji='✏️', custom_id='admin_edit_role')
    async def edit_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditRoleModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='🗑️ Remove Role', style=discord.ButtonStyle.danger, emoji='🗑️', custom_id='admin_remove_role')
    async def remove_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RemoveRoleModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='📋 List Roles', style=discord.ButtonStyle.secondary, emoji='📋', custom_id='admin_list_roles')
    async def list_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.list_roles_command(interaction)

    @discord.ui.button(label='🔄 Refresh Panel', style=discord.ButtonStyle.secondary, emoji='🔄', custom_id='admin_refresh_role_panel')
    async def refresh_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛠️ Role Management Panel",
            description="Use the buttons below to manage role assignments:",
            color=COLORS['primary']
        )
        embed.add_field(
            name="➕ Add Role", 
            value="Add a new role to the assignment panel", 
            inline=False
        )
        embed.add_field(
            name="✏️ Edit Role", 
            value="Modify an existing role's display settings", 
            inline=False
        )
        embed.add_field(
            name="🗑️ Remove Role", 
            value="Remove a role from the assignment panel", 
            inline=False
        )
        embed.add_field(
            name="📋 List Roles", 
            value="View all configured roles", 
            inline=False
        )
        embed.set_footer(text="Admin Panel • Only visible to administrators")
        
        await interaction.response.edit_message(embed=embed, view=self)

class AddRoleModal(discord.ui.Modal, title="Add Role to Panel"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    role_id = discord.ui.TextInput(
        label="Role ID",
        placeholder="Enter the role ID (right-click role → Copy ID)",
        required=True,
        min_length=17,
        max_length=20
    )
    
    label = discord.ui.TextInput(
        label="Button Label",
        placeholder="Enter the text to display on the button",
        required=True,
        max_length=80
    )
    
    emoji = discord.ui.TextInput(
        label="Emoji",
        placeholder="Enter an emoji (e.g., 🎮, 🎯, 🏆)",
        required=False,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_id = int(self.role_id.value)
            role = interaction.guild.get_role(role_id)
            
            if not role:
                await interaction.response.send_message("❌ Role not found! Please check the role ID.", ephemeral=True, delete_after=15)
                return

            # Add role to panel
            success = await self.cog.add_role_to_panel(interaction.guild.id, role_id, self.label.value, self.emoji.value or "")
            
            if success:
                embed = discord.Embed(
                    title="✅ Role Added!",
                    description=f"**{role.name}** has been added to the role panel.",
                    color=COLORS['success']
                )
                embed.add_field(name="Label", value=self.label.value, inline=True)
                if self.emoji.value:
                    embed.add_field(name="Emoji", value=self.emoji.value, inline=True)
                embed.set_footer(text="Auto-deletes in 15s")
                
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
                
                # Refresh the role panel
                await self.cog.refresh_role_panel(interaction.guild.id)
            else:
                await interaction.response.send_message("❌ Failed to add role. It might already exist in the panel.", ephemeral=True, delete_after=15)
                
        except ValueError:
            await interaction.response.send_message("❌ Invalid role ID! Please enter a valid number.", ephemeral=True, delete_after=15)

class EditRoleModal(discord.ui.Modal, title="Edit Role in Panel"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    role_id = discord.ui.TextInput(
        label="Role ID",
        placeholder="Enter the role ID to edit",
        required=True,
        min_length=17,
        max_length=20
    )
    
    new_label = discord.ui.TextInput(
        label="New Button Label",
        placeholder="Enter the new text to display on the button",
        required=True,
        max_length=80
    )
    
    new_emoji = discord.ui.TextInput(
        label="New Emoji",
        placeholder="Enter a new emoji (e.g., 🎮, 🎯, 🏆)",
        required=False,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_id = int(self.role_id.value)
            success = await self.cog.edit_role_in_panel(interaction.guild.id, role_id, self.new_label.value, self.new_emoji.value or "")
            
            if success:
                embed = discord.Embed(
                    title="✅ Role Updated!",
                    description=f"Role has been updated in the panel.",
                    color=COLORS['success']
                )
                embed.add_field(name="New Label", value=self.new_label.value, inline=True)
                if self.new_emoji.value:
                    embed.add_field(name="New Emoji", value=self.new_emoji.value, inline=True)
                embed.set_footer(text="Auto-deletes in 15s")
                
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
                
                # Refresh the role panel
                await self.cog.refresh_role_panel(interaction.guild.id)
            else:
                await interaction.response.send_message("❌ Role not found in panel or failed to update.", ephemeral=True, delete_after=15)
                
        except ValueError:
            await interaction.response.send_message("❌ Invalid role ID! Please enter a valid number.", ephemeral=True, delete_after=15)

class RemoveRoleModal(discord.ui.Modal, title="Remove Role from Panel"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    role_id = discord.ui.TextInput(
        label="Role ID",
        placeholder="Enter the role ID to remove",
        required=True,
        min_length=17,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_id = int(self.role_id.value)
            success = await self.cog.remove_role_from_panel(interaction.guild.id, role_id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Role Removed!",
                    description=f"Role has been removed from the panel.",
                    color=COLORS['success']
                )
                embed.set_footer(text="Auto-deletes in 15s")
                
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
                
                # Refresh the role panel
                await self.cog.refresh_role_panel(interaction.guild.id)
            else:
                await interaction.response.send_message("❌ Role not found in panel or failed to remove.", ephemeral=True, delete_after=15)
                
        except ValueError:
            await interaction.response.send_message("❌ Invalid role ID! Please enter a valid number.", ephemeral=True, delete_after=15)

class RoleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = 'data/role_system.json'
        self.role_panels = self.load_role_panels()
        self.panel_messages = {}  # Store panel message IDs for each guild

    def load_role_panels(self):
        """Load role panel data from JSON file"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_role_panels(self):
        """Save role panel data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.role_panels, f, indent=2)

    async def add_role_to_panel(self, guild_id: int, role_id: int, label: str, emoji: str) -> bool:
        """Add a role to the panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels:
            self.role_panels[guild_key] = []
        
        # Check if role already exists
        for role_data in self.role_panels[guild_key]:
            if role_data['role_id'] == role_id:
                return False
        
        # Add new role
        self.role_panels[guild_key].append({
            'role_id': role_id,
            'label': label,
            'emoji': emoji,
            'added_at': datetime.now().isoformat()
        })
        
        self.save_role_panels()
        return True

    async def edit_role_in_panel(self, guild_id: int, role_id: int, new_label: str, new_emoji: str) -> bool:
        """Edit a role in the panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels:
            return False
        
        for role_data in self.role_panels[guild_key]:
            if role_data['role_id'] == role_id:
                role_data['label'] = new_label
                role_data['emoji'] = new_emoji
                role_data['updated_at'] = datetime.now().isoformat()
                self.save_role_panels()
                return True
        
        return False

    async def remove_role_from_panel(self, guild_id: int, role_id: int) -> bool:
        """Remove a role from the panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels:
            return False
        
        for i, role_data in enumerate(self.role_panels[guild_key]):
            if role_data['role_id'] == role_id:
                del self.role_panels[guild_key][i]
                self.save_role_panels()
                return True
        
        return False

    async def create_role_panel(self, guild_id: int, channel_id: int) -> discord.Message:
        """Create a new role panel in the specified channel"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return None
        
        guild_key = str(guild_id)
        roles = self.role_panels.get(guild_key, [])
        
        if not roles:
            embed = discord.Embed(
                title="🎭 Role Assignment",
                description="No roles have been configured yet.\n\nUse the admin panel to add roles!",
                color=COLORS['info']
            )
            embed.set_footer(text="Click the buttons below to get or remove roles")
        else:
            embed = discord.Embed(
                title="🎭 Role Assignment",
                description="Click the buttons below to get or remove roles:\n\n" + 
                           "\n".join([f"• {role['emoji']} **{role['label']}**" for role in roles]),
                color=COLORS['primary']
            )
            embed.set_footer(text="Click a button to toggle the role")
        
        view = RolePanelView(self)
        message = await channel.send(embed=embed, view=view)
        
        # Store the message ID
        if guild_key not in self.panel_messages:
            self.panel_messages[guild_key] = {}
        self.panel_messages[guild_key]['role_panel'] = message.id
        
        return message

    async def refresh_role_panel(self, guild_id: int):
        """Refresh the role panel with updated buttons"""
        guild_key = str(guild_id)
        
        if guild_key not in self.panel_messages or 'role_panel' not in self.panel_messages[guild_key]:
            return
        
        message_id = self.panel_messages[guild_key]['role_panel']
        guild = self.bot.get_guild(guild_id)
        
        if not guild:
            return
        
        # Find the message in any channel
        message = None
        for channel in guild.text_channels:
            try:
                message = await channel.fetch_message(message_id)
                break
            except:
                continue
        
        if message:
            # Update the embed and view
            roles = self.role_panels.get(guild_key, [])
            
            if not roles:
                embed = discord.Embed(
                    title="🎭 Role Assignment",
                    description="No roles have been configured yet.\n\nUse the admin panel to add roles!",
                    color=COLORS['info']
                )
                embed.set_footer(text="Click the buttons below to get or remove roles")
            else:
                embed = discord.Embed(
                    title="🎭 Role Assignment",
                    description="Click the buttons below to get or remove roles:\n\n" + 
                               "\n".join([f"• {role['emoji']} **{role['label']}**" for role in roles]),
                    color=COLORS['primary']
                )
                embed.set_footer(text="Click a button to toggle the role")
            
            view = RolePanelView(self)
            await message.edit(embed=embed, view=view)

    @commands.command(name='createrolepanel')
    @commands.has_permissions(administrator=True)
    async def create_role_panel_command(self, ctx, channel: discord.TextChannel = None):
        """Create a role assignment panel in the current or specified channel"""
        if not channel:
            channel = ctx.channel
        
        message = await self.create_role_panel(ctx.guild.id, channel.id)
        
        if message:
            embed = discord.Embed(
                title="✅ Role Panel Created!",
                description=f"Role assignment panel has been created in {channel.mention}",
                color=COLORS['success']
            )
            embed.add_field(
                name="Next Steps",
                value="Use the admin panel to add roles to this panel!",
                inline=False
            )
            await ctx.send(embed=embed, delete_after=15)
        else:
            await ctx.send("❌ Failed to create role panel!", delete_after=10)

    @commands.command(name='adminrolepanel')
    @commands.has_permissions(administrator=True)
    async def admin_role_panel_command(self, ctx):
        """Open the role management admin panel"""
        embed = discord.Embed(
            title="🛠️ Role Management Panel",
            description="Use the buttons below to manage role assignments:",
            color=COLORS['primary']
        )
        embed.add_field(
            name="➕ Add Role", 
            value="Add a new role to the assignment panel", 
            inline=False
        )
        embed.add_field(
            name="✏️ Edit Role", 
            value="Modify an existing role's display settings", 
            inline=False
        )
        embed.add_field(
            name="🗑️ Remove Role", 
            value="Remove a role from the assignment panel", 
            inline=False
        )
        embed.add_field(
            name="📋 List Roles", 
            value="View all configured roles", 
            inline=False
        )
        embed.set_footer(text="Admin Panel • Only visible to administrators")
        
        view = AdminRoleView(self)
        await ctx.send(embed=embed, view=view, delete_after=300)  # Delete after 5 minutes

    async def list_roles_command(self, interaction: discord.Interaction):
        """List all configured roles (called from admin panel)"""
        guild_key = str(interaction.guild.id)
        roles = self.role_panels.get(guild_key, [])
        
        if not roles:
            embed = discord.Embed(
                title="📋 Configured Roles",
                description="No roles have been configured yet.",
                color=COLORS['info']
            )
        else:
            embed = discord.Embed(
                title="📋 Configured Roles",
                description=f"Found {len(roles)} configured role(s):",
                color=COLORS['primary']
            )
            
            for i, role_data in enumerate(roles, 1):
                role = interaction.guild.get_role(role_data['role_id'])
                role_name = role.name if role else "Unknown Role"
                
                embed.add_field(
                    name=f"{i}. {role_data['emoji']} {role_data['label']}",
                    value=f"Role: {role_name}\nID: {role_data['role_id']}",
                    inline=False
                )
        
        embed.set_footer(text="Auto-deletes in 30s")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=30)

    @commands.Cog.listener()
    async def on_ready(self):
        """Recreate role panels when bot restarts"""
        for guild in self.bot.guilds:
            guild_key = str(guild.id)
            if guild_key in self.role_panels and self.role_panels[guild_key]:
                # Try to find existing panel message
                panel_found = False
                
                # Check if we have a stored message ID
                if guild_key in self.panel_messages and 'role_panel' in self.panel_messages[guild_key]:
                    message_id = self.panel_messages[guild_key]['role_panel']
                    
                    # Try to find the message
                    for channel in guild.text_channels:
                        try:
                            message = await channel.fetch_message(message_id)
                            if message:
                                # Update the view to make it functional again
                                view = RolePanelView(self)
                                await message.edit(view=view)
                                panel_found = True
                                break
                        except:
                            continue
                
                # If no panel found, create a new one in the first available channel
                if not panel_found:
                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).send_messages:
                            await self.create_role_panel(guild.id, channel.id)
                            break

async def setup(bot):
    await bot.add_cog(RoleSystem(bot))
