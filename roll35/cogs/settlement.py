# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cog for rolling items for settlements.'''

from __future__ import annotations

import logging

from nextcord.ext import commands

from .. import types
from ..roller.settlement import roll_settlement_async

logger = logging.getLogger(__name__)


class Settlement(types.R35Cog):
    '''Roll35 cog for handling settlements.'''
    async def __settlement(self: Settlement, ctx: commands.Context, /, population: int) -> None:
        try:
            pop = int(population)
        except ValueError:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        if pop < 1:
            await ctx.send('Population value must be an integer greater than 0.')
            return

        match await roll_settlement_async(pop, self.pool, self.ds, self.renderer):
            case (types.Ret.OK, str() as msg):
                await ctx.send(msg)
                return
            case (types.Ret() as ret, str() as msg) if ret is not types.Ret.OK:
                await ctx.send(msg)
                return

        # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
        #
        # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
        raise RuntimeError

    @commands.command()  # type: ignore
    async def settlement(self, ctx, population: int, /):
        '''Roll magic items for a settlement with the given population.'''
        await self.__settlement(ctx, population)
