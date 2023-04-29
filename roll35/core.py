# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Core commands.'''

import platform

import nextcord

from nextcord.ext import commands

from .cog import Cog
from .common import VERSION


class Core(Cog):
    @commands.command()
    async def ping(self, ctx):
        '''Check if the bot is alive'''
        await ctx.send('pong')

    @commands.command()
    async def version(self, ctx):
        '''Check the version of the bot'''

        await ctx.send(
            f'\nRoll35 version: { VERSION[0] }.{ VERSION[1] }.{ VERSION[2] }\n' +
            f'Running on Python { platform.python_version() } ({ platform.python_implementation() })\n' +
            f'Using Nextcord { nextcord.__version__ }'
        )
