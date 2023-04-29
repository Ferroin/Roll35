# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for compound item lists.'''

import logging

from . import agent
from . import constants
from ..common import yaml, bad_return
from ..retcode import Ret

logger = logging.getLogger(__name__)


def create_spellmult_xform(classes):
    def xform(x):
        levels = map(lambda x: x['levels'], classes.values())

        match x:
            case {'spell': {'level': level, 'class': 'minimum'}, 'costmult': costmult}:
                levels = filter(lambda x: len(x) > level and x[level] is not None, levels)
                levels = set(map(lambda x: x[level], levels))
                minlevel = min(levels)
                x['cost'] = minlevel * costmult
            case {'spell': {'level': level}, 'costmult': costmult}:
                levels = filter(lambda x: len(x) > level and x[level] is not None, levels)
                levels = set(map(lambda x: x[level], levels))
                minlevel = min(levels)
                maxlevel = max(levels)
                x['costrange'] = [
                    minlevel * costmult,
                    maxlevel * costmult,
                ]
            case _:
                raise ValueError(f'Invalid compound spell entry { x }')

        return x

    return xform


class CompoundAgent(agent.Agent):
    def __init__(self, dataset, name):
        super().__init__(dataset, name)

    @staticmethod
    def _process_data(data):
        return agent.process_compound_itemlist(data)

    async def random(self, **kwargs):
        return await super().random_compound(**kwargs)


class CompoundSpellAgent(CompoundAgent):
    @staticmethod
    def _process_data(data, classes):
        ret = agent.process_compound_itemlist(
            data,
            create_spellmult_xform(classes)
        )

        return ret

    async def load_data(self, pool):
        '''Load data for this agent.'''
        if not self._ready.is_set():
            logger.info('Fetching class data.')

            classes = await self._ds['classes'].W_classdata()

            logger.info(f'Loading { self.name } data.')

            with open(constants.DATA_ROOT / f'{ self.name }.yaml') as f:
                data = yaml.load(f)

            self._data = await self._process_async(pool, self._process_data, [data, classes])
            logger.info(f'Finished loading { self.name } data.')

            self._ready.set()

        return Ret.OK

    async def random(self, cls=None, **kwargs):
        match await super().random_compound(**kwargs):
            case Ret.NO_MATCH:
                return (Ret.NO_MATCH, 'No items match specified cost range.')
            case {'spell': spell, **item}:
                match await self._ds['spell'].random(**spell):
                    case Ret.NOT_READY:
                        return (Ret.NOT_READY, 'Failed to roll random spell for item: spell data not ready.')
                    case (ret, msg) if ret is not Ret.OK:
                        logger.warning(f'Failed to roll random spell for item using parameters: { msg }, recieved: { msg }')
                        return (ret, f'Failed to roll random spell for item: { msg }')
                    case (Ret.OK, spell):
                        if 'costmult' in item:
                            item['cost'] = item['costmult'] * spell['caster_level']

                        item['rolled_spell'] = spell
                        item['spell'] = spell
                        return (Ret.OK, item)
                    case ret:
                        logger.error(bad_return(ret))
                        return (Ret.FAILED, 'Unknown internal error.')
            case item:
                return (Ret.OK, item)
