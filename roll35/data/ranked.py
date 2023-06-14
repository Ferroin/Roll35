# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for ranked item lists.'''

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any, TypeVar, cast

from . import agent
from .classes import ClassesAgent
from .spell import SpellAgent
from .. import types
from ..common import yaml, bad_return, ismapping, rnd, flatten, make_weighted_entry
from ..log import log_call

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence, Iterable, Callable
    from concurrent.futures import Executor

logger = logging.getLogger(__name__)

T = TypeVar('T')


def convert_ranked_item(item: Mapping[str, Any], /) -> types.item.SimpleItem:
    '''Convert a ranked item entry to the appropriate dataclass.'''
    match item:
        case {'spell': _}:
            return types.item.SimpleSpellItem(**item)
        case _:
            return types.item.SimpleItem(**item)


def process_ranked_itemlist(
        items: Mapping[str, Mapping[str, Iterable[types.Item]]],
        /, *,
        typ: Callable[[Any], Any] = lambda x: x,
        xform: Callable[[T], T] = lambda x: x) -> \
        types.RankedItemList:
    '''Process ranked list of weighted values.

       This takes a dict of ranks to dicts of subranks to lists of dicts
       of weighted items, and processes them into the format used by
       our weighted random selection in various data agent modules.'''
    ret: types.RankedItemList = types.R35Map()

    for rank in [x for x in types.Rank if x.value in items]:
        ret[rank] = process_subranked_itemlist(items[rank.value], typ=typ, xform=xform)

    return ret


def process_subranked_itemlist(
        items: Mapping[str, Iterable[types.Item]],
        /, *,
        typ: Callable[[Any], Any] = lambda x: x,
        xform: Callable[[T], T] = lambda x: x) -> \
        types.SubrankedItemList:
    '''Process a subranked list of weighted values.

       This takes a dict of subranks to lists of dicts of weighted items
       and processes them into the format used by our weighted random
       selection in various data agent modules.'''
    ret: types.SubrankedItemList = types.R35Map()

    for subrank in [x for x in types.Subrank if x.value in items]:
        ret[subrank] = types.R35List()

        for item in items[subrank.value]:
            try:
                ret[subrank].append(make_weighted_entry(cast(types.Item, xform(typ(item)))))
            except TypeError:
                raise RuntimeError(f'Failed to process entry for ranked item list: { item }')

    return ret


class RankedAgent(agent.Agent):
    '''Data agent for ranked item lists.'''
    @staticmethod
    def _process_data(data: Mapping | Sequence, /, classes: types.item.ClassMap = dict()) -> agent.AgentData:
        if not ismapping(data):
            raise ValueError('Ranked data must be a mapping')

        return agent.AgentData(
            ranked=process_ranked_itemlist(
                data,
                typ=convert_ranked_item,
                xform=agent.create_spellmult_xform(classes),
            )
        )

    async def load_data_async(self: RankedAgent, pool: Executor, /) -> types.Ret:
        '''Load data for this agent.'''
        if not self._ready.is_set():
            logger.info('Fetching class data.')

            classes = await cast(ClassesAgent, self._ds['classes']).W_classdata_async()

            logger.info(f'Loading { self.name } data.')

            with open(self._ds.src / f'{ self.name }.yaml') as f:
                data = yaml.load(f)

            self._data = await self._process_async(pool, self._process_data, [data, classes])
            logger.info(f'Finished loading { self.name } data.')

            self._ready.set()

        return types.Ret.OK

    @log_call(logger, 'roll random ranked item')
    async def random_async(
            self: RankedAgent,
            /,
            rank: types.Rank | None = None,
            subrank: types.Subrank | None = None,
            *,
            level: int | None = None,
            cls: str | None = None,
            mincost: types.Cost | None = None,
            maxcost: types.Cost | None = None) -> \
            types.item.BaseItem | types.Ret:
        '''Roll a random ranked item, then roll a spell for it if needed.'''
        match level:
            case None:
                item = await super().random_ranked_async(
                    rank=rank,
                    subrank=subrank,
                    mincost=mincost,
                    maxcost=maxcost,
                )
            case int():
                if self._data.ranked is None:
                    return types.Ret.NO_MATCH

                match rank:
                    case None:
                        searchitems: Iterable[types.item.BaseItem] = []

                        for si1 in self._data.ranked.values():
                            for si2 in si1.values():
                                cast(list, searchitems).append(si2)
                    case rank if self._valid_rank(rank):
                        match subrank:
                            case None:
                                searchitems = flatten(self._data.ranked[rank].values())
                            case subrank if self._valid_subrank(rank, subrank):
                                searchitems = self._data.ranked[rank][subrank]
                            case _:
                                raise ValueError(f'Invalid sub-rank for { self.name }: { rank }')
                    case _:
                        raise ValueError(f'Invalid rank for { self.name }: { rank }')

                possible = []

                for i1 in searchitems:
                    match i1:
                        case types.item.SpellItem(spell={'level': int() as l1}) if l1 == level:
                            possible.append(i1)

                match rnd(agent.costfilter(possible, mincost=mincost, maxcost=maxcost)):
                    case types.Ret.NO_MATCH:
                        return types.Ret.NO_MATCH
                    case types.item.BaseItem() as i2:
                        item = i2
                    case ret:
                        logger.warning(bad_return(ret))
                        return types.Ret.FAILED
            case _:
                raise ValueError

        match item:
            case types.Ret.NO_MATCH:
                return types.Ret.NO_MATCH
            case types.item.SpellItem(spell=spell):
                if spell.cls is None and cls is not None:
                    spell.cls = cls

                match await cast(SpellAgent, self._ds['spell']).random_async(**spell.dict()):
                    case types.Ret.NOT_READY:
                        return types.Ret.NOT_READY
                    case (types.Ret.OK, types.item.Spell() as s1):
                        if hasattr(item, 'costmult') and item.costmult is not None and s1.rolled_caster_level is not None:
                            item.cost = item.costmult * s1.rolled_caster_level

                        item.rolled_spell = s1
                        return item
                    case (types.Ret() as r1, msg) if r1 is not types.Ret.OK:
                        logger.warning(f'Failed to roll random spell for item using parameters: { spell }, recieved: { msg }')
                        return r1
                    case r1:
                        logger.error(bad_return(r1))
                        return types.Ret.FAILED
            case types.item.BaseItem() as item:
                return item
            case r2:
                logger.warning(bad_return(r2))
                return types.Ret.FAILED

        # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
        #
        # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
        raise RuntimeError
