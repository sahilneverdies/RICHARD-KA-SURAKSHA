import discord
import aiosqlite

class WhitelistView(discord.ui.View):
    def __init__(self, author, member, db_manager):
        super().__init__(timeout=60)
        self.author = author
        self.member = member
        self.db_manager = db_manager
        self.selected_options = []

    @discord.ui.select(
        placeholder="Choose Your Options",
        min_values=1,
        max_values=15,
        options=[
            discord.SelectOption(label="Anti Role Creation", description="Whitelist from role creation protection", value="role_create"),
            discord.SelectOption(label="Anti Role Deletion", description="Whitelist from role deletion protection", value="role_delete"),
            discord.SelectOption(label="Anti Role Update", description="Whitelist from role update protection", value="role_update"),
            discord.SelectOption(label="Anti Channel Creation", description="Whitelist from channel creation protection", value="channel_create"),
            discord.SelectOption(label="Anti Channel Deletion", description="Whitelist from channel deletion protection", value="channel_delete"),
            discord.SelectOption(label="Anti Channel Update", description="Whitelist from channel update protection", value="channel_update"),
            discord.SelectOption(label="Anti Ban", description="Whitelist from ban protection", value="ban"),
            discord.SelectOption(label="Anti Kick", description="Whitelist from kick protection", value="kick"),
            discord.SelectOption(label="Anti Prune", description="Whitelist from prune protection", value="prune"),
            discord.SelectOption(label="Anti Webhook", description="Whitelist from webhook protection", value="webhook_manage"),
            discord.SelectOption(label="Anti Bot", description="Whitelist from bot protection", value="bot_add"),
            discord.SelectOption(label="Anti Server", description="Whitelist from server protection", value="server_update"),
            discord.SelectOption(label="Anti Ping", description="Whitelist from ping protection", value="mention_everyone"),
            discord.SelectOption(label="Anti Emoji", description="Whitelist from emoji protection", value="emoji"),
            discord.SelectOption(label="Anti Member Role Update", description="Whitelist from member role update protection", value="member_update")
        ],
        custom_id="wl"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.author.id:
            return
        self.selected_options = select.values
        embed = self.get_updated_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def get_updated_embed(self):
        event_status = {}
        events = ["role_create", "role_delete", "role_update", "channel_create", "channel_delete", "channel_update", "ban", "kick", "prune", "webhook_manage", "bot_add", "server_update", "mention_everyone", "emoji", "member_update"]
        
        for event in events:
            event_status[event] = event in self.selected_options
        
        description_lines = []
        for event, enabled in event_status.items():
            status_icon = "<:tick:1380440073526579270>" if enabled else "<:cross:1380440015070298172>"
            event_name = event.replace('_', ' ').title().replace('Role', 'Role').replace('Channel', 'Channel').replace('Ban', 'Ban').replace('Kick', 'Kick').replace('Prune', 'Prune').replace('Webhook Manage', 'Webhook').replace('Bot Add', 'Bot').replace('Server Update', 'Server').replace('Mention Everyone', 'Ping').replace('Emoji', 'Emoji').replace('Member Update', 'Member Role Update')
            description_lines.append(f"{status_icon} **{event_name}**")
        
        embed = discord.Embed(
            title="Whitelist Configuration",
            color=0x2f3136,
            description="\n".join(description_lines) + f"\n\n**Executor:** {self.author.mention} (`{self.author.id}`)\n**Target User:** {self.member.mention} (`{self.member.id}`)\n\nSelected {len(self.selected_options)}/15 permissions"
        )
        embed.set_author(name="Security System", icon_url=self.author.display_avatar.url)
        return embed

    @discord.ui.button(label="Add User To All Categories", style=discord.ButtonStyle.primary, custom_id="catWl")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return
        self.selected_options = ["role_create", "role_delete", "role_update", "channel_create", "channel_delete", "channel_update", "ban", "kick", "prune", "webhook_manage", "bot_add", "server_update", "mention_everyone", "emoji", "member_update"]
        embed = self.get_updated_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, custom_id="confirm")
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return
        await interaction.response.defer()
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author.id

class AntinukeView(discord.ui.View):
    def __init__(self, author, guild_id, db_manager):
        super().__init__(timeout=60)
        self.author = author
        self.guild_id = guild_id
        self.db_manager = db_manager
        self.selected_options = []

    async def load_current_events(self):
        async with aiosqlite.connect("database/antinuke.db") as db:
            async with db.execute("SELECT event_type FROM antinuke_events WHERE guild_id = ? AND enabled = TRUE", (self.guild_id,)) as cursor:
                results = await cursor.fetchall()
                self.selected_options = [result[0] for result in results]

    @discord.ui.select(
        placeholder="Choose Events to Enable",
        min_values=0,
        max_values=15,
        options=[
            discord.SelectOption(label="Anti Role Creation", description="Enable role creation protection", value="role_create"),
            discord.SelectOption(label="Anti Role Deletion", description="Enable role deletion protection", value="role_delete"),
            discord.SelectOption(label="Anti Role Update", description="Enable role update protection", value="role_update"),
            discord.SelectOption(label="Anti Channel Creation", description="Enable channel creation protection", value="channel_create"),
            discord.SelectOption(label="Anti Channel Deletion", description="Enable channel deletion protection", value="channel_delete"),
            discord.SelectOption(label="Anti Channel Update", description="Enable channel update protection", value="channel_update"),
            discord.SelectOption(label="Anti Ban", description="Enable ban protection", value="ban"),
            discord.SelectOption(label="Anti Kick", description="Enable kick protection", value="kick"),
            discord.SelectOption(label="Anti Prune", description="Enable prune protection", value="prune"),
            discord.SelectOption(label="Anti Webhook", description="Enable webhook protection", value="webhook_manage"),
            discord.SelectOption(label="Anti Bot", description="Enable bot protection", value="bot_add"),
            discord.SelectOption(label="Anti Server", description="Enable server protection", value="server_update"),
            discord.SelectOption(label="Anti Ping", description="Enable ping protection", value="mention_everyone"),
            discord.SelectOption(label="Anti Emoji", description="Enable emoji protection", value="emoji"),
            discord.SelectOption(label="Anti Member Role Update", description="Enable member role update protection", value="member_update")
        ],
        custom_id="antinuke_events"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.author.id:
            return
        self.selected_options = select.values
        embed = self.get_updated_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def get_updated_embed(self):
        event_status = {}
        all_events = ["role_create", "role_delete", "role_update", "channel_create", "channel_delete", "channel_update", "ban", "kick", "prune", "webhook_manage", "bot_add", "server_update", "mention_everyone", "emoji", "member_update"]
        
        for event in all_events:
            event_status[event] = event in self.selected_options
        
        description_lines = []
        for event, enabled in event_status.items():
            status_icon = "<:tick:1380440073526579270>" if enabled else "<:cross:1380440015070298172>"
            event_name = event.replace('_', ' ').title().replace('Role', 'Role').replace('Channel', 'Channel').replace('Ban', 'Ban').replace('Kick', 'Kick').replace('Prune', 'Prune').replace('Webhook Manage', 'Webhook').replace('Bot Add', 'Bot').replace('Server Update', 'Server').replace('Mention Everyone', 'Ping').replace('Emoji', 'Emoji').replace('Member Update', 'Member Role Update')
            description_lines.append(f"{status_icon} **{event_name}**")
        
        status_icon = "<:Enable:1400507483684077598>" if self.selected_options else "<:disabled:1400507479930048512>"
        embed = discord.Embed(
            title="Antinuke Configuration",
            color=0x2f3136,
            description="\n".join(description_lines) + f"\n\n**Executor:** {self.author.mention} (`{self.author.id}`)\n**System Status:** {status_icon}\n\nSelected {len(self.selected_options)}/15 events"
        )
        embed.set_author(name="Security System", icon_url=self.author.display_avatar.url)
        return embed

    @discord.ui.button(label="Enable All Events", style=discord.ButtonStyle.success, custom_id="enable_all")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return
        self.selected_options = ["role_create", "role_delete", "role_update", "channel_create", "channel_delete", "channel_update", "ban", "kick", "prune", "webhook_manage", "bot_add", "server_update", "mention_everyone", "emoji", "member_update"]
        embed = self.get_updated_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.primary, custom_id="confirm")
    async def confirm_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return
        await interaction.response.defer()
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author.id