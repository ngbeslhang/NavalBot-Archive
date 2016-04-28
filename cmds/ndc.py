"""
=================================

This file is part of NavalBot.
Copyright (C) 2016 Isaac Dickinson
Copyright (C) 2016 Nils Theres

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>

=================================
"""

# Owner commands.
import asyncio
import importlib
import logging
import re
import sys

import discord

import cmds
import util

getter = re.compile(r'`{1,3}(.*?)`{1,3}')

loop = asyncio.get_event_loop()

logger = logging.getLogger("NavalBot")


@cmds.command("reload")
@util.owner
@util.enforce_args(1, "You must pick a file to reload.")
async def reload_f(client: discord.Client, message: discord.Message, args: list):
    """
    Reloads a module in the bot.
    """
    mod = args[0]
    if mod not in sys.modules:
        if 'cmds.' + mod not in sys.modules:
            await client.send_message(message.channel, ":x: Module is not loaded.")
            return
        else:
            mod = 'cmds.' + mod
    # Reload using importlib.
    new_mod = importlib.reload(sys.modules[mod])
    # Update sys.modules
    sys.modules[mod] = new_mod
    await client.send_message(message.channel, ":heavy_check_mark: Reloaded module.")


@cmds.command("reloadall")
@util.owner
async def reload_all(client: discord.Client, message: discord.Message):
    """
    Reloads all modules.
    """
    # Reload util
    importlib.reload(sys.modules["util"])
    for mod in sys.modules:
        if mod.startswith("cmds."):
            # Reload it.
            logger.info("Reloading module: {}".format(mod))
            importlib.reload(sys.modules[mod])
            logger.info("Reloaded module.")

    await client.send_message(message.channel, ":heavy_check_mark: Reloaded all.")


@cmds.command("reloadvoice")
@util.owner
async def reload_voice(client: discord.Client, message: discord.Message):
    """
    Reloads new voice.
    """
    if not client.user.bot:
        return

    for mod in sys.modules:
        if mod.startswith("voice."):
            # Reload it.
            logger.info("Reloading module: {}".format(mod))
            importlib.reload(sys.modules[mod])
            logger.info("Reloaded module.")

    await client.send_message(message.channel, ":heavy_check_mark: Reloaded voice.")


@cmds.command("sql")
@util.owner
async def sql(client: discord.Client, message: discord.Message):
    sql_cmd = getter.findall(message.content)
    if not sql_cmd:
        return
    util.cursor.execute(sql_cmd[0])
    await client.send_message(message.channel, "`{}`".format(util.cursor.fetchall()))


@cmds.command("py")
@util.owner
async def py(client: discord.Client, message: discord.Message):
    match = getter.findall(message.content)
    if not match:
        return
    else:
        result = eval(match[0])
        await client.send_message(message.channel, "```{}```".format(result))


@cmds.command("rget")
@util.owner
async def redis_get(client: discord.Client, message: discord.Message):
    key = getter.findall(message.content)
    if not key:
        return
    pool = await util.get_pool()
    async with pool.get() as conn:
        k = await conn.get(key[0])
        if k:
            k = k.decode()
        await client.send_message(message.channel, "`{}`".format(k))