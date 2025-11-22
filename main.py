import os
import discord, asyncio, sys, jishaku
from discord.ext import commands
from discord.gateway import DiscordWebSocket

async def identify(self):
    payload = {
        'op': self.IDENTIFY,
        'd': {
            'token': self.token,
            'properties': {
                '$os': sys.platform,
                '$browser': 'Discord Android',
                '$device': 'Discord Android',
                '$referrer': '',
                '$referring_domain': ''
            },
            'compress': True,
            'large_threshold': 250,
            'v': 3
        }
    }
    if self.shard_id is not None and self.shard_count is not None:
        payload['d']['shard'] = [self.shard_id, self.shard_count]
    state = self._connection
    if state._activity is not None or state._status is not None:
        payload['d']['presence'] = {
            'status': state._status,
            'game': state._activity,
            'since': 0,
            'afk': False
        }
    if state._intents is not None:
        payload['d']['intents'] = state._intents.value
    await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
    await self.send_as_json(payload)

DiscordWebSocket.identify = identify

os.system("clear")

intents = discord.Intents.all()
OWNER = [1094102183399669821]

bot = commands.Bot(command_prefix="$", intents=intents, owner_ids=OWNER, help_command=None)
bot.remove_command("help")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f'Connected to {len(bot.guilds)} servers')
    await bot.change_presence(activity=discord.CustomActivity(name=f"🔐 Protecting {len(bot.guilds)} servers from nukes"))

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    bot_mentions = [f'<@{bot.user.id}>', f'<@!{bot.user.id}>', bot.user.name.lower()]
    if any(mention in message.content.lower() for mention in bot_mentions):
        embed = discord.Embed(
            description=(
                f"👋 Hello {message.author.mention}!\n\n"
                f"**My prefix is:** `$`\n\n"
                f"Use `$help` to see all commands\n"
            ),
            color=0x2f3136,
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=bot.user.name, icon_url=bot.user.display_avatar.url)
        embed.set_footer(text="Stay protected!")
        try:
            await message.channel.send(embed=embed)
        except:
            pass
    await bot.process_commands(message)
    
async def main():
    await bot.load_extension("jishaku")
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            extension = file[:-3]
            try:
                await bot.load_extension(f"cogs.{extension}")
                print(f"Loaded extension: {extension}")
            except Exception as e:
                print(f"Failed to load extension {extension}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
   