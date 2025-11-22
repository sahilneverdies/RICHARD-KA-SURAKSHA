import discord
from discord.ext import commands
import json
import traceback
import sys

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_error_message(self, ctx, description):
        try:
            embed = discord.Embed(description=description, color=0x2f3136)
            await ctx.send(embed=embed)
            return True
        except discord.Forbidden:
            try:
                embed = discord.Embed(
                    description=f"I don't have permission to send messages in {ctx.channel.mention}. Please check my permissions.",
                    color=0x2f3136
                )
                await ctx.author.send(embed=embed)
            except discord.Forbidden:
                pass
            return False

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
            
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
                
        ignored = (commands.CommandNotFound,)
        error = getattr(error, 'original', error)
        
        if isinstance(error, ignored):
            return
            
        if isinstance(error, commands.DisabledCommand):
            await self.send_error_message(ctx, f"**{ctx.command}** has been disabled.")
            
        elif isinstance(error, commands.NoPrivateMessage):
            await self.send_error_message(ctx, "You can't use this command in DMs.")
            
        elif isinstance(error, commands.BadArgument):
            await self.send_error_message(ctx, str(error))
            
        elif isinstance(error, commands.NSFWChannelRequired):
            await self.send_error_message(ctx, "This command can only be used in NSFW channels.")
            
        elif isinstance(error, commands.CommandOnCooldown):
            await self.send_error_message(ctx, f"Command is on cooldown. Try again in **{error.retry_after:.2f} seconds**.")
            
        elif isinstance(error, commands.MissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]
            if len(missing) > 1:
                fmt = ", ".join(missing[:-1]) + " and " + missing[-1]
            else:
                fmt = missing[0]
            await self.send_error_message(ctx, f"You need `{fmt}` permission(s) to use **{ctx.command.name}**.")
            
        elif isinstance(error, commands.BotMissingPermissions):
            missing = [
                perm.replace("_", " ").replace("guild", "server").title()
                for perm in error.missing_permissions
            ]
            if len(missing) > 1:
                fmt = ", ".join(missing[:-1]) + " and " + missing[-1]
            else:
                fmt = missing[0]
            await self.send_error_message(ctx, f"I need `{fmt}` permission(s) to run **{ctx.command.name}**.")
            
        elif isinstance(error, commands.NotOwner):
            await self.send_error_message(ctx, "You must be the bot owner to use this command.")
            
        elif isinstance(error, discord.Forbidden):
            await self.send_error_message(ctx, "I don't have permission to perform this action.")
            
        elif isinstance(error, commands.CheckFailure):
            await self.send_error_message(ctx, "You don't have permission to use this command.")
            
        elif isinstance(error, commands.MissingRequiredArgument):
            await self.send_error_message(ctx, f"Missing required argument: `{error.param.name}`")
            
        else:
            await self.send_error_message(ctx, "An unexpected error occurred while executing the command.")
            error_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))