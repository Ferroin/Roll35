# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for compound item lists.'''

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any, cast

import aiofiles

from . import agent
from .classes import ClassesAgent
from .spell import SpellAgent
from .. import types
from ..common import bad_return, flatten, ismapping, make_weighted_entry, rnd, yaml
from ..log import log_call, log_call_async

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from concurrent.futures import Executor

logger = logging.getLogger(__name__)


def process_compound_itemlist(
        items: Iterable[Mapping[str, Any]],
        classes: types.item.ClassMap,
        extra_classes: set[str],
        /) -> \
        types.CompoundItemList:
    '''Process a compound list of weighted values.

       Each list entry must be a dict with keys coresponding to the
       possible values for `roll35.types.Rank` with each such key bearing
       a weight to use for the entry when rolling a random item of the
       corresponding rank.'''
    ret: types.CompoundItemList = types.R35Map()
    valid_classes = {x for x in classes} | extra_classes

    for rank in types.Rank:
        ilist: types.CompoundItemSublist = types.R35List()

        for item in items:
            match item:
                case {'spell': _}:
                    try:
                        e1 = types.item.CompoundSpellItem(**item)
                    except (ValueError, TypeError) as e:
                        raise ValueError(f'Invalid compound item entry: {e}: {item}.')

                    if e1.spell.cls is not None and e1.spell.cls not in valid_classes:
                        raise ValueError(f'Unrecognized class name {e1.spell.cls} in compound item entry for {e1.name}.')

                    if getattr(e1, rank.value):
                        e1.weight = getattr(e1, rank.value)
                        ilist.append(make_weighted_entry(
                            e1,
                            costmult_handler=agent.create_spellmult_xform(classes),
                        ))
                case _:
                    e2 = types.item.CompoundItem(**item)

                    if getattr(e2, rank.value):
                        e2.weight = getattr(e2, rank.value)
                        ilist.append(make_weighted_entry(
                            e2,
                        ))

        ret[rank] = ilist

    return ret


class CompoundAgent(agent.Agent):
    '''Basic data agent for compound item lists.'''
    @staticmethod
    def _process_data(data: Mapping | Sequence, /, classes: types.item.ClassMap = dict(), extra_classes: set[str] = set()) -> agent.AgentData:
        if ismapping(data):
            raise ValueError('Compound Spell data must be a sequence')

        return agent.AgentData(
            compound=process_compound_itemlist(data, classes, extra_classes)
        )

    def load_data(self: CompoundAgent, /) -> types.Ret:
        '''Load data for this agent.'''
        if not self.ready:
            logger.info('Fetching class data.')

            classes = cast(ClassesAgent, self._ds['classes']).classdata()
            extra_classes = cast(SpellAgent, self._ds['spell']).EXTRA_CLASS_NAMES

            if classes == types.Ret.NOT_READY:
                raise RuntimeError('Class data is not ready.')

            logger.info(f'Loading {self.name} data.')

            with open(self._ds.src / f'{self.name}.yaml') as f:
                data = yaml.load(f)

            self._data = self._process_data(data, classes, extra_classes)
            logger.info(f'Finished loading {self.name} data.')

            self.ready = True

        return types.Ret.OK

    async def load_data_async(self: CompoundAgent, pool: Executor, /) -> types.Ret:
        '''Load data for this agent.'''
        if not self.ready:
            logger.info('Fetching class data.')

            classes = await cast(ClassesAgent, self._ds['classes']).W_classdata_async()
            extra_classes = cast(SpellAgent, self._ds['spell']).EXTRA_CLASS_NAMES

            logger.info(f'Loading {self.name} data.')

            async with aiofiles.open(self._ds.src / f'{self.name}.yaml') as f:
                data = await f.read()

            self._data = await self._process_async(pool, self._process_data, [yaml.load(data), classes, extra_classes])
            logger.info(f'Finished loading {self.name} data.')

            self.ready = True

        return types.Ret.OK

    def __handle_level_search(
            self: CompoundAgent,
            /,
            rank: types.Rank | None = None,
            *,
            level: int,
            mincost: types.Cost = agent.DEFAULT_MINCOST,
            maxcost: types.Cost = agent.DEFAULT_MAXCOST) -> \
            types.CompoundItem | types.item.CompoundSpellItem | types.Ret:
        if self._data.compound is None:
            return types.Ret.NO_MATCH

        match rank:
            case None:
                searchitems: Iterable[types.CompoundItem] = \
                    flatten(cast(Sequence[Sequence[types.CompoundItem]], self._data.compound.values()))
            case rank if self._valid_rank(rank):
                searchitems = cast(Sequence[types.CompoundItem], self._data.compound[rank])
            case _:
                raise ValueError(f'Invalid rank for {self.name}: {rank}')

        possible = []

        for i1 in searchitems:
            match i1:
                case types.item.CompoundSpellItem(spell={'level': int() as l1}) if l1 == level:
                    possible.append(i1)

        items = cast(Sequence[types.item.CompoundSpellItem], agent.costfilter(possible, mincost=mincost, maxcost=maxcost))

        match rnd(items):
            case types.Ret.NO_MATCH:
                return types.Ret.NO_MATCH
            case i2:
                return i2

    def __handle_item(
            self: CompoundAgent,
            /,
            item: types.CompoundItem | types.item.CompoundSpellItem | types.Ret,
            spell: types.Result[types.item.Spell] | types.Ret | None) -> \
            types.CompoundItem | types.item.CompoundSpellItem | types.Ret:
        match item:
            case types.Ret.NO_MATCH:
                return types.Ret.NO_MATCH
            case types.item.CompoundSpellItem():
                match spell:
                    case types.Ret.NOT_READY:
                        return types.Ret.NOT_READY
                    case (types.Ret.OK, types.item.Spell() as s1):
                        if hasattr(item, 'costmult') and item.costmult is not None and s1.rolled_caster_level is not None:
                            item.cost = item.costmult * s1.rolled_caster_level

                        item.rolled_spell = s1
                        return item
                    case (types.Ret() as r1, msg) if r1 is not types.Ret.OK:
                        logger.warning(f'Failed to roll random spell for item using parameters: {spell}, recieved: {msg}')
                        return r1
                    case ret:
                        logger.error(bad_return(ret))
                        return types.Ret.FAILED
            case types.CompoundItem() as item:
                return item
            case ret:
                logger.warning(bad_return(ret))
                return types.Ret.FAILED

        # The below line should never actually be run, as the above match clauses are (theoretically) exhaustive.
        #
        # However, mypy thinks this function is missing a return statement, and this line convinces it otherwise.
        raise RuntimeError

    @log_call(logger, 'roll compound item')
    def random(
        self: CompoundAgent,
        /,
        rank: types.Rank | None = None,
        *,
        cls: str | None = None,
        level: int | None = None,
        mincost: types.Cost = agent.DEFAULT_MINCOST,
        maxcost: types.Cost = agent.DEFAULT_MAXCOST,
    ) -> types.CompoundItem | types.item.CompoundSpellItem | types.Ret:
        '''Roll a random item, then roll a spell for it if needed.'''
        match level:
            case None:
                item: types.CompoundItem | types.item.CompoundSpellItem | types.Ret = cast(types.CompoundItem, super().random_compound(
                    rank=rank,
                    mincost=mincost,
                    maxcost=maxcost,
                ))
            case int():
                item = self.__handle_level_search(rank=rank, level=level, mincost=mincost, maxcost=maxcost)
            case _:
                raise ValueError

        spell = None

        if isinstance(item, types.item.CompoundSpellItem):
            spellparams = item.spell

            if spellparams.cls is None and cls is not None:
                spellparams.cls = cls

            spell = cast(SpellAgent, self._ds['spell']).random(**spellparams.dict())

        return self.__handle_item(item, spell)

    @log_call_async(logger, 'roll compound item')
    async def random_async(
        self: CompoundAgent,
        /,
        rank: types.Rank | None = None,
        *,
        cls: str | None = None,
        level: int | None = None,
        mincost: types.Cost = agent.DEFAULT_MINCOST,
        maxcost: types.Cost = agent.DEFAULT_MAXCOST,
    ) -> types.CompoundItem | types.item.CompoundSpellItem | types.Ret:
        '''Roll a random item, then roll a spell for it if needed.'''
        match level:
            case None:
                item: types.CompoundItem | types.item.CompoundSpellItem | types.Ret = cast(types.CompoundItem, await super().random_compound_async(
                    rank=rank,
                    mincost=mincost,
                    maxcost=maxcost,
                ))
            case int():
                item = self.__handle_level_search(rank=rank, level=level, mincost=mincost, maxcost=maxcost)
            case _:
                raise ValueError

        spell = None

        if isinstance(item, types.item.CompoundSpellItem):
            spellparams = item.spell

            if spellparams.cls is None and cls is not None:
                spellparams.cls = cls

            spell = await cast(SpellAgent, self._ds['spell']).random_async(**spellparams.dict())

        return self.__handle_item(item, spell)
