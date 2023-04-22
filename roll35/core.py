# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Core commands.'''

import logging
import os
import platform

import nextcord

from nextcord.ext import commands

from .cog import Cog
from .common import VERSION

logger = logging.getLogger(__name__)


class Core(Cog):
    def __init__(self, bot, _pool, renderer):
        super().__init__(bot, renderer, logger)

    @commands.command()
    async def ping(self, ctx):
        '''Check if the bot is alive'''
        await ctx.send('pong')

    @commands.command()
    async def version(self, ctx):
        '''Check the version of the bot'''
        if '_R35_CONTAINER_BUILD_DATE' in os.environ:
            build_date = os.environ['_R35_CONTAINER_BUILD_DATE']
        else:
            build_date = 'unknown'

        await ctx.send(
            f'\nRoll35 version: { VERSION[0] }.{ VERSION[1] }.{ VERSION[2] }\n' +
            f'Image build date: { build_date }\n' +
            f'Running on Python { platform.python_version() } ({ platform.python_implementation() })\n' +
            f'Using Nextcord { nextcord.__version__ }'
        )
