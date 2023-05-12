# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

from __future__ import annotations

import platform

import nextcord

from nextcord.ext import commands

from ..types import R35Cog
from ..common import VERSION


class Core(R35Cog):
    '''Roll35 core bot commands.'''
    async def _ping(self: Core, ctx: commands.Context, /) -> None:
        await ctx.send('pong')

    @commands.command()  # type: ignore
    async def ping(self, ctx, /):
        '''Check if the bot is alive'''
        await self._ping(ctx)

    async def _version(self: Core, ctx: commands.Context, /) -> None:
        await ctx.send(
            f'\nRoll35 version: { VERSION[0] }.{ VERSION[1] }.{ VERSION[2] }\n' +
            f'Running on Python { platform.python_version() } ({ platform.python_implementation() })\n' +
            f'Using Nextcord { nextcord.__version__ }'
        )

    @commands.command()  # type: ignore
    async def version(self, ctx, /):
        '''Check the version of the bot'''
        await self._version(ctx)
