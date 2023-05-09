# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for ranked item lists.'''

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any, cast

from . import agent
from . import constants
from .classes import ClassMap, ClassesAgent
from .spell import SpellAgent
from .. import types
from ..common import yaml, bad_return, ismapping
from ..log import log_call_async

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from concurrent.futures import Executor

logger = logging.getLogger(__name__)


def convert_ranked_item(item: Mapping[str, Any]) -> types.item.SimpleItem:
    '''Convert a ranked item entry to the appropriate dataclass.'''
    match item:
        case {'spell': _}:
            return types.item.SimpleSpellItem(**item)
        case _:
            return types.item.SimpleItem(**item)


class RankedAgent(agent.Agent):
    '''Data agent for ranked item lists.'''
    @staticmethod
    def _process_data(data: Mapping | Sequence, classes: ClassMap = dict()) -> agent.AgentData:
        if not ismapping(data):
            raise ValueError('Ranked data must be a mapping')

        return agent.AgentData(
            ranked=agent.process_ranked_itemlist(
                data,
                typ=convert_ranked_item,
                xform=agent.create_spellmult_xform(classes),
            )
        )

    async def load_data(self: RankedAgent, pool: Executor) -> types.Ret:
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

    @log_call_async(logger, 'roll random ranked item')
    async def random(self: RankedAgent, **kwargs) -> types.Item | types.Ret:
        item = await super().random_ranked(**kwargs)

        match item:
            case types.Ret.NO_MATCH:
                return types.Ret.NO_MATCH
            case types.item.SpellItem(spell=spell):
                match await cast(SpellAgent, self._ds['spell']).random(**spell):
                    case types.Ret.NOT_READY:
                        return types.Ret.NOT_READY
                    case (ret, msg) if ret is not types.Ret.OK:
                        logger.warning(f'Failed to roll random spell for item using parameters: { spell }, recieved: { msg }')
                        return ret
                    case (types.Ret.OK, spell):
                        if hasattr(item, 'costmult') and item.costmult is not None:
                            item.cost = item.costmult * spell.caster_level

                        item.rolled_spell = spell
                        return item
                    case ret:
                        logger.error(bad_return(ret))
                        return types.Ret.FAILED
            case item:
                return item
