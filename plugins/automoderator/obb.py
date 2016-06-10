"""
AutoModerator object class.

Used for running.
"""
import discord

from navalbot.api.commands import CommandContext


class NoSuchItem(Exception): ...


class Action(object):
    """
    Represents an action to run.
    """

    def __init__(self, ctx: CommandContext, doc: dict):
        """
        Defines a new moderation Action.
        """
        self._document = doc

        self._ctx = ctx

        self.items = {"users": [], "channels": [], "permissions": [], "attrs": {}}

        # Parse it out.
        self._parse_action()

    def _parse_action(self):
        """
        Parses the action and creates the appropriate data fields.
        """
        self.action = self._document.get("action")

        # Parse out the items.
        self._items = self._document.get("items", [])

        # Parse them into objects.
        self._parse_items()

        # Parse the permissions.
        self._perms = self._document.get("permissions", [])
        self._parse_permissions()

    def _parse_permissions(self):
        """
        Parse out the permissions.
        """
        if isinstance(self._perms,  int):
            # Integer role, create a new permissions object for it.
            self.items["permissions"] = discord.Permissions(permissions=self._perms)
        elif isinstance(self._perms, list):
            # Get each item, and setattr it.
            self.items["permissions"] = discord.Permissions()
            for perm in self._perms:
                setattr(self.items["permissions"], perm, True)
        else:
            self.items["permissions"] = discord.Permissions.none()

    def _parse_items(self):
        """
        Parses out the items in self._items and loads them.
        """
        for item in self._items:
            # Str items, for example, users.
            if isinstance(item, str):
                # If it begins with an `!`, it's a user.
                if item.startswith("!"):
                    u = self._ctx.get_named_user(item[1:])
                    if not u:
                        raise NoSuchItem(item[1:])
                    self.items["users"].append(u)
                # If it starts with a `#`, it's a channel.
                if item.startswith("#"):
                    assert isinstance(self._ctx.server, discord.Server)
                    # Check for the special case @all.
                    if item == "#@all":
                        for chan in self._ctx.server.channels:
                            self.items["channels"].append(chan)
                    else:
                        chan = discord.utils.get(self._ctx.server.channels, name=item[1:])
                        if not chan:
                            raise NoSuchItem(item[1:])
                        self.items["channels"].append(chan)
            # Dict items, for stuff like create-role.
            elif isinstance(item, dict):
                self.items["attrs"].update(item)

    async def run(self):
        """
        Runs the Automod action.
        """
        users = self.items["users"]
        channels = self.items["channels"]
        attrs = self.items["attrs"]
        if self.action == "mute":
            # Mute the specified users on the specified channels.
            perms = discord.Permissions.text()
            # Give them some perms, like read.
            perms.read_messages = True
            perms.read_message_history = True
            for user in users:
                for chan in channels:
                    assert isinstance(user, discord.User)
                    assert isinstance(chan, discord.Channel)
                    await self._ctx.client.edit_channel_permissions(chan, user, deny=perms)
                    await self._ctx.reply("automod.actions.mute", chan=chan.name, user=user.display_name)
        elif self.action == "clean-perms":
            # Clear special permissions on each channel.
            for user in users:
                for chan in channels:
                    assert isinstance(user, discord.User)
                    assert isinstance(chan, discord.Channel)
                    await self._ctx.client.delete_channel_permissions(chan, user)
                    await self._ctx.reply("automod.actions.clean_perms", chan=chan, user=user.display_name)
        elif self.action == "create-role":
            # Create a new role.
            # Load the attrs from self.items["attrs"]
            name = attrs.get("name", None)
            if not name:
                raise NoSuchItem("Name is not specified in items")
            colour = attrs.get("colour", 0)
            try:
                if isinstance(colour, str):
                    colour = int(colour, 16)
                colour = discord.Colour(colour)
            except ValueError:
                await self._ctx.reply("generic.not_int", val=colour)
                return
            # Create the permission.
            await self._ctx.client.create_role(self._ctx.server, name=name, colour=colour,
                                               hoist=attrs.get("hoist", False), permissions=self.items["permissions"])
            await self._ctx.reply("automod.actions.role_create", serv=self._ctx.server, name=name)
        # The action does not exist.
        else:
            await self._ctx.reply("automod.actions.none", action=self.action)