# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Base class for all of our cogs.'''

from __future__ import annotations

import logging

from nextcord.ext import commands

from typing import NoReturn, TYPE_CHECKING

if TYPE_CHECKING:
    from concurrent.futures import Executor

    from .item import Item, SpellEntry
    from .retcode import Result
    from ..data import DataSet
    from ..renderer import Renderer

logger = logging.getLogger(__name__)


class R35Cog(commands.Cog):
    '''nextcord.ext.commands.Cog subclass for our local behavior.'''
    def __init__(self: R35Cog, /, pool: Executor, dataset: DataSet, renderer: Renderer) -> None:
        super().__init__()
        self.pool = pool
        self.ds = dataset
        self.renderer = renderer

    async def render(self: R35Cog, /, item: Item | SpellEntry) -> Result[str]:
        '''Render an item using the renderer passed on initialization.'''
        return await self.renderer.render(item)

    async def cog_before_invoke(self: R35Cog, /, ctx: commands.Context) -> None:
        '''Flag the bot as typing to indicate that it’s processing the command.

           Also handles logging of commands when log level is set to debug.'''
        await ctx.trigger_typing()

        assert ctx.command is not None

        logger.debug(
            f'Invoking { ctx.command.name } from message { ctx.message.content }.'
        )

    async def cog_command_error(self: R35Cog, /, ctx: commands.Context, err: Exception) -> NoReturn:
        '''Explicitly notify the user about errors encountered while running a command.'''
        await ctx.send(
            'Error encountered while processing command:\n' + repr(err)
        )
        raise
