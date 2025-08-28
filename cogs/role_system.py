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
    def __init__(self, cog, panel_id: str):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog
        self.panel_id = panel_id
        self.update_buttons()

    def update_buttons(self):
        """Update the view with current role buttons"""
        # Clear existing buttons
        self.clear_items()
        
        try:
            # Add role buttons
            guild_id = str(self.cog.bot.guilds[0].id) if self.cog.bot.guilds else None
            if guild_id and guild_id in self.cog.role_panels:
                guild_data = self.cog.role_panels[guild_id]
                
                # Ensure guild_data is a dictionary
                if not isinstance(guild_data, dict):
                    return
                
                panel = guild_data.get(self.panel_id, {})
                if not isinstance(panel, dict):
                    return
                    
                roles = panel.get('roles', [])
                if not isinstance(roles, list):
                    return
                
                for role_data in roles:
                    if isinstance(role_data, dict) and 'role_id' in role_data and 'label' in role_data:
                        button = RoleButton(
                            role_id=role_data['role_id'],
                            label=role_data['label'],
                            emoji=role_data.get('emoji', ''),
                            style=discord.ButtonStyle.primary,
                            custom_id=f"role_{self.panel_id}_{role_data['role_id']}"
                        )
                        self.add_item(button)
        except Exception as e:
            print(f"Error updating buttons for panel {self.panel_id}: {e}")

class AdminRoleView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog

    @discord.ui.button(label='📋 Manage Panels', style=discord.ButtonStyle.primary, emoji='📋', custom_id='admin_manage_panels')
    async def manage_panels(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ManagePanelsModal(self.cog)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='➕ Add Role', style=discord.ButtonStyle.success, emoji='➕', custom_id='admin_add_role')
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show panel selection first
        await self.show_panel_selection(interaction, "add")

    @discord.ui.button(label='✏️ Edit Role', style=discord.ButtonStyle.primary, emoji='✏️', custom_id='admin_edit_role')
    async def edit_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_panel_selection(interaction, "edit")

    @discord.ui.button(label='🗑️ Remove Role', style=discord.ButtonStyle.danger, emoji='🗑️', custom_id='admin_remove_role')
    async def remove_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_panel_selection(interaction, "remove")

    @discord.ui.button(label='📊 List All', style=discord.ButtonStyle.secondary, emoji='📊', custom_id='admin_list_all')
    async def list_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.list_all_panels_command(interaction)

    @discord.ui.button(label='🔄 Refresh Panel', style=discord.ButtonStyle.secondary, emoji='🔄', custom_id='admin_refresh_role_panel')
    async def refresh_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛠️ Role Management Panel",
            description="Use the buttons below to manage role assignments:",
            color=COLORS['primary']
        )
        embed.add_field(
            name="📋 Manage Panels", 
            value="Create, edit, or delete role panels", 
            inline=False
        )
        embed.add_field(
            name="➕ Add Role", 
            value="Add a new role to a panel", 
            inline=False
        )
        embed.add_field(
            name="✏️ Edit Role", 
            value="Modify an existing role's display settings", 
            inline=False
        )
        embed.add_field(
            name="🗑️ Remove Role", 
            value="Remove a role from a panel", 
            inline=False
        )
        embed.add_field(
            name="📊 List All", 
            value="View all panels and their roles", 
            inline=False
        )
        embed.set_footer(text="Admin Panel • Only visible to administrators")
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_panel_selection(self, interaction: discord.Interaction, action: str):
        """Show panel selection for role operations"""
        try:
            guild_key = str(interaction.guild.id)
            guild_data = self.cog.role_panels.get(guild_key, {})
            
            # Ensure guild_data is a dictionary
            if not isinstance(guild_data, dict):
                await interaction.response.send_message("❌ Invalid data format. Please contact an administrator.", ephemeral=True, delete_after=15)
                return
            
            if not guild_data:
                await interaction.response.send_message("❌ No panels exist yet! Create a panel first.", ephemeral=True, delete_after=15)
                return
            
            # Create panel selection embed
            embed = discord.Embed(
                title=f"Select Panel for {action.title()}",
                description="Choose which panel to manage:",
                color=COLORS['primary']
            )
            
            for panel_id, panel_data in guild_data.items():
                if isinstance(panel_data, dict):
                    role_count = len(panel_data.get('roles', []))
                    embed.add_field(
                        name=f"📋 {panel_data.get('name', panel_id)}",
                        value=f"ID: `{panel_id}`\nRoles: {role_count}",
                        inline=True
                    )
            
            # Create panel selection view
            view = PanelSelectionView(self.cog, action)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=60)
        except Exception as e:
            print(f"Error showing panel selection: {e}")
            await interaction.response.send_message("❌ An error occurred while showing panel selection.", ephemeral=True, delete_after=15)

class PanelSelectionView(discord.ui.View):
    def __init__(self, cog, action: str):
        super().__init__(timeout=60)
        self.cog = cog
        self.action = action
        self.add_panel_options()

    def add_panel_options(self):
        """Add panel selection options"""
        try:
            guild_id = str(self.cog.bot.guilds[0].id) if self.cog.bot.guilds else None
            if guild_id and guild_id in self.cog.role_panels:
                guild_data = self.cog.role_panels[guild_id]
                
                # Ensure guild_data is a dictionary
                if not isinstance(guild_data, dict):
                    return
                
                for panel_id, panel_data in guild_data.items():
                    if isinstance(panel_data, dict):
                        button = discord.ui.Button(
                            label=panel_data.get('name', panel_id),
                            custom_id=f"select_panel_{panel_id}_{self.action}",
                            style=discord.ButtonStyle.primary
                        )
                        button.callback = self.panel_selected
                        self.add_item(button)
        except Exception as e:
            print(f"Error adding panel options: {e}")

    async def panel_selected(self, interaction: discord.Interaction):
        """Handle panel selection"""
        custom_id = interaction.data.get('custom_id', '')
        parts = custom_id.split('_')
        if len(parts) >= 4:
            panel_id = parts[2]
            action = parts[3]
            
            if action == "add":
                modal = AddRoleModal(self.cog, panel_id)
                await interaction.response.send_modal(modal)
            elif action == "edit":
                modal = EditRoleModal(self.cog, panel_id)
                await interaction.response.send_modal(modal)
            elif action == "remove":
                modal = RemoveRoleModal(self.cog, panel_id)
                await interaction.response.send_modal(modal)

class ManagePanelsModal(discord.ui.Modal, title="Manage Role Panels"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    action = discord.ui.TextInput(
        label="Action",
        placeholder="Enter: create, edit, or delete",
        required=True,
        max_length=10
    )
    
    panel_id = discord.ui.TextInput(
        label="Panel ID",
        placeholder="Enter panel ID (e.g., games, age, gender)",
        required=True,
        max_length=20
    )
    
    panel_name = discord.ui.TextInput(
        label="Panel Name",
        placeholder="Enter display name (e.g., Game Roles, Age Groups)",
        required=False,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            action = self.action.value.lower()
            panel_id = self.panel_id.value.lower()
            panel_name = self.panel_name.value or panel_id.title()
            
            if action == "create":
                success = await self.cog.create_panel(interaction.guild.id, panel_id, panel_name)
                if success:
                    await interaction.response.send_message(f"✅ Panel '{panel_name}' created successfully!", ephemeral=True, delete_after=15)
                else:
                    await interaction.response.send_message("❌ Panel already exists or creation failed!", ephemeral=True, delete_after=15)
            
            elif action == "edit":
                success = await self.cog.edit_panel(interaction.guild.id, panel_id, panel_name)
                if success:
                    await interaction.response.send_message(f"✅ Panel '{panel_id}' updated successfully!", ephemeral=True, delete_after=15)
                else:
                    await interaction.response.send_message("❌ Panel not found or update failed!", ephemeral=True, delete_after=15)
            
            elif action == "delete":
                success = await self.cog.delete_panel(interaction.guild.id, panel_id)
                if success:
                    await interaction.response.send_message(f"✅ Panel '{panel_id}' deleted successfully!", ephemeral=True, delete_after=15)
                else:
                    await interaction.response.send_message("❌ Panel not found or deletion failed!", ephemeral=True, delete_after=15)
            
            else:
                await interaction.response.send_message("❌ Invalid action! Use: create, edit, or delete", ephemeral=True, delete_after=15)
        except Exception as e:
            print(f"Error managing panels: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred while managing panels. Please try again.", ephemeral=True, delete_after=15)
            except:
                # If response already sent, try followup
                try:
                    await interaction.followup.send("❌ An error occurred while managing panels. Please try again.", ephemeral=True, delete_after=15)
                except:
                    print(f"Failed to send error message to user: {e}")

class AddRoleModal(discord.ui.Modal, title="Add Role to Panel"):
    def __init__(self, cog, panel_id: str):
        super().__init__()
        self.cog = cog
        self.panel_id = panel_id

    role_name = discord.ui.TextInput(
        label="Role Name",
        placeholder="Enter the role name (e.g., Gamer, Adult, Female)",
        required=True,
        max_length=50
    )
    
    button_label = discord.ui.TextInput(
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
            role_name = self.role_name.value
            button_label = self.button_label.value
            emoji = self.emoji.value or ""
            
            # Find role by name
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                await interaction.response.send_message(f"❌ Role '{role_name}' not found! Please check the spelling.", ephemeral=True, delete_after=15)
                return

            # Add role to panel
            success = await self.cog.add_role_to_panel(interaction.guild.id, self.panel_id, role.id, button_label, emoji)
            
            if success:
                embed = discord.Embed(
                    title="✅ Role Added!",
                    description=f"**{role.name}** has been added to the **{self.panel_id}** panel.",
                    color=COLORS['success']
                )
                embed.add_field(name="Button Label", value=button_label, inline=True)
                if emoji:
                    embed.add_field(name="Emoji", value=emoji, inline=True)
                embed.set_footer(text="Auto-deletes in 15s")
                
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
                
                # Refresh the role panel
                await self.cog.refresh_role_panel(interaction.guild.id, self.panel_id)
            else:
                await interaction.response.send_message("❌ Failed to add role. It might already exist in the panel.", ephemeral=True, delete_after=15)
        except Exception as e:
            print(f"Error adding role: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred while adding the role. Please try again.", ephemeral=True, delete_after=15)
            except:
                # If response already sent, try followup
                try:
                    await interaction.followup.send("❌ An error occurred while adding the role. Please try again.", ephemeral=True, delete_after=15)
                except:
                    print(f"Failed to send error message to user: {e}")

class EditRoleModal(discord.ui.Modal, title="Edit Role in Panel"):
    def __init__(self, cog, panel_id: str):
        super().__init__()
        self.cog = cog
        self.panel_id = panel_id

    role_name = discord.ui.TextInput(
        label="Role Name",
        placeholder="Enter the role name to edit",
        required=True,
        max_length=50
    )
    
    new_button_label = discord.ui.TextInput(
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
            role_name = self.role_name.value
            new_button_label = self.new_button_label.value
            new_emoji = self.new_emoji.value or ""
            
            # Find role by name
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                await interaction.response.send_message(f"❌ Role '{role_name}' not found! Please check the spelling.", ephemeral=True, delete_after=15)
                return

            success = await self.cog.edit_role_in_panel(interaction.guild.id, self.panel_id, role.id, new_button_label, new_emoji)
            
            if success:
                embed = discord.Embed(
                    title="✅ Role Updated!",
                    description=f"Role has been updated in the **{self.panel_id}** panel.",
                    color=COLORS['success']
                )
                embed.add_field(name="New Button Label", value=new_button_label, inline=True)
                if new_emoji:
                    embed.add_field(name="New Emoji", value=new_emoji, inline=True)
                embed.set_footer(text="Auto-deletes in 15s")
                
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
                
                # Refresh the role panel
                await self.cog.refresh_role_panel(interaction.guild.id, self.panel_id)
            else:
                await interaction.response.send_message("❌ Role not found in panel or failed to update.", ephemeral=True, delete_after=15)
        except Exception as e:
            print(f"Error editing role: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred while editing the role. Please try again.", ephemeral=True, delete_after=15)
            except:
                # If response already sent, try followup
                try:
                    await interaction.followup.send("❌ An error occurred while editing the role. Please try again.", ephemeral=True, delete_after=15)
                except:
                    print(f"Failed to send error message to user: {e}")

class RemoveRoleModal(discord.ui.Modal, title="Remove Role from Panel"):
    def __init__(self, cog, panel_id: str):
        super().__init__()
        self.cog = cog
        self.panel_id = panel_id

    role_name = discord.ui.TextInput(
        label="Role Name",
        placeholder="Enter the role name to remove",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            role_name = self.role_name.value
            
            # Find role by name
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                await interaction.response.send_message(f"❌ Role '{role_name}' not found! Please check the spelling.", ephemeral=True, delete_after=15)
                return

            success = await self.cog.remove_role_from_panel(interaction.guild.id, self.panel_id, role.id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Role Removed!",
                    description=f"Role has been removed from the **{self.panel_id}** panel.",
                    color=COLORS['success']
                )
                embed.set_footer(text="Auto-deletes in 15s")
                
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=15)
                
                # Refresh the role panel
                await self.cog.refresh_role_panel(interaction.guild.id, self.panel_id)
            else:
                await interaction.response.send_message("❌ Role not found in panel or failed to remove.", ephemeral=True, delete_after=15)
        except Exception as e:
            print(f"Error removing role: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred while removing the role. Please try again.", ephemeral=True, delete_after=15)
            except:
                # If response already sent, try followup
                try:
                    await interaction.followup.send("❌ An error occurred while removing the role. Please try again.", ephemeral=True, delete_after=15)
                except:
                    print(f"Failed to send error message to user: {e}")

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
                    data = json.load(f)
                    
                # Migrate old data format to new format
                migrated_data = self.migrate_old_data(data)
                return migrated_data
            except:
                return {}
        return {}

    def migrate_old_data(self, data):
        """Migrate old data format to new format"""
        migrated_data = {}
        
        for guild_key, guild_data in data.items():
            if isinstance(guild_data, list):
                # Old format: guild_data is a list of roles
                # Convert to new format with a default 'main' panel
                migrated_data[guild_key] = {
                    'main': {
                        'name': 'Main Role Panel',
                        'roles': guild_data,
                        'created_at': datetime.now().isoformat(),
                        'migrated': True
                    }
                }
            elif isinstance(guild_data, dict):
                # New format: guild_data is a dict of panels
                migrated_data[guild_key] = guild_data
            else:
                # Invalid format, skip this guild
                continue
        
        # Save migrated data
        if migrated_data != data:
            self.role_panels = migrated_data
            self.save_role_panels()
        
        return migrated_data

    def save_role_panels(self):
        """Save role panel data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.role_panels, f, indent=2)

    async def create_panel(self, guild_id: int, panel_id: str, panel_name: str) -> bool:
        """Create a new role panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels:
            self.role_panels[guild_key] = {}
        
        if panel_id in self.role_panels[guild_key]:
            return False  # Panel already exists
        
        self.role_panels[guild_key][panel_id] = {
            'name': panel_name,
            'roles': [],
            'created_at': datetime.now().isoformat()
        }
        
        self.save_role_panels()
        return True

    async def edit_panel(self, guild_id: int, panel_id: str, new_name: str) -> bool:
        """Edit an existing panel name"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            return False
        
        self.role_panels[guild_key][panel_id]['name'] = new_name
        self.role_panels[guild_key][panel_id]['updated_at'] = datetime.now().isoformat()
        self.save_role_panels()
        return True

    async def delete_panel(self, guild_id: int, panel_id: str) -> bool:
        """Delete a role panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            return False
        
        del self.role_panels[guild_key][panel_id]
        self.save_role_panels()
        return True

    async def add_role_to_panel(self, guild_id: int, panel_id: str, role_id: int, label: str, emoji: str) -> bool:
        """Add a role to a specific panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            return False
        
        # Check if role already exists in this panel
        for role_data in self.role_panels[guild_key][panel_id]['roles']:
            if role_data['role_id'] == role_id:
                return False
        
        # Add new role
        self.role_panels[guild_key][panel_id]['roles'].append({
            'role_id': role_id,
            'label': label,
            'emoji': emoji,
            'added_at': datetime.now().isoformat()
        })
        
        self.save_role_panels()
        return True

    async def edit_role_in_panel(self, guild_id: int, panel_id: str, role_id: int, new_label: str, new_emoji: str) -> bool:
        """Edit a role in a specific panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            return False
        
        for role_data in self.role_panels[guild_key][panel_id]['roles']:
            if role_data['role_id'] == role_id:
                role_data['label'] = new_label
                role_data['emoji'] = new_emoji
                role_data['updated_at'] = datetime.now().isoformat()
                self.save_role_panels()
                return True
        
        return False

    async def remove_role_from_panel(self, guild_id: int, panel_id: str, role_id: int) -> bool:
        """Remove a role from a specific panel"""
        guild_key = str(guild_id)
        
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            return False
        
        for i, role_data in enumerate(self.role_panels[guild_key][panel_id]['roles']):
            if role_data['role_id'] == role_id:
                del self.role_panels[guild_key][panel_id]['roles'][i]
                self.save_role_panels()
                return True
        
        return False

    async def create_role_panel(self, guild_id: int, channel_id: int, panel_id: str) -> discord.Message:
        """Create a new role panel in the specified channel"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return None
        
        guild_key = str(guild_id)
        panel = self.role_panels.get(guild_key, {}).get(panel_id, {})
        roles = panel.get('roles', [])
        panel_name = panel.get('name', panel_id.title())
        
        if not roles:
            embed = discord.Embed(
                title=f"🎭 {panel_name}",
                description="No roles have been configured yet.\n\nUse the admin panel to add roles!",
                color=COLORS['info']
            )
            embed.set_footer(text="Click the buttons below to get or remove roles")
        else:
            embed = discord.Embed(
                title=f"🎭 {panel_name}",
                description="Click the buttons below to get or remove roles:\n\n" + 
                           "\n".join([f"• {role['emoji']} **{role['label']}**" for role in roles]),
                color=COLORS['primary']
            )
            embed.set_footer(text="Click a button to toggle the role")
        
        view = RolePanelView(self, panel_id)
        message = await channel.send(embed=embed, view=view)
        
        # Store the message ID
        if guild_key not in self.panel_messages:
            self.panel_messages[guild_key] = {}
        self.panel_messages[guild_key][panel_id] = message.id
        
        return message

    async def refresh_role_panel(self, guild_id: int, panel_id: str):
        """Refresh a specific role panel with updated buttons"""
        guild_key = str(guild_id)
        
        if guild_key not in self.panel_messages or panel_id not in self.panel_messages[guild_key]:
            return
        
        message_id = self.panel_messages[guild_key][panel_id]
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
            panel = self.role_panels.get(guild_key, {}).get(panel_id, {})
            roles = panel.get('roles', [])
            panel_name = panel.get('name', panel_id.title())
            
            if not roles:
                embed = discord.Embed(
                    title=f"🎭 {panel_name}",
                    description="No roles have been configured yet.\n\nUse the admin panel to add roles!",
                    color=COLORS['info']
                )
                embed.set_footer(text="Click the buttons below to get or remove roles")
            else:
                embed = discord.Embed(
                    title=f"🎭 {panel_name}",
                    description="Click the buttons below to get or remove roles:\n\n" + 
                               "\n".join([f"• {role['emoji']} **{role['label']}**" for role in roles]),
                    color=COLORS['primary']
                )
                embed.set_footer(text="Click a button to toggle the role")
            
            view = RolePanelView(self, panel_id)
            await message.edit(embed=embed, view=view)

    @commands.command(name='createrolepanel')
    @commands.has_permissions(administrator=True)
    async def create_role_panel_command(self, ctx, panel_id: str, channel: discord.TextChannel = None):
        """Create a role assignment panel in the current or specified channel"""
        if not channel:
            channel = ctx.channel
        
        # Check if panel exists, if not create it
        guild_key = str(ctx.guild.id)
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            await self.create_panel(ctx.guild.id, panel_id, panel_id.title())
        
        message = await self.create_role_panel(ctx.guild.id, channel.id, panel_id)
        
        if message:
            embed = discord.Embed(
                title="✅ Role Panel Created!",
                description=f"Role assignment panel for **{panel_id}** has been created in {channel.mention}",
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

    @commands.command(name='displaypanel')
    @commands.has_permissions(administrator=True)
    async def display_panel_command(self, ctx, panel_id: str, channel: discord.TextChannel = None):
        """Display an existing role panel in the current or specified channel"""
        if not channel:
            channel = ctx.channel
        
        guild_key = str(ctx.guild.id)
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            await ctx.send(f"❌ Panel '{panel_id}' doesn't exist! Create it first with `!createrolepanel {panel_id}`", delete_after=15)
            return
        
        # Check if panel is already displayed in this channel
        if guild_key in self.panel_messages and panel_id in self.panel_messages[guild_key]:
            try:
                old_message_id = self.panel_messages[guild_key][panel_id]
                old_channel = None
                
                # Find the old message
                for ch in ctx.guild.text_channels:
                    try:
                        old_message = await ch.fetch_message(old_message_id)
                        if old_message:
                            old_channel = ch
                            break
                    except:
                        continue
                
                if old_channel and old_channel.id != channel.id:
                    # Ask if user wants to move the panel
                    embed = discord.Embed(
                        title="⚠️ Panel Already Displayed",
                        description=f"Panel '{panel_id}' is already displayed in {old_channel.mention}",
                        color=COLORS['warning']
                    )
                    embed.add_field(
                        name="Options",
                        value="1. Use `!movepanel {panel_id} {channel.mention}` to move it\n2. Use `!removepanel {panel_id}` to remove it first",
                        inline=False
                    )
                    await ctx.send(embed=embed, delete_after=20)
                    return
                elif old_channel and old_channel.id == channel.id:
                    await ctx.send(f"✅ Panel '{panel_id}' is already displayed in {channel.mention}", delete_after=10)
                    return
            except:
                pass
        
        # Create/display the panel
        message = await self.create_role_panel(ctx.guild.id, channel.id, panel_id)
        
        if message:
            embed = discord.Embed(
                title="✅ Role Panel Displayed!",
                description=f"Role assignment panel for **{panel_id}** is now visible in {channel.mention}",
                color=COLORS['success']
            )
            embed.add_field(
                name="Next Steps",
                value="Use the admin panel to add roles to this panel!",
                inline=False
            )
            await ctx.send(embed=embed, delete_after=15)
        else:
            await ctx.send("❌ Failed to display role panel!", delete_after=10)

    @commands.command(name='movepanel')
    @commands.has_permissions(administrator=True)
    async def move_panel_command(self, ctx, panel_id: str, new_channel: discord.TextChannel):
        """Move a role panel to a different channel"""
        guild_key = str(ctx.guild.id)
        if guild_key not in self.role_panels or panel_id not in self.role_panels[guild_key]:
            await ctx.send(f"❌ Panel '{panel_id}' doesn't exist!", delete_after=15)
            return
        
        # Remove old panel message
        if guild_key in self.panel_messages and panel_id in self.panel_messages[guild_key]:
            old_message_id = self.panel_messages[guild_key][panel_id]
            
            # Try to delete the old message
            for ch in ctx.guild.text_channels:
                try:
                    old_message = await ch.fetch_message(old_message_id)
                    if old_message:
                        await old_message.delete()
                        break
                except:
                    continue
        
        # Create panel in new channel
        message = await self.create_role_panel(ctx.guild.id, new_channel.id, panel_id)
        
        if message:
            embed = discord.Embed(
                title="✅ Role Panel Moved!",
                description=f"Role assignment panel for **{panel_id}** has been moved to {new_channel.mention}",
                color=COLORS['success']
            )
            await ctx.send(embed=embed, delete_after=15)
        else:
            await ctx.send("❌ Failed to move role panel!", delete_after=10)

    @commands.command(name='removepanel')
    @commands.has_permissions(administrator=True)
    async def remove_panel_display_command(self, ctx, panel_id: str):
        """Remove a role panel display (but keep the panel data)"""
        guild_key = str(ctx.guild.id)
        if guild_key not in self.panel_messages or panel_id not in self.panel_messages[guild_key]:
            await ctx.send(f"❌ Panel '{panel_id}' is not currently displayed anywhere!", delete_after=15)
            return
        
        message_id = self.panel_messages[guild_key][panel_id]
        message_deleted = False
        
        # Try to delete the message
        for channel in ctx.guild.text_channels:
            try:
                message = await channel.fetch_message(message_id)
                if message:
                    await message.delete()
                    message_deleted = True
                    break
            except:
                continue
        
        if message_deleted:
            # Remove from panel_messages
            del self.panel_messages[guild_key][panel_id]
            
            embed = discord.Embed(
                title="✅ Panel Display Removed!",
                description=f"Role panel '{panel_id}' is no longer displayed, but the panel data is preserved.",
                color=COLORS['success']
            )
            embed.add_field(
                name="To Display Again",
                value=f"Use `!displaypanel {panel_id} [channel]`",
                inline=False
            )
            await ctx.send(embed=embed, delete_after=15)
        else:
            await ctx.send(f"❌ Failed to remove panel display for '{panel_id}'", delete_after=15)

    @commands.command(name='listpanels')
    @commands.has_permissions(administrator=True)
    async def list_panels_command(self, ctx):
        """List all role panels and where they're displayed"""
        guild_key = str(ctx.guild.id)
        panels = self.role_panels.get(guild_key, {})
        panel_messages = self.panel_messages.get(guild_key, {})
        
        if not panels:
            embed = discord.Embed(
                title="📋 Role Panels",
                description="No role panels have been created yet.",
                color=COLORS['info']
            )
        else:
            embed = discord.Embed(
                title="📋 Role Panels",
                description=f"Found {len(panels)} panel(s):",
                color=COLORS['primary']
            )
            
            for panel_id, panel_data in panels.items():
                roles = panel_data.get('roles', [])
                panel_name = panel_data.get('name', panel_id.title())
                
                # Check if panel is displayed
                if panel_id in panel_messages:
                    message_id = panel_messages[panel_id]
                    channel_info = "Unknown channel"
                    
                    # Find which channel it's in
                    for channel in ctx.guild.text_channels:
                        try:
                            message = await channel.fetch_message(message_id)
                            if message:
                                channel_info = channel.mention
                                break
                        except:
                            continue
                    
                    status = f"✅ Displayed in {channel_info}"
                else:
                    status = "❌ Not displayed"
                
                if roles:
                    role_count = len(roles)
                    embed.add_field(
                        name=f"📋 {panel_name}",
                        value=f"ID: `{panel_id}`\nStatus: {status}\nRoles: {role_count}",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name=f"📋 {panel_name}",
                        value=f"ID: `{panel_id}`\nStatus: {status}\nNo roles configured",
                        inline=True
                    )
        
        embed.set_footer(text="Use !displaypanel <id> [channel] to show panels")
        await ctx.send(embed=embed, delete_after=60)

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
            name="📋 Manage Panels", 
            value="Create, edit, or delete role panels", 
            inline=False
        )
        embed.add_field(
            name="➕ Add Role", 
            value="Add a new role to a panel", 
            inline=False
        )
        embed.add_field(
            name="✏️ Edit Role", 
            value="Modify an existing role's display settings", 
            inline=False
        )
        embed.add_field(
            name="🗑️ Remove Role", 
            value="Remove a role from a panel", 
            inline=False
        )
        embed.add_field(
            name="📊 List All", 
            value="View all panels and their roles", 
            inline=False
        )
        embed.set_footer(text="Admin Panel • Only visible to administrators")
        
        view = AdminRoleView(self)
        await ctx.send(embed=embed, view=view, delete_after=300)  # Delete after 5 minutes

    async def list_all_panels_command(self, interaction: discord.Interaction):
        """List all panels and their roles (called from admin panel)"""
        try:
            guild_key = str(interaction.guild.id)
            guild_data = self.role_panels.get(guild_key, {})
            
            # Ensure guild_data is a dictionary
            if not isinstance(guild_data, dict):
                embed = discord.Embed(
                    title="📊 All Role Panels",
                    description="❌ Invalid data format. Please contact an administrator.",
                    color=COLORS['error']
                )
                embed.set_footer(text="Auto-deletes in 45s")
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=45)
                return
            
            if not guild_data:
                embed = discord.Embed(
                    title="📊 All Role Panels",
                    description="No panels have been created yet.",
                    color=COLORS['info']
                )
            else:
                embed = discord.Embed(
                    title="📊 All Role Panels",
                    description=f"Found {len(guild_data)} panel(s):",
                    color=COLORS['primary']
                )
                
                for panel_id, panel_data in guild_data.items():
                    if isinstance(panel_data, dict):
                        roles = panel_data.get('roles', [])
                        panel_name = panel_data.get('name', panel_id.title())
                        
                        if roles and isinstance(roles, list):
                            role_list = "\n".join([f"• {role.get('emoji', '')} {role.get('label', 'Unknown')}" for role in roles if isinstance(role, dict)])
                            embed.add_field(
                                name=f"📋 {panel_name}",
                                value=f"ID: `{panel_id}`\nRoles ({len(roles)}):\n{role_list}",
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name=f"📋 {panel_name}",
                                value=f"ID: `{panel_id}`\nNo roles configured",
                                inline=False
                            )
            
            embed.set_footer(text="Auto-deletes in 45s")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=45)
        except Exception as e:
            print(f"Error listing panels: {e}")
            embed = discord.Embed(
                title="📊 All Role Panels",
                description="❌ An error occurred while listing panels.",
                color=COLORS['error']
            )
            embed.set_footer(text="Auto-deletes in 45s")
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=45)

    @commands.Cog.listener()
    async def on_ready(self):
        """Recreate role panels when bot restarts"""
        for guild in self.bot.guilds:
            try:
                guild_key = str(guild.id)
                if guild_key in self.role_panels:
                    guild_data = self.role_panels[guild_key]
                    
                    # Ensure guild_data is a dictionary
                    if not isinstance(guild_data, dict):
                        print(f"Warning: Invalid data format for guild {guild.name}, skipping...")
                        continue
                    
                    for panel_id, panel_data in guild_data.items():
                        try:
                            # Ensure panel_data has the expected structure
                            if not isinstance(panel_data, dict) or 'roles' not in panel_data:
                                print(f"Warning: Invalid panel data for {panel_id} in guild {guild.name}, skipping...")
                                continue
                            
                            # Try to find existing panel message
                            panel_found = False
                            
                            # Check if we have a stored message ID
                            if guild_key in self.panel_messages and panel_id in self.panel_messages[guild_key]:
                                message_id = self.panel_messages[guild_key][panel_id]
                                
                                # Try to find the message
                                for channel in guild.text_channels:
                                    try:
                                        message = await channel.fetch_message(message_id)
                                        if message:
                                            # Update the view to make it functional again
                                            view = RolePanelView(self, panel_id)
                                            await message.edit(view=view)
                                            panel_found = True
                                            break
                                    except:
                                        continue
                            
                            # If no panel found, create a new one in the first available channel
                            if not panel_found:
                                for channel in guild.text_channels:
                                    if channel.permissions_for(guild.me).send_messages:
                                        await self.create_role_panel(guild.id, channel.id, panel_id)
                                        break
                        except Exception as e:
                            print(f"Error processing panel {panel_id} in guild {guild.name}: {e}")
                            continue
            except Exception as e:
                print(f"Error processing guild {guild.name}: {e}")
                continue

async def setup(bot):
    await bot.add_cog(RoleSystem(bot))
