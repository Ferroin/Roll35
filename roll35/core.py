# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Core commands.'''

import logging

from nextcord.ext import commands

from .cog import Cog

logger = logging.getLogger(__name__)


class Core(Cog):
    def __init__(self, bot, _pool, renderer):
        super().__init__(bot, renderer, logger)

    @commands.command()
    async def ping(self, ctx):
        '''Check if the bot is alive'''
        await ctx.send('pong')
