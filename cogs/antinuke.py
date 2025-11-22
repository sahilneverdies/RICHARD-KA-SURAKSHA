import discord
from discord.ext import commands
import aiosqlite
import asyncio
import time
import datetime
import pytz
from extras.events import EventHandlers
from extras.views import AntinukeView, WhitelistView
from extras.database import DatabaseManager

class WhitelistShowView(discord.ui.View):
    def __init__(self, author, guild_id, db_manager, bot):
        super().__init__(timeout=60)
        self.author = author
        self.guild_id = guild_id
        self.db_manager = db_manager
        self.bot = bot
        self.selected_event = None
        self.message = None
        event_options = [
            discord.SelectOption(label="Anti Role Creation", value="role_create", description="Show users whitelisted for role creation"),
            discord.SelectOption(label="Anti Role Deletion", value="role_delete", description="Show users whitelisted for role deletion"),
            discord.SelectOption(label="Anti Role Update", value="role_update", description="Show users whitelisted for role updates"),
            discord.SelectOption(label="Anti Channel Creation", value="channel_create", description="Show users whitelisted for channel creation"),
            discord.SelectOption(label="Anti Channel Deletion", value="channel_delete", description="Show users whitelisted for channel deletion"),
            discord.SelectOption(label="Anti Channel Update", value="channel_update", description="Show users whitelisted for channel updates"),
            discord.SelectOption(label="Anti Ban", value="ban", description="Show users whitelisted for bans"),
            discord.SelectOption(label="Anti Kick", value="kick", description="Show users whitelisted for kicks"),
            discord.SelectOption(label="Anti Prune", value="prune", description="Show users whitelisted for pruning"),
            discord.SelectOption(label="Anti Webhook", value="webhook_manage", description="Show users whitelisted for webhook management"),
            discord.SelectOption(label="Anti Bot", value="bot_add", description="Show users whitelisted for bot additions"),
            discord.SelectOption(label="Anti Server", value="server_update", description="Show users whitelisted for server updates"),
            discord.SelectOption(label="Anti Ping", value="mention_everyone", description="Show users whitelisted for everyone pings"),
            discord.SelectOption(label="Anti Emoji", value="emoji", description="Show users whitelisted for emoji events"),
            discord.SelectOption(label="Anti Member Role Update", value="member_update", description="Show users whitelisted for member role updates"),
            discord.SelectOption(label="Anti Unban", value="unban", description="Show users whitelisted for unbans")
        ]
        self.event_select = discord.ui.Select(
            placeholder="Select an event to view whitelisted users",
            options=event_options,
            max_values=1
        )
        self.event_select.callback = self.select_callback
        self.add_item(self.event_select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You are not authorized to use this menu.", ephemeral=True)
            return
        self.selected_event = self.event_select.values[0]
        await self.update_whitelist_display(interaction)

    async def update_whitelist_display(self, interaction: discord.Interaction):
        whitelisted_users = await self.db_manager.get_whitelisted_users(self.guild_id)
        event_display_names = {
            "role_create": "Anti Role Creation",
            "role_delete": "Anti Role Deletion",
            "role_update": "Anti Role Update",
            "channel_create": "Anti Channel Creation",
            "channel_delete": "Anti Channel Deletion",
            "channel_update": "Anti Channel Update",
            "ban": "Anti Ban",
            "kick": "Anti Kick",
            "prune": "Anti Prune",
            "webhook_manage": "Anti Webhook",
            "bot_add": "Anti Bot",
            "server_update": "Anti Server",
            "mention_everyone": "Anti Ping",
            "emoji": "Anti Emoji",
            "member_update": "Anti Member Role Update",
            "unban": "Anti Unban"
        }
        filtered_users = []
        serial = 1
        for row in whitelisted_users:
            user_id = row[0]
            raw_permissions = row[1] if len(row) > 1 else ""
            if isinstance(user_id, str) and user_id.isdigit():
                user_id = int(user_id)
            try:
                user_obj = self.bot.get_user(user_id)
            except Exception:
                user_obj = None
            if not user_obj:
                try:
                    user_obj = await self.bot.fetch_user(user_id)
                except Exception:
                    user_obj = None
            if raw_permissions == "all":
                has_permission = True
            else:
                user_perms = raw_permissions.split(",") if raw_permissions else []
                user_perms = [p.strip() for p in user_perms if p.strip()]
                has_permission = self.selected_event in user_perms
            if has_permission:
                mention = user_obj.mention if user_obj else f"{user_id}"
                filtered_users.append(f"`[{serial}.]` | [**{self.bot.get_user(user_id).display_name}**](https://discord.com/users/{user_id}) - `({user_id})`")
                serial += 1
        event_name = event_display_names.get(self.selected_event, self.selected_event)
        if not filtered_users:
            embed = discord.Embed(
                description=f"## Whitelisted Users For {event_name} - {len(filtered_users)}\n\nNo users are whitelisted for this event.",
                color=0x2f3136
            )
        else:
            user_list = "\n".join(filtered_users[:13])
            embed = discord.Embed(
                description=f"## Whitelisted Users For {event_name} - {len(filtered_users)}\n\n{user_list}",
                color=0x2f3136
            )
        current_time = datetime.datetime.now(pytz.timezone('UTC'))
        svr = self.bot.get_guild(self.guild_id)
        embed.set_footer(text=f"{self.bot.user.name} • {current_time.strftime('%B %d, %Y at %I:%M %p')}")
        embed.set_thumbnail(url='' if svr.icon is None else svr.icon.url)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("You are not authorized to use this menu.", ephemeral=True)
            return False
        return True

class AntinukeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_tracking = {}
        self.cooldown_tracker = {}
        self.db_manager = DatabaseManager()
        self.event_handlers = EventHandlers(self)
        self.recovery_queue = asyncio.Queue()
        self.processing_tasks = {}

    @commands.Cog.listener()
    async def on_ready(self):
        await self.db_manager.initialize_database()
        asyncio.create_task(self.process_recovery_queue())

    async def process_recovery_queue(self):
        while True:
            recovery_task = await self.recovery_queue.get()
            await recovery_task()
            self.recovery_queue.task_done()

    async def is_antinuke_enabled(self, guild_id):
        return await self.db_manager.is_antinuke_enabled(guild_id)

    async def is_event_enabled(self, guild_id, event_type):
        return await self.db_manager.is_event_enabled(guild_id, event_type)

    async def is_user_whitelisted(self, guild_id, user_id, permission_type=None):
        return await self.db_manager.is_user_whitelisted(guild_id, user_id, permission_type)

    def check_rate_limit(self, guild_id, event_type, max_attempts=5, time_window=10, cooldown_time=300):
        current_time = datetime.datetime.now()
        self.event_tracking.setdefault(guild_id, {}).setdefault(event_type, []).append(current_time)
        event_history = [t for t in self.event_tracking[guild_id][event_type] if (current_time - t).total_seconds() <= time_window]
        self.event_tracking[guild_id][event_type] = event_history
        if guild_id in self.cooldown_tracker and event_type in self.cooldown_tracker[guild_id]:
            if (current_time - self.cooldown_tracker[guild_id][event_type]).total_seconds() < cooldown_time:
                return False
            del self.cooldown_tracker[guild_id][event_type]
        if len(event_history) > max_attempts:
            self.cooldown_tracker.setdefault(guild_id, {})[event_type] = current_time
            return False
        return True

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.event_handlers.handle_channel_create(channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.event_handlers.handle_channel_delete(channel)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        await self.event_handlers.handle_channel_update(before, after)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.event_handlers.handle_role_create(role)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        await self.event_handlers.handle_role_delete(role)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await self.event_handlers.handle_role_update(before, after)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await self.event_handlers.handle_member_ban(guild, user)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        await self.event_handlers.handle_member_unban(guild, user)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.event_handlers.handle_member_remove(member)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.event_handlers.handle_member_join(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        await self.event_handlers.handle_member_update(before, after)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        await self.event_handlers.handle_guild_update(before, after)

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.event_handlers.handle_message(message)

    @commands.Cog.listener()
    async def on_webhook_update(self, channel):
        await self.event_handlers.handle_webhook_update(channel)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def antinuke(self, ctx, action: str = None):
        if action is None:
            embed = discord.Embed(
                description="Antinuke security system management. Use `antinuke enable` to activate protection or `antinuke disable` to deactivate it.",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)
        if action.lower() == "enable":
            if await self.is_antinuke_enabled(ctx.guild.id):
                embed = discord.Embed(
                    description="Antinuke protection is already enabled for this server.",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                return await ctx.send(embed=embed)
            view = AntinukeView(ctx.author, ctx.guild.id, self.db_manager)
            await view.load_current_events()
            embed = view.get_updated_embed()
            message = await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.selected_options:
                await self.db_manager.enable_antinuke(ctx.guild.id, view.selected_options)
                final_embed = discord.Embed(
                    description=f"Antinuke protection has been activated with {len(view.selected_options)} events enabled.",
                    color=0x2f3136
                )
                final_embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                await message.edit(embed=final_embed, view=None)
            else:
                embed = discord.Embed(
                    description="No events were selected. Antinuke protection remains disabled.",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                await message.edit(embed=embed, view=None)
        elif action.lower() == "disable":
            if not await self.is_antinuke_enabled(ctx.guild.id):
                embed = discord.Embed(
                    description="Antinuke protection is already disabled for this server.",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                return await ctx.send(embed=embed)
            await self.db_manager.disable_antinuke(ctx.guild.id)
            embed = discord.Embed(
                description="Antinuke protection has been deactivated. All events have been reset and security monitoring is now disabled.",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)
        elif action.lower() == "config":
            config_data = await self.db_manager.get_config_data(ctx.guild.id)
            if not config_data:
                embed = discord.Embed(
                    description="Antinuke is not enabled for this server.",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                return await ctx.send(embed=embed)
            is_enabled = config_data['enabled']
            whitelist_count = config_data['whitelist_count']
            enabled_events = config_data['enabled_events']
            webhook_protection = config_data['webhook_protection']
            max_webhooks = config_data['max_webhooks']
            mass_threshold = config_data['mass_threshold']
            event_display = {
                "role_create": "Anti Role Creation",
                "role_delete": "Anti Role Deletion", 
                "role_update": "Anti Role Update",
                "channel_create": "Anti Channel Creation",
                "channel_delete": "Anti Channel Deletion",
                "channel_update": "Anti Channel Update",
                "ban": "Anti Ban",
                "kick": "Anti Kick",
                "prune": "Anti Prune",
                "webhook_manage": "Anti Webhook",
                "bot_add": "Anti Bot",
                "server_update": "Anti Server",
                "mention_everyone": "Anti Ping",
                "emoji": "Anti Emoji",
                "member_update": "Anti Member Role Update",
                "unban": "Anti Unban"
            }
            enabled_list = []
            for event in event_display.keys():
                if event in enabled_events:
                    enabled_list.append(f"<:tick:1380440073526579270> `{event_display[event]}`")
                else:
                    enabled_list.append(f"<:cross:1380440015070298172> `{event_display[event]}`")
            status_text = "Active and Monitoring" if is_enabled else "Inactive"
            embed = discord.Embed(
                description=f"Antinuke Status: {status_text}\n\nWhitelisted Users: {whitelist_count}/13\nEnabled Events: {len(enabled_events)}/16\nResponse Time: Instant detection and action\nWebhook Protection: {'Enabled' if webhook_protection else 'Disabled'}\nMax Webhooks/User: {max_webhooks}\nMass Action Threshold: {mass_threshold}",
                color=0x2f3136
            )
            embed.add_field(
                name="Enabled Protection Events",
                value="\n".join(enabled_list),
                inline=False
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description="Invalid action specified. Use enable, disable, or config.",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def whitelist(self, ctx, action: str = None, user: discord.Member = None):
        if not await self.is_antinuke_enabled(ctx.guild.id):
            embed = discord.Embed(
                description="Antinuke protection must be enabled to use whitelist commands.",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)
        if action is None:
            embed = discord.Embed(
                description="Use whitelist add @user or whitelist remove @user",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            return await ctx.send(embed=embed)
        if action.lower() == "add":
            if not user:
                embed = discord.Embed(
                    description="Specify a user. Example: whitelist add @user",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                return await ctx.send(embed=embed)
            if await self.is_user_whitelisted(ctx.guild.id, user.id):
                embed = discord.Embed(
                    description="This user is already whitelisted.",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                return await ctx.send(embed=embed)
            view = WhitelistView(ctx.author, user, self.db_manager)
            embed = view.get_updated_embed()
            message = await ctx.send(embed=embed, view=view)
            await view.wait()
            if view.selected_options:
                await self.db_manager.add_whitelist_user(ctx.guild.id, user.id, view.selected_options)
                final_embed = discord.Embed(
                    description=f"User whitelisted with {len(view.selected_options)} permissions.",
                    color=0x2f3136
                )
                final_embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                await message.edit(embed=final_embed, view=None)
            else:
                embed = discord.Embed(
                    description="No permissions were selected.",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                await message.edit(embed=embed, view=None)
        elif action.lower() == "remove":
            if not user:
                embed = discord.Embed(
                    description="Specify a user. Example: whitelist remove @user",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                return await ctx.send(embed=embed)
            if not await self.is_user_whitelisted(ctx.guild.id, user.id):
                embed = discord.Embed(
                    description="This user is not whitelisted.",
                    color=0x2f3136
                )
                embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
                return await ctx.send(embed=embed)
            await self.db_manager.remove_whitelist_user(ctx.guild.id, user.id)
            embed = discord.Embed(
                description=f"<:tick:1380440073526579270> {user.mention} removed from whitelist.",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)
        elif action.lower() == "show":
            whitelisted_users = await self.db_manager.get_whitelisted_users(ctx.guild.id)
            view = WhitelistShowView(ctx.author, ctx.guild.id, self.db_manager, self.bot)
            embed = discord.Embed(
                description="Select an event to view whitelisted users",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            view.message = await ctx.send(embed=embed, view=view)
        else:
            embed = discord.Embed(
                description="Invalid action. Use add, remove, or show.",
                color=0x2f3136
            )
            embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx):
        start = time.perf_counter()
        async with aiosqlite.connect("database/antinuke.db") as db:
            db_start = time.perf_counter()
            await db.execute("SELECT 1")
            db_end = time.perf_counter()
        end = time.perf_counter()
        embed = discord.Embed(title="🏓 Pong!", description=f"Bot Latency: `{round(self.bot.latency*1000,2)}ms`\nDatabase Latency: `{round((db_end-db_start)*1000,2)}ms`", color=0x2f3136)
        embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def invite(self, ctx):
        embed = discord.Embed(
            description=f"> [Click To Invite {self.bot.user.name}](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions=8)\n> [Join My Support Server](https://discord.gg/xm3g9cqt)\n> [Visit My Website](https://protonweb.netlify.app/)",
            color=0x2f3136)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx):
        embed = discord.Embed(title="Antinuke Bot Help",
            description=(
                "Antinuke Commands:\n"
                "`antinuke <enable|disable|config>`\n\n"
                "Whitelist Commands:\n"
                "`whitelist add @user`\n"
                "`whitelist remove @user`\n"
                "`whitelist show`\n\n"
                "Other Commands:\n"
                "`ping` - Check latency"
            ),
            color=0x2f3136
        )
        embed.set_author(name="Security System", icon_url=self.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AntinukeSystem(bot))