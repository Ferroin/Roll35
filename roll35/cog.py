# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Base class for all of our cogs.'''

import logging

from nextcord.ext import commands

logger = logging.getLogger(__name__)


class Cog(commands.Cog):
    def __init__(self, bot, dataset, renderer):
        self.bot = bot
        self.ds = dataset
        self.renderer = renderer

    async def render(self, item):
        return await self.renderer.render(item)

    async def cog_before_invoke(self, ctx):
        await ctx.trigger_typing()

        logger.debug(
            f'Invoking { ctx.command.name } from message { ctx.message.content }.'
        )

    async def cog_command_error(self, ctx, err):
        await ctx.send(
            'Error encountered while processing command:\n' + repr(err)
        )
        raise
