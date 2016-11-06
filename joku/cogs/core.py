"""
Core commands.
"""
import inspect

import aiohttp
import asyncio
import discord
import json
from discord.ext import commands
from discord.ext.commands import Command, CheckFailure
from discord.ext.commands import Context
import psutil
from discord.ext.commands.bot import _default_help_command

from joku.bot import Jokusoramame
from joku.checks import is_owner
from joku.redis import with_redis_cooldown


class Core(object):
    """
    Core command class.
    """

    def __init__(self, bot: Jokusoramame):
        self.bot = bot

        self._is_loaded = False

    async def ready(self):
        if self.bot.shard_id != 0:
            return

        if self._is_loaded:
            return

        self._is_loaded = True

        # Start the Discord Bots stats uploader.
        with aiohttp.ClientSession() as sess:
            while True:
                try:
                    token = self.bot.manager.config.get("dbots_token", None)
                    if not token:
                        self.bot.logger.error("Cannot get token.")
                        return

                    # Make a POST request.
                    headers = {
                        "Authorization": token,
                        "User-Agent": "Jokusoramame - Powered by Python 3",
                        "X-Fuck-Meew0": "true",
                        "Content-Type": "application/json"
                    }
                    body = {
                        "server_count": str(sum(1 for server in self.bot.manager.get_all_servers()))
                    }

                    url = "https://bots.discord.pw/api/bots/{}/stats".format(self.bot.user.id)

                    async with sess.post(url, headers=headers, data=json.dumps(body)) as r:
                        if r.status != 200:
                            self.bot.logger.error("Failed to update server count.")
                            self.bot.logger.error(await r.text())
                        else:
                            self.bot.logger.info("Updated server count on bots.discord.pw.")
                except:
                    self.bot.logger.exception()
                finally:
                    await asyncio.sleep(15)

    def can_run_recursive(self, ctx, command: Command):
        # Check if the command has a parent.
        if command.parent is not None:
            rec = self.can_run_recursive(ctx, command.parent)
            if not rec:
                return False

        try:
            can_run = command.can_run(ctx)
        except CheckFailure:
            return False
        else:
            return can_run

    @commands.command(pass_context=True)
    @commands.check(is_owner)
    async def changename(self, ctx: Context, *, name: str):
        """
        Changes the current username of the bot.

        This command is only usable by the owner.
        """
        await self.bot.edit_profile(username=name)
        await self.bot.say(":heavy_check_mark: Changed username.")

    @commands.command(pass_context=True)
    async def info(self, ctx):
        """
        Shows botto info.
        """
        await ctx.bot.say(":exclamation: **See <https://github.com/SunDwarf/Jokusoramame>, "
                          "or join the server at https://discord.gg/uQwVat8.**")

    @commands.command(pass_context=True)
    async def invite(self, ctx):
        invite = discord.utils.oauth_url(ctx.bot.app_id)
        await ctx.bot.say("**To invite the bot to your server, use this link: {}**".format(invite))

    @commands.command(pass_context=True)
    async def stats(self, ctx):
        """
        Shows stats about the bot.
        """
        current_process = psutil.Process()

        tmp = {
            "shards": ctx.bot.manager.max_shards,
            "servers": sum(1 for _ in ctx.bot.manager.get_all_servers()),
            "members": sum(1 for _ in ctx.bot.manager.get_all_members()),
            "unique_members": ctx.bot.manager.unique_member_count,
            "channels": sum(1 for _ in ctx.bot.manager.get_all_channels()),
            "shard": ctx.bot.shard_id,
            "memory": (current_process.memory_info().rss / 1024 // 1024)
        }

        await ctx.bot.say("Currently connected to `{servers}` servers, "
                          "with `{channels}` channels "
                          "and `{members}` members (`{unique_members}` unique) "
                          "across `{shards}` shards.\n"
                          "Currently using **{memory}MB** of memory\n\n"
                          "This is shard ID **{shard}**.".format(**tmp))

    @commands.command(pass_context=True)
    async def help(self, ctx, *, command: str = None):
        """
        Help command.
        """
        prefix = ctx.prefix

        if command is None:
            # List the commands.
            base = "**Commands:**\nUse `{}help <command>` for more information about each command.\n\n".format(prefix)
            for n, (name, cls) in enumerate(ctx.bot.cogs.items()):
                # Increment N, so we start at 1 index instead of 0.
                n += 1

                cmds = []

                # Get a list of commands on the cog.
                members = inspect.getmembers(cls)
                for cname, m in members:
                    if isinstance(m, Command):
                        # Check if the author can run the command.
                        try:
                            if self.can_run_recursive(ctx, m):
                                cmds.append("`" + m.name + "`")
                        except CheckFailure:
                            pass

                base += "**{}. {}: ** {}\n".format(n, name, ' '.join(cmds) if cmds else "`No commands available to "
                                                                                        "you.`")

            await ctx.bot.say(base)
        else:
            # Use the default help command.
            await _default_help_command(ctx, *command.split(" "))


def setup(bot: Jokusoramame):
    bot.add_cog(Core(bot))
