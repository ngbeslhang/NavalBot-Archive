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

import asyncio
import datetime
import functools
import os
import random

from dateutil.parser import parse

import discord
import praw
import psutil
import pyowm
from pyowm.webapi25.weather import Weather
from pyowm.webapi25.location import Location
import urbandict
import pytz
from google import search

from navalbot.api import db, util
from navalbot.api.commands import command
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.api.contexts import CommandContext

VERSION = "1.0.0"

loop = asyncio.get_event_loop()

r = praw.Reddit(user_agent='NavalBot/6.x for Discord')


@command("choice", "choose", argcount="?")
async def choice(ctx: CommandContext):
    """
    Makes that hard choice for you.
    """
    # Choose a random argument from the list.
    chosen = random.choice(ctx.args)
    await ctx.reply("fun.chosen", choice=chosen)


def _get_google(f):
    return list(f())[0]


@command("google", argcount="?")
async def google(ctx: CommandContext):
    """
    Searches google for the top two results for the search.
    """
    userinput = ' '.join(ctx.args)
    f = functools.partial(search, userinput, stop=1)
    f2 = functools.partial(_get_google, f)
    l = await util.with_threading(f2)
    await ctx.client.send_message(ctx.message.channel, l)


def _get_weather(api_key, userinput):
    owm = pyowm.OWM(api_key, version='2.5')
    observation = owm.weather_at_place(userinput)
    return observation


@command("weather", argcount="?", argerror=":x: You must specify a village/town/city/settlement to query!")
async def weather(ctx: CommandContext):
    """
    Displays the weather of a specified place.
    """
    api_key = await db.get_key("owm_key")
    if not api_key:
        await ctx.reply("fun.weather.bad_api_key")
        return
    userinput = ' '.join(ctx.args)
    observation = await util.with_threading(functools.partial(_get_weather, api_key, userinput))
    if not observation:
        await ctx.reply("fun.weather.no_such_place", place=userinput)
        return

    # Load out the weather.
    weather = observation.get_weather()
    assert isinstance(weather, Weather)

    place = observation.get_location()
    assert isinstance(place, Location)

    place_name = place.get_name()
    country = place.get_country()

    # Load the status.
    status = weather.get_status()
    extended_status = weather.get_detailed_status()
    temperature = weather.get_temperature("celsius")['temp']
    humidity = weather.get_humidity()
    wind = weather.get_wind()['speed']

    # Pick an emoji.
    if 'rain' in status.lower():
        emoji = ":cloud_rain:"
    elif 'clear' in status.lower():
        emoji = ":sunny:"
    else:
        emoji = ":cloud:"

    # First, send the generic result.
    await ctx.reply("fun.weather.result", emoji=emoji, place=(place_name, country),
                    temperature=temperature, humidity=humidity, wind=wind, status=extended_status)

    if 'rain' in status.lower():
        # Send rain information.
        rain = weather.get_rain().get("1h", 0)
        await ctx.reply("fun.weather.rain", rain=rain)


@command("commands", "info")
async def commands(ctx: CommandContext):
    """
    Gives a link for information about the bot.
    """
    await ctx.reply("fun.commands")


@command("whois", argcount=1)
async def whois(ctx: CommandContext):
    """
    Displays information about the user specified.
    """
    user = ctx.get_user()

    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    # Get the roles.
    s_roles = sorted(user.roles, key=lambda role: role.position)
    # Remove the @everyone mention
    n_roles = []
    for r in s_roles:
        assert isinstance(r, discord.Role)
        if not r.is_everyone:
            n_roles.append(r)
    roles = ', '.join(r.name for r in n_roles)

    await ctx.reply("fun.whois.response", author=user, roles=roles)


@command("uptime")
async def uptime(ctx: CommandContext):
    """
    Gives the uptime of the bot.
    """
    upt = datetime.datetime.now() - util.startup
    s = upt.total_seconds()
    formatted = util.format_timedelta(s, ctx.locale["fun.uptime.time_fmt"])
    await ctx.reply("fun.uptime.response", time=formatted, pid=os.getpid())


@command("stats")
async def stats(ctx: CommandContext):
    """
    Displays statistics about the currently running bot.
    """
    server_count = len(ctx.client.servers)
    msgcount = util.msgcount
    voice_clients = len(ctx.client.voice_clients)
    streams = sum([1 for proc in psutil.process_iter() if proc.name() == "ffmpeg"])
    # Memory stats
    used_memory = psutil.Process().memory_info().rss
    used_memory = round(used_memory / 1024 / 1024, 2)
    tasks = len(asyncio.Task.all_tasks())
    if hasattr(ctx.client, "shard_id") and ctx.client.shard_id is not None:
        shardm = ctx.locale["fun.stats.shard"].format(shard_id=ctx.client.shard_id + 1,
                                                      shard_count=ctx.client.shard_count) + "\n"
    else:
        shardm = ""
    await ctx.reply("fun.stats.response",
                    shardm=shardm, servcount=server_count, msgcount=msgcount, vcount=voice_clients,
                    scount=streams, memcount=used_memory, tasks=tasks)


def _get_urban(get):
    define = urbandict.define(get)[0]
    return define['word'], define['def'], define['example']


@command("urban", argcount="?", argerror=":x: You must provide a word or phrase.")
async def urban(ctx: CommandContext):
    """
    Defines a word using urban dictionary.
    """
    word, definition, example = await util.with_threading(functools.partial(_get_urban, ' '.join(ctx.args)))
    await ctx.reply("fun.urban", search=word, definition=definition, example=example)


def _get_sr_data(arg):
    subreddit = r.get_subreddit(arg)
    if not subreddit or subreddit.over18:
        return
    submissions = list(subreddit.get_hot(limit=30))
    # shuffle
    random.shuffle(submissions)
    sub = submissions[0]
    return sub.url


@command("sr", "subreddit", argcount=1, argerror=":x: You must provide a subreddit.")
async def subreddit(ctx: CommandContext):
    """
    Fetches random post from subreddit's front page.
    """
    sr_link = await util.with_threading(functools.partial(_get_sr_data, ctx.args[0]))
    if not sr_link:
        await ctx.reply("fun.sr.no_sr")
        return
    await ctx.client.send_message(ctx.message.channel, sr_link)


@command("fullwidth", argcount="?", argerror=":x: You must provide at least one word to fullwidth.")
async def aesthetic(ctx: CommandContext):
    """
    ﻿Ｆｕｌｌｗｉｄｔｈｓ  ｓｏｍｅ  ｔｅｘｔ．
    """
    final_c = ""
    pre_c = ' '.join(ctx.args)
    for char in pre_c:
        if not ord(char) in range(33, 127):
            final_c += char
            continue
        # Add 65248 to the ord() value to get the fullwidth counterpart.
        final_c += chr(ord(char) + 65248)
    await ctx.client.send_message(ctx.message.channel, final_c)


@command("remind", "remindme", argcount="?")
async def remindme(ctx: CommandContext):
    """
    Remind you to do stuff
    """

    async def _remind_task(time: int, s: str):
        await asyncio.sleep(time)
        await ctx.reply("fun.reminder", mention=ctx.author.mention, message=s)

    if len(ctx.args) < 2:
        await ctx.reply("fun.reminder.no_args")
        return

    try:
        time = int(ctx.args[0])
    except ValueError:
        await ctx.reply("generic.not_int")
        return

    loop.create_task(_remind_task(time, ' '.join(ctx.args[1:])))
    await ctx.reply("fun.reminder.reminding")


@command("tz", argcount="+")
async def timezone(ctx: CommandContext):
    """
    Checks the current time in the time zone specified.
    """
    try:
        timezone = ctx.args[0]
    except IndexError:
        timezone = "UTC"

    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        await ctx.reply("fun.tz.unknown", timezone=timezone)
        return

    curr = datetime.datetime.now(tz=tz)
    ts = curr.strftime("%Y-%m-%d %H:%M:%S %z")
    await ctx.reply("fun.tz.result", t=ts)


@command("servinfo")
async def get_server_info(ctx: CommandContext):
    """
    Gets information about the server.
    """
    created_time = ctx.server.created_at.strftime("%Y-%m-%d %H:%M:%S %z")
    await ctx.reply("fun.servinfo",
                    server=ctx.server, channels=len(ctx.server.channels),
                    created=created_time)


@command("timetravel", roles={NavalRole.ADMIN}, argcount="+")
async def timetravel(ctx: CommandContext):
    """
    Time-travel to the past.
    """
    if not ctx.args:
        i = ctx.client.logs_from(ctx.channel, after=ctx.channel, limit=1)
    else:
        i = ctx.client.logs_from(ctx.channel, after=parse(ctx.args[0]), limit=1)
    msg = []
    async for m in i:
        msg.append(m)

    if not msg:
        await ctx.reply("fun.timetravel.future")
        return

    msg = msg[0]
    try:
        await ctx.client.pin_message(msg)
    except discord.Forbidden:
        await ctx.reply("fun.timetravel.cannot_pin")
        return
    await ctx.send(msg.id)


@command("game", owner=True, argcount="?")
async def game(ctx: CommandContext):
    await ctx.client.change_status(discord.Game(name=' '.join(ctx.args)))

    await ctx.send(":heavy_check_mark: Changed game to `{}`.".format(' '.join(ctx.args)))


@command("gamestream", owner=True, argcount=2)
async def changestream(ctx: CommandContext):
    await ctx.client.change_status(discord.Game(name=ctx.args[0], url=ctx.args[1], type=1))

    await ctx.send(":heavy_check_mark: Set bot as streaming.")
