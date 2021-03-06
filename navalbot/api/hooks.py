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

# Hooks file.
# This allows adding hooks to `on_message`, and generic events.
import logging
import types
import typing

import discord

from navalbot.api.botcls import NavalClient
from navalbot.api.contexts import EventContext

logger = logging.getLogger("NavalBot")


def register_hook_class(cls):
    """
    Register a class as a hook class.

    This will recieve a dispatch on EVERY event.
    """
    client = NavalClient.get_navalbot()
    client.register_hook_class(cls)
    return cls


def on_message(func: typing.Callable[[EventContext], None]) -> types.FunctionType:
    """
    Registers a hook to be ran every message.
    """

    return on_event("on_message")(func)


def on_generic_event(func: typing.Callable[[EventContext], None]) -> types.FunctionType:
    """
    Registers a hook to be ran on every event.
    """

    return on_event("on_recv")(func)


def on_event(name: str, err_func=None):
    """
    Registers a hook to be run on a any event you specify.

    You can optionally provide an err function.
    In the event of an error, this function is called with the error object.
    """

    def _inner(func: typing.Callable[[EventContext], None]):
        try:
            instance = NavalClient._instance
            assert isinstance(instance, NavalClient)
        except (AssertionError, AttributeError):
            logger.critical("Attempted to register on_message for function `{}` before bot is created."
                            .format(func.__name__))
            return

        if name not in instance.hooks:
            instance.hooks[name] = {}

        async def __event_wrapper(ctx: EventContext):
            try:
                await func(ctx)  # Await the hook, wrapped inside a try.
            except Exception as e:
                if err_func:
                    reraise = await err_func(ctx, e)
                else:
                    reraise = True
                # Re-raise the error if we need to.
                if reraise:
                    raise e

        __event_wrapper.__name__ = func.__name__

        # Use func.__name__ as the key.
        # This prevents multiple messages on a reload.
        instance.hooks[name][func.__name__] = __event_wrapper
        logger.info("Registered hook for `{}` -> `{}`".format(name, func.__name__))

        return func

    return _inner
