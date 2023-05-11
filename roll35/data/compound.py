# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for compound item lists.'''

from __future__ import annotations

import logging

from typing import Any, TYPE_CHECKING, cast

from . import agent
from . import constants
from .classes import ClassMap, ClassesAgent
from .spell import SpellAgent
from .. import types
from ..common import yaml, bad_return, ismapping, rnd, flatten
from ..log import log_call_async

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Iterable
    from concurrent.futures import Executor

logger = logging.getLogger(__name__)


def convert_compound_item(item: Mapping[str, Any], /) -> types.item.CompoundItem:
    '''Convert a compound item entry to the appropriate dataclass.'''
    match item:
        case {'spell': _}:
            return types.item.CompoundSpellItem(**item)
        case _:
            return types.item.CompoundItem(**item)


class CompoundAgent(agent.Agent):
    '''Basic data agent for compound item lists.'''
    @staticmethod
    def _process_data(data: Mapping | Sequence, /, classes: ClassMap = dict()) -> agent.AgentData:
        if ismapping(data):
            raise ValueError('Compound Spell data must be a sequence')

        return agent.AgentData(
            compound=agent.process_compound_itemlist(
                data,
                typ=convert_compound_item,
                xform=agent.create_spellmult_xform(classes),
            )
        )

    async def load_data(self: CompoundAgent, pool: Executor, /) -> types.Ret:
        '''Load data for this agent.'''
        if not self._ready.is_set():
            logger.info('Fetching class data.')

            classes = await cast(ClassesAgent, self._ds['classes']).W_classdata()

            logger.info(f'Loading { self.name } data.')

            with open(constants.DATA_ROOT / f'{ self.name }.yaml') as f:
                data = yaml.load(f)

            self._data = await self._process_async(pool, self._process_data, [data, classes])
            logger.info(f'Finished loading { self.name } data.')

            self._ready.set()

        return types.Ret.OK

    @log_call_async(logger, 'roll compound item')
    async def random(
            self: CompoundAgent,
            /,
            rank: types.Rank | None = None,
            *,
            cls: str | None = None,
            level: int | None = None,
            mincost: types.item.Cost | None = None,
            maxcost: types.item.Cost | None = None) -> \
            types.Item | types.Ret:
        '''Roll a random item, then roll a spell for it if needed.'''
        match level:
            case None:
                item = await super().random_compound(
                    rank=rank,
                    mincost=mincost,
                    maxcost=maxcost,
                )
            case int():
                if self._data.compound is None:
                    return types.Ret.NO_MATCH

                match rank:
                    case None:
                        searchitems: Iterable[types.WeightedEntry] = flatten(self._data.compound.values())
                    case rank if self._valid_rank(rank):
                        searchitems = self._data.compound[rank]
                    case _:
                        raise ValueError(f'Invalid rank for { self.name }: { rank }')

                possible = []

                for i1 in searchitems:
                    match i1:
                        case types.WeightedEntry(value=types.item.SpellItem(spell={'level': int() as l1})) if l1 == level:
                            possible.append(i1)

                items = agent.costfilter(possible, mincost=mincost, maxcost=maxcost)

                match rnd(items):
                    case types.Ret.NO_MATCH:
                        return types.Ret.NO_MATCH
                    case i2:
                        item = i2
            case _:
                raise ValueError

        match item:
            case types.Ret.NO_MATCH:
                return types.Ret.NO_MATCH
            case types.item.SpellItem(spell=spell):
                if ('cls' not in spell or spell['cls'] is None) and cls is not None:
                    spell['cls'] = cls

                match await cast(SpellAgent, self._ds['spell']).random(**spell):
                    case types.Ret.NOT_READY:
                        return types.Ret.NOT_READY
                    case (types.Ret.OK, types.item.SpellEntry() as s1):
                        if hasattr(item, 'costmult') and item.costmult is not None:
                            item.cost = item.costmult * s1.caster_level

                        item.rolled_spell = s1
                        return item
                    case (types.Ret() as r1, msg) if r1 is not types.Ret.OK:
                        logger.warning(f'Failed to roll random spell for item using parameters: { spell }, recieved: { msg }')
                        return r1
                    case ret:
                        logger.error(bad_return(ret))
                        return types.Ret.FAILED
            case types.BaseItem() as item:
                return item
            case ret:
                logger.warning(bad_return(ret))
                return types.Ret.FAILED

        # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
        #
        # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
        raise RuntimeError
