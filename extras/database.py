import aiosqlite

class DatabaseManager:
    def __init__(self):
        self.db_initialized = False

    async def initialize_database(self):
        if self.db_initialized:
            return
        async with aiosqlite.connect("database/antinuke.db") as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS antinuke_config (guild_id INTEGER PRIMARY KEY, enabled BOOLEAN DEFAULT FALSE, webhook_spam_protection BOOLEAN DEFAULT TRUE, max_webhooks_per_user INTEGER DEFAULT 3, mass_action_threshold INTEGER DEFAULT 5)"
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS antinuke_events (guild_id INTEGER, event_type TEXT, enabled BOOLEAN DEFAULT FALSE, PRIMARY KEY (guild_id, event_type))"
            )
            await db.execute(
                "CREATE TABLE IF NOT EXISTS whitelist_data (guild_id INTEGER, user_id INTEGER, ban BOOLEAN DEFAULT FALSE, kick BOOLEAN DEFAULT FALSE, prune BOOLEAN DEFAULT FALSE, bot_add BOOLEAN DEFAULT FALSE, server_update BOOLEAN DEFAULT FALSE, member_update BOOLEAN DEFAULT FALSE, channel_create BOOLEAN DEFAULT FALSE, channel_delete BOOLEAN DEFAULT FALSE, channel_update BOOLEAN DEFAULT FALSE, role_create BOOLEAN DEFAULT FALSE, role_update BOOLEAN DEFAULT FALSE, role_delete BOOLEAN DEFAULT FALSE, mention_everyone BOOLEAN DEFAULT FALSE, webhook_manage BOOLEAN DEFAULT FALSE, emoji BOOLEAN DEFAULT FALSE, PRIMARY KEY (guild_id, user_id))"
            )
            await db.commit()

            async with db.execute("PRAGMA table_info(whitelist_data)") as cursor:
                columns = await cursor.fetchall()
                column_names = [c[1] for c in columns]
                if "emoji" not in column_names:
                    await db.execute("ALTER TABLE whitelist_data ADD COLUMN emoji BOOLEAN DEFAULT FALSE")
                await db.commit()

        self.db_initialized = True

    async def is_antinuke_enabled(self, guild_id):
        async with aiosqlite.connect("database/antinuke.db") as db:
            async with db.execute("SELECT enabled FROM antinuke_config WHERE guild_id = ?", (guild_id,)) as cursor:
                result = await cursor.fetchone()
                return result and result[0]

    async def is_event_enabled(self, guild_id, event_type):
        async with aiosqlite.connect("database/antinuke.db") as db:
            async with db.execute("SELECT enabled FROM antinuke_events WHERE guild_id = ? AND event_type = ?", (guild_id, event_type)) as cursor:
                result = await cursor.fetchone()
                return result and result[0]
            
    async def reset_events(self, guild_id):
        async with aiosqlite.connect("database/antinuke.db") as db:
            await db.execute("DELETE FROM antinuke_events WHERE guild_id = ?", (guild_id,))
            await db.commit()

    async def is_user_whitelisted(self, guild_id, user_id, permission_type=None):
        async with aiosqlite.connect("database/antinuke.db") as db:
            if permission_type:
                async with db.execute(f"SELECT {permission_type} FROM whitelist_data WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                    result = await cursor.fetchone()
                    return result and result[0]
            async with db.execute("SELECT 1 FROM whitelist_data WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                return await cursor.fetchone() is not None

    async def enable_antinuke(self, guild_id, events):
        async with aiosqlite.connect("database/antinuke.db") as db:
            await db.execute("INSERT OR REPLACE INTO antinuke_config (guild_id, enabled, webhook_spam_protection, max_webhooks_per_user, mass_action_threshold) VALUES (?, ?, ?, ?, ?)", (guild_id, True, True, 3, 5))
            
            for event_type in events:
                await db.execute("INSERT OR REPLACE INTO antinuke_events (guild_id, event_type, enabled) VALUES (?, ?, ?)", (guild_id, event_type, True))
            
            await db.commit()

    async def disable_antinuke(self, guild_id):
        async with aiosqlite.connect("database/antinuke.db") as db:
            await db.execute("INSERT OR REPLACE INTO antinuke_config (guild_id, enabled) VALUES (?, ?)", (guild_id, False))
            await db.execute("DELETE FROM antinuke_events WHERE guild_id = ?", (guild_id,))
            await db.commit()

    async def add_whitelist_user(self, guild_id, user_id, permissions):
        whitelist_data = {event: True for event in permissions}
        
        async with aiosqlite.connect("database/antinuke.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO whitelist_data (guild_id, user_id, ban, kick, prune, bot_add, server_update, member_update, channel_create, channel_delete, channel_update, role_create, role_update, role_delete, mention_everyone, webhook_manage, emoji) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    guild_id, user_id,
                    whitelist_data.get("ban", False),
                    whitelist_data.get("kick", False),
                    whitelist_data.get("prune", False),
                    whitelist_data.get("bot_add", False),
                    whitelist_data.get("server_update", False),
                    whitelist_data.get("member_update", False),
                    whitelist_data.get("channel_create", False),
                    whitelist_data.get("channel_delete", False),
                    whitelist_data.get("channel_update", False),
                    whitelist_data.get("role_create", False),
                    whitelist_data.get("role_update", False),
                    whitelist_data.get("role_delete", False),
                    whitelist_data.get("mention_everyone", False),
                    whitelist_data.get("webhook_manage", False),
                    whitelist_data.get("emoji", False)
                )
            )
            await db.commit()

    async def remove_whitelist_user(self, guild_id, user_id):
        async with aiosqlite.connect("database/antinuke.db") as db:
            await db.execute("DELETE FROM whitelist_data WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            await db.commit()

    async def get_whitelisted_users(self, guild_id):
        async with aiosqlite.connect("database/antinuke.db") as db:
            async with db.execute(
                "SELECT user_id, ban, kick, prune, bot_add, server_update, member_update, channel_create, channel_delete, channel_update, role_create, role_update, role_delete, mention_everyone, webhook_manage, emoji FROM whitelist_data WHERE guild_id = ? LIMIT 13", 
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                
            formatted_rows = []
            for row in rows:
                user_id = row[0]
                permissions = []
                
                if row[1]: permissions.append("ban")
                if row[2]: permissions.append("kick")
                if row[3]: permissions.append("prune")
                if row[4]: permissions.append("bot_add")
                if row[5]: permissions.append("server_update")
                if row[6]: permissions.append("member_update")
                if row[7]: permissions.append("channel_create")
                if row[8]: permissions.append("channel_delete")
                if row[9]: permissions.append("channel_update")
                if row[10]: permissions.append("role_create")
                if row[11]: permissions.append("role_update")
                if row[12]: permissions.append("role_delete")
                if row[13]: permissions.append("mention_everyone")
                if row[14]: permissions.append("webhook_manage")
                if row[15]: permissions.append("emoji")
                
                permissions_str = ",".join(permissions) if permissions else ""
                formatted_rows.append((user_id, permissions_str))
            
            return formatted_rows

    async def get_config_data(self, guild_id):
        async with aiosqlite.connect("database/antinuke.db") as db:
            async with db.execute("SELECT COUNT(*) FROM whitelist_data WHERE guild_id = ?", (guild_id,)) as cursor:
                whitelist_count = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT webhook_spam_protection, max_webhooks_per_user, mass_action_threshold FROM antinuke_config WHERE guild_id = ?", (guild_id,)) as cursor:
                config_data = await cursor.fetchone()
            
            async with db.execute("SELECT event_type FROM antinuke_events WHERE guild_id = ? AND enabled = TRUE", (guild_id,)) as cursor:
                enabled_events = [row[0] for row in await cursor.fetchall()]
            
            is_enabled = await self.is_antinuke_enabled(guild_id)
            webhook_protection = config_data[0] if config_data else True
            max_webhooks = config_data[1] if config_data else 3
            mass_threshold = config_data[2] if config_data else 5
            
            return {
                'enabled': is_enabled,
                'whitelist_count': whitelist_count,
                'enabled_events': enabled_events,
                'webhook_protection': webhook_protection,
                'max_webhooks': max_webhooks,
                'mass_threshold': mass_threshold
            }