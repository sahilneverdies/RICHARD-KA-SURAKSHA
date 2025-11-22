import discord
import datetime
import pytz

class EventHandlers:
    def __init__(self, antinuke_system):
        self.antinuke = antinuke_system

    async def get_audit_entry(self, guild, action_type, target_id=None):
        if not guild.me.guild_permissions.view_audit_log:
            return None
        async for entry in guild.audit_logs(action=action_type, limit=1):
            utc_now = datetime.datetime.now(pytz.utc)
            time_diff = (utc_now - entry.created_at).total_seconds() * 1000
            if time_diff >= 3600000:
                return None
            if target_id is None or getattr(entry.target, 'id', None) == target_id:
                return entry
        return None

    async def execute_safety_action(self, guild, user, action_reason):
        if guild.me.guild_permissions.ban_members:
            await guild.ban(user, reason=action_reason)
            return True
        return False

    async def check_mass_action(self, guild_id, event_type):
        current_time = datetime.datetime.now()
        self.antinuke.event_tracking.setdefault(guild_id, {}).setdefault(f"mass_{event_type}", []).append(current_time)
        event_history = [t for t in self.antinuke.event_tracking[guild_id][f"mass_{event_type}"] if (current_time - t).total_seconds() <= 30]
        self.antinuke.event_tracking[guild_id][f"mass_{event_type}"] = event_history
        return len(event_history) >= 5

    async def revert_channel_creation(self, channel, user):
        if not self.antinuke.check_rate_limit(channel.guild.id, "channel_create", 6, 10, 300):
            return
        if await self.check_mass_action(channel.guild.id, "channel_create"):
            return
        if channel.guild.me.guild_permissions.manage_channels:
            await channel.delete(reason="Mass creation recovery")
        await self.execute_safety_action(channel.guild, user, "Channel creation without authorization")

    async def revert_channel_deletion(self, channel, user):
        if await self.check_mass_action(channel.guild.id, "channel_delete"):
            return
        if channel.guild.me.guild_permissions.manage_channels:
            if isinstance(channel, discord.TextChannel):
                await channel.clone(reason="Mass deletion recovery")
            elif isinstance(channel, discord.VoiceChannel):
                await channel.clone(reason="Mass deletion recovery")
            elif isinstance(channel, discord.CategoryChannel):
                await channel.clone(reason="Mass deletion recovery")
        await self.execute_safety_action(channel.guild, user, "Channel deletion without authorization")

    async def revert_channel_update(self, before, after, user):
        if await self.check_mass_action(before.guild.id, "channel_update"):
            return
        if before.guild.me.guild_permissions.manage_channels:
            if isinstance(before, discord.TextChannel):
                await after.edit(
                    name=before.name,
                    topic=before.topic,
                    nsfw=before.nsfw,
                    position=before.position,
                    slowmode_delay=before.slowmode_delay,
                    reason="Channel modification reversion"
                )
            elif isinstance(before, discord.VoiceChannel):
                await after.edit(
                    name=before.name,
                    position=before.position,
                    bitrate=before.bitrate,
                    user_limit=before.user_limit,
                    rtc_region=before.rtc_region,
                    reason="Channel modification reversion"
                )
            elif isinstance(before, discord.CategoryChannel):
                await after.edit(
                    name=before.name,
                    position=before.position,
                    reason="Channel modification reversion"
                )
        await self.execute_safety_action(after.guild, user, "Channel modification without authorization")

    async def revert_role_creation(self, role, user):
        if await self.check_mass_action(role.guild.id, "role_create"):
            return
        if role.guild.me.guild_permissions.manage_roles:
            await role.delete(reason="Mass creation recovery")
        await self.execute_safety_action(role.guild, user, "Role creation without authorization")

    async def revert_role_deletion(self, role, user):
        if await self.check_mass_action(role.guild.id, "role_delete"):
            return
        if role.guild.me.guild_permissions.manage_roles:
            await role.guild.create_role(
                name=role.name,
                permissions=role.permissions,
                color=role.color,
                hoist=role.hoist,
                mentionable=role.mentionable,
                reason="Mass deletion recovery"
            )
        await self.execute_safety_action(role.guild, user, "Role deletion without authorization")

    async def revert_role_update(self, before, after, user):
        if await self.check_mass_action(before.guild.id, "role_update"):
            return
        if before.guild.me.guild_permissions.manage_roles:
            await after.edit(
                name=before.name,
                permissions=before.permissions,
                color=before.color,
                hoist=before.hoist,
                mentionable=before.mentionable,
                reason="Role modification reversion"
            )
        await self.execute_safety_action(after.guild, user, "Role modification without authorization")

    async def revert_ban_action(self, guild, banned_user, executor):
        if guild.me.guild_permissions.ban_members:
            await guild.unban(banned_user, reason="Ban reversal by security system")
        await self.execute_safety_action(guild, executor, "Member ban without authorization")

    async def revert_kick_action(self, guild, executor):
        await self.execute_safety_action(guild, executor, "Member kick without authorization")

    async def revert_bot_addition(self, guild, bot_user, inviter):
        if guild.me.guild_permissions.kick_members:
            await guild.kick(bot_user, reason="Unauthorized bot removal")
        await self.execute_safety_action(guild, inviter, "Bot addition without authorization")

    async def revert_member_update(self, member, executor, added_role):
        if member.guild.me.guild_permissions.manage_roles:
            await member.remove_roles(added_role, reason="Unauthorized role assignment reversion")
        await self.execute_safety_action(member.guild, executor, "Member role modification without authorization")
        
    async def revert_unban_action(self, guild, unbanned_user, executor):
        if guild.me.guild_permissions.ban_members:
            await guild.ban(unbanned_user, reason="Unban reversal by security system")
        await self.execute_safety_action(guild, executor, "Member unban without authorization")

    async def restore_server_modification(self, previous_state, current_state, responsible_user):
        modification_made = False
        if current_state.me.guild_permissions.manage_guild:
            if previous_state.name != current_state.name:
                await current_state.edit(name=previous_state.name)
                modification_made = True
            if previous_state.icon != current_state.icon:
                await current_state.edit(icon=previous_state.icon)
                modification_made = True
            if previous_state.banner != current_state.banner:
                await current_state.edit(banner=previous_state.banner)
                modification_made = True
            if previous_state.splash != current_state.splash:
                await current_state.edit(splash=previous_state.splash)
                modification_made = True
            if previous_state.description != current_state.description:
                await current_state.edit(description=previous_state.description)
                modification_made = True
            if previous_state.afk_channel != current_state.afk_channel:
                await current_state.edit(afk_channel=previous_state.afk_channel)
                modification_made = True
            if previous_state.afk_timeout != current_state.afk_timeout:
                await current_state.edit(afk_timeout=previous_state.afk_timeout)
                modification_made = True
            if previous_state.system_channel != current_state.system_channel:
                await current_state.edit(system_channel=previous_state.system_channel)
                modification_made = True
        if modification_made:
            await self.execute_safety_action(current_state, responsible_user, "Unauthorized server modification")

    async def handle_mention_abuse(self, message):
        if message.guild.me.guild_permissions.manage_messages:
            await message.delete()
        return True

    async def revert_webhook_actions(self, guild, executor, webhook_target):
        if webhook_target and guild.me.guild_permissions.manage_webhooks:
            await webhook_target.delete(reason="Webhook action reversion")
        await self.execute_safety_action(guild, executor, "Webhook management without authorization")

    async def handle_member_unban(self, guild, user):
        if not await self.antinuke.is_antinuke_enabled(guild.id) or not await self.antinuke.is_event_enabled(guild.id, "unban"):
            return
        audit_entry = await self.get_audit_entry(guild, discord.AuditLogAction.unban, user.id)
        if not audit_entry:
            return
        executor = audit_entry.user
        if executor.id in [guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(guild.id, executor.id, "unban"):
            return
        await self.revert_unban_action(guild, user, executor)

    async def handle_channel_create(self, channel):
        if not await self.antinuke.is_antinuke_enabled(channel.guild.id) or not await self.antinuke.is_event_enabled(channel.guild.id, "channel_create"):
            return
        audit_entry = await self.get_audit_entry(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        if not audit_entry:
            return
        user = audit_entry.user
        if user.id in [channel.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(channel.guild.id, user.id, "channel_create"):
            return
        await self.revert_channel_creation(channel, user)

    async def handle_channel_delete(self, channel):
        if not await self.antinuke.is_antinuke_enabled(channel.guild.id) or not await self.antinuke.is_event_enabled(channel.guild.id, "channel_delete"):
            return
        audit_entry = await self.get_audit_entry(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        if not audit_entry:
            return
        user = audit_entry.user
        if user.id in [channel.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(channel.guild.id, user.id, "channel_delete"):
            return
        await self.revert_channel_deletion(channel, user)

    async def handle_channel_update(self, before, after):
        if not await self.antinuke.is_antinuke_enabled(before.guild.id) or not await self.antinuke.is_event_enabled(before.guild.id, "channel_update"):
            return
        audit_entry = await self.get_audit_entry(before.guild, discord.AuditLogAction.channel_update, after.id)
        if not audit_entry:
            return
        user = audit_entry.user
        if user.id in [before.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(before.guild.id, user.id, "channel_update"):
            return
        await self.revert_channel_update(before, after, user)

    async def handle_role_create(self, role):
        if not await self.antinuke.is_antinuke_enabled(role.guild.id) or not await self.antinuke.is_event_enabled(role.guild.id, "role_create"):
            return
        audit_entry = await self.get_audit_entry(role.guild, discord.AuditLogAction.role_create)
        if not audit_entry:
            return
        user = audit_entry.user
        if user.id in [role.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(role.guild.id, user.id, "role_create"):
            return
        await self.revert_role_creation(role, user)

    async def handle_role_delete(self, role):
        if not await self.antinuke.is_antinuke_enabled(role.guild.id) or not await self.antinuke.is_event_enabled(role.guild.id, "role_delete"):
            return
        audit_entry = await self.get_audit_entry(role.guild, discord.AuditLogAction.role_delete)
        if not audit_entry:
            return
        user = audit_entry.user
        if user.id in [role.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(role.guild.id, user.id, "role_delete"):
            return
        await self.revert_role_deletion(role, user)

    async def handle_role_update(self, before, after):
        if not await self.antinuke.is_antinuke_enabled(before.guild.id) or not await self.antinuke.is_event_enabled(before.guild.id, "role_update"):
            return
        audit_entry = await self.get_audit_entry(before.guild, discord.AuditLogAction.role_update, after.id)
        if not audit_entry:
            return
        user = audit_entry.user
        if user.id in [before.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(before.guild.id, user.id, "role_update"):
            return
        await self.revert_role_update(before, after, user)

    async def handle_member_ban(self, guild, user):
        if not await self.antinuke.is_antinuke_enabled(guild.id) or not await self.antinuke.is_event_enabled(guild.id, "ban"):
            return
        audit_entry = await self.get_audit_entry(guild, discord.AuditLogAction.ban, user.id)
        if not audit_entry:
            return
        executor = audit_entry.user
        if executor.id in [guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(guild.id, executor.id, "ban"):
            return
        await self.revert_ban_action(guild, user, executor)

    async def handle_member_remove(self, member):
        if not await self.antinuke.is_antinuke_enabled(member.guild.id):
            return
        audit_entry = await self.get_audit_entry(member.guild, discord.AuditLogAction.kick, member.id)
        if audit_entry:
            if not await self.antinuke.is_event_enabled(member.guild.id, "kick"):
                return
            executor = audit_entry.user
            if executor.id not in [member.guild.owner_id, self.antinuke.bot.user.id] and not await self.antinuke.is_user_whitelisted(member.guild.id, executor.id, "kick"):
                await self.revert_kick_action(member.guild, executor)
                return
        prune_audit = await self.get_audit_entry(member.guild, discord.AuditLogAction.member_prune)
        if prune_audit:
            if not await self.antinuke.is_event_enabled(member.guild.id, "prune"):
                return
            executor = prune_audit.user
            if executor.id not in [member.guild.owner_id, self.antinuke.bot.user.id] and not await self.antinuke.is_user_whitelisted(member.guild.id, executor.id, "prune"):
                await self.execute_safety_action(member.guild, executor, "Member pruning without authorization")

    async def handle_member_join(self, member):
        if not member.bot or not await self.antinuke.is_antinuke_enabled(member.guild.id) or not await self.antinuke.is_event_enabled(member.guild.id, "bot_add"):
            return
        audit_entry = await self.get_audit_entry(member.guild, discord.AuditLogAction.bot_add, member.id)
        if not audit_entry:
            return
        inviter = audit_entry.user
        if inviter.id in [member.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(member.guild.id, inviter.id, "bot_add"):
            return
        await self.revert_bot_addition(member.guild, member, inviter)

    async def handle_member_update(self, before, after):
        if not await self.antinuke.is_antinuke_enabled(before.guild.id) or not await self.antinuke.is_event_enabled(before.guild.id, "member_update"):
            return
        added_roles = [role for role in after.roles if role not in before.roles]
        if not added_roles:
            return
        dangerous_roles = []
        for role in added_roles:
            if any([
                role.permissions.ban_members,
                role.permissions.administrator,
                role.permissions.manage_guild,
                role.permissions.manage_channels,
                role.permissions.manage_roles,
                role.permissions.mention_everyone,
                role.permissions.manage_webhooks
            ]):
                dangerous_roles.append(role)
        if not dangerous_roles:
            return
        audit_entry = await self.get_audit_entry(before.guild, discord.AuditLogAction.member_role_update, after.id)
        if not audit_entry:
            return
        executor = audit_entry.user
        if executor.id in [before.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(before.guild.id, executor.id, "member_update"):
            return
        for dangerous_role in dangerous_roles:
            await self.revert_member_update(after, executor, dangerous_role)

    async def handle_guild_update(self, before, after):
        if not await self.antinuke.is_antinuke_enabled(before.id) or not await self.antinuke.is_event_enabled(before.id, "server_update"):
            return
        audit_entry = await self.get_audit_entry(before, discord.AuditLogAction.guild_update)
        if not audit_entry:
            return
        executor = audit_entry.user
        if executor.id in [before.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(before.id, executor.id, "server_update"):
            return
        await self.restore_server_modification(before, after, executor)

    async def handle_message(self, message):
        if (not message.guild or not message.mention_everyone or 
            not await self.antinuke.is_antinuke_enabled(message.guild.id) or not await self.antinuke.is_event_enabled(message.guild.id, "mention_everyone")):
            return
        if message.author.bot and message.author.id != self.antinuke.bot.user.id:
            await self.handle_mention_abuse(message)
            return
        if message.author.id in [message.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(message.guild.id, message.author.id, "mention_everyone"):
            return
        if not self.antinuke.check_rate_limit(message.guild.id, "mention_abuse", 5, 10, 300):
            return
        await self.handle_mention_abuse(message)

    async def handle_webhook_update(self, channel):
        if not await self.antinuke.is_antinuke_enabled(channel.guild.id) or not await self.antinuke.is_event_enabled(channel.guild.id, "webhook_manage"):
            return
        audit_entry = await self.get_audit_entry(channel.guild, discord.AuditLogAction.webhook_update, channel.id)
        if not audit_entry:
            return
        executor = audit_entry.user
        if executor.id in [channel.guild.owner_id, self.antinuke.bot.user.id] or await self.antinuke.is_user_whitelisted(channel.guild.id, executor.id, "webhook_manage"):
            return
        await self.revert_webhook_actions(channel.guild, executor, audit_entry.target)