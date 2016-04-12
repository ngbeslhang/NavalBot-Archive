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
import os

import discord

import cmds
import util
from bot import get_file
from exceptions import CommandError


@cmds.command("mute")
@util.with_permission("Admin", "Bot Commander")
async def mute(client: discord.Client, message: discord.Message):
    """
    Mutes a user. This user must be @mentioned.
    You must a have `Muted` role installed on the server.
    """
    muterole = discord.utils.get(message.server.roles, name='Muted')

    if not muterole:
        raise CommandError('No Muted role created')

    if len(message.mentions) > 0:
        try:
            await client.add_roles(message.mentions[0], muterole)
            await client.server_voice_state(message.mentions[0], mute=True)
            await client.send_message(message.channel,
                                      'User {} got muted by {}'.format(message.mentions[0], message.author))
        except discord.Forbidden:
            await client.send_message('Not enough permissions to mute user {}'.format(message.mentions[0].name))
            raise CommandError('Not enough permissions to mute user : {}'.format(message.mentions[0].name))
    else:
        await client.send_message(message.channel, "Usage: ?mute @UserName")


@cmds.command("unmute")
@util.with_permission("Admin", "Bot Commander")
async def unmute(client: discord.Client, message: discord.Message):
    """
    Unmutes a user. This user must be @mentioned.
    You must a have `Muted` role installed on the server.
    """
    muterole = discord.utils.get(message.server.roles, name='Muted')

    if not muterole:
        raise CommandError('No Muted role created')
    if len(message.mentions) > 0:
        try:
            await client.remove_roles(message.mentions[0], muterole)
            await client.server_voice_state(message.mentions[0], mute=False)
            await client.send_message(message.channel,
                                      'User {} got unmuted by {}'.format(message.mentions[0], message.author))
        except discord.Forbidden:
            await client.send_message('Not enough permissions to unmute user {}'.format(message.mentions[0].name))
            raise CommandError('Not enough permissions to unmute user : {}'.format(message.mentions[0].name))
    else:
        await client.send_message(message.channel, "Usage: ?unmute @UserName")


@cmds.command("ban")
@util.with_permission("Admin", "Bot Commander")
async def ban(client: discord.Client, message: discord.Message):
    """
    Bans a user from the server.
    """
    try:
        await client.ban(member=message.mentions[0]) \
            if len(message.mentions) > 0 \
            else client.send_message(message.channel, content=":question: You must provide a user to ban.")
        await client.send_message(message.channel,
                                  '{} got banned by {}!'.format(message.mentions[0], message.author.name))
    except (discord.Forbidden, IndexError) as banerror:
        print('[ERROR]:', banerror)


@cmds.command("unban")
@util.with_permission("Admin", "Bot Commander")
async def unban(client: discord.Client, message: discord.Message):
    """
    nah
    """


@cmds.command("kick")
@util.with_permission("Admin", "Bot Commander")
async def kick(client: discord.Client, message: discord.Message):
    """
    Kicks a user from the server.
    """
    try:
        await client.kick(member=message.mentions[0])
        await client.send_message(message.channel,
                                  '{} got kicked by {}!'.format(message.mentions[0], message.author.name))
    except (discord.Forbidden, IndexError) as kickerror:
        print('[Error]', kickerror)


@cmds.command("delete")
@util.with_permission("Admin", "Bot Commander")
async def delete(client: discord.Client, message: discord.Message, count=None):
    """
    Prunes a certain number of messages from the server.
    """
    try:
        count = int(' '.join(message.content.split(" ")[1:]))
    except ValueError:
        await client.send_message(message.channel, "This is not a number")
    async for msg in client.logs_from(message.channel, count + 1):
        await client.delete_message(msg)
    if count == 1:
        await client.send_message(message.channel, '**{} message deleted by {}**💣'.format(count, message.author))
    else:
        await client.send_message(message.channel, '**{} messages deleted by {}** 💣'.format(count, message.author))


@cmds.command("invite")
async def invite(client: discord.Client, message: discord.Message):
    """
    Accepts an invite to another server.
    """
    try:
        invite = message.content.split(" ")[1]
    except IndexError:
        await client.send_message(message.channel, "Usage: ?invite [link]")
        return

    await client.accept_invite(invite)
    await client.send_message(message.channel, "Joined server specified.")


@cmds.command("avatar")
@util.only(cmds.RCE_IDS)
@util.enforce_args(1, error_msg='You need to provide a link')
async def avatar(client: discord.Client, message: discord.Message, args: list):
    """
    Changes the avatar of the bot.
    You must provide a valid url, pointing to a jpeg or png file.
    """

    file = args[0]
    try:
        await get_file((client, message), url=file, name='avatar.jpg')
        fp = open(os.path.join(os.getcwd(), "files", "avatar.jpg"), 'rb')
        await client.edit_profile(avatar=fp.read())
        await client.send_message(message.channel, "Avatar got changed!")
    except (ValueError, discord.errors.InvalidArgument):
        await client.send_message(message.channel, "This command only supports jpeg or png files!")

"""
@cmds.command("createmuted")
@util.with_permission('Admin')
async def createmuted(client: discord.Client, message: discord.Message):
    await client.create_role(server=message.server, role=discord.Role.name('Test'), permissions=discord.Permissions(
        permissions=discord.Permissions.send_messages == 0))
    await   client.send_message(message.channel, "something happened, idk what")
"""