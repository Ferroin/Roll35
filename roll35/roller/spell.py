# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Functions for rolling random spells.'''

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any, cast

from .. import types
from ..common import bad_return, ret_async
from ..data.spell import SpellAgent
from ..log import log_call_async

if TYPE_CHECKING:
    from collections.abc import Awaitable, Mapping, Sequence

    from ..data import DataSet

    SResult = types.Result[types.Spell]

NOT_READY = 'Spell data is not yet available, please try again later.'

MAX_COUNT = 32

logger = logging.getLogger(__name__)


def roll_many_async(ds: DataSet, /, count: int, args: Mapping[str, Any]) -> Sequence[Awaitable[SResult]]:
    '''Roll a number of spells.

       Returns a list of coroutines that can be awaited to get the
       requested spells.'''
    if not ds.ready:
        return [ret_async((types.Ret.NOT_READY, NOT_READY))]

    if count > MAX_COUNT:
        return [ret_async((types.Ret.LIMITED, f'Too many spells requested, no more than {MAX_COUNT} may be rolled at a time.'))]

    coros = []

    for i in range(0, count):
        coros.append(roll_spell_async(ds, args))

    return coros


@log_call_async(logger, 'roll spell')
async def roll_spell_async(ds: DataSet, /, args: Mapping[str, Any]) -> SResult:
    '''Roll a random spell with the given parameters.'''
    match await cast(SpellAgent, ds['spell']).random_async(**args):
        case (types.Ret.OK, types.Spell() as spell):
            return (types.Ret.OK, spell)
        case (types.Ret.NOT_READY, str() as msg):
            return (types.Ret.NOT_READY, msg)
        case types.Ret.NOT_READY:
            return (types.Ret.NOT_READY, NOT_READY)
        case ret:
            logger.warning(bad_return(ret))
            return (types.Ret.FAILED, 'Unknown internal error.')

    # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
    #
    # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
    raise RuntimeError
