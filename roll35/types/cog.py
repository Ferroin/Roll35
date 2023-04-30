# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Base class for all of our cogs.'''

import logging

from nextcord.ext import commands

logger = logging.getLogger(__name__)


class R35Cog(commands.Cog):
    '''nextcord.ext.commands.Cog subclass for our local behavior.'''
    def __init__(self, bot, dataset, renderer):
        self.bot = bot
        self.ds = dataset
        self.renderer = renderer

    async def render(self, item):
        '''Render an item using the renderer passed on initialization.'''
        return await self.renderer.render(item)

    async def cog_before_invoke(self, ctx):
        '''Flag the bot as typing to indicate that it’s processing the command.

           Also handles logging of commands when log level is set to debug.'''
        await ctx.trigger_typing()

        logger.debug(
            f'Invoking { ctx.command.name } from message { ctx.message.content }.'
        )

    async def cog_command_error(self, ctx, err):
        '''Explicitly notify the user about errors encountered while running a command.'''
        await ctx.send(
            'Error encountered while processing command:\n' + repr(err)
        )
        raise
