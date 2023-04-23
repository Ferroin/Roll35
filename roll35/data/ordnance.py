# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for armor, shields, and weapons.'''

import logging

from . import agent
from . import types
from ..common import DATA_ROOT, yaml

logger = logging.getLogger(__name__)


class OrdnanceAgent(agent.Agent):
    def __init__(self, pool, name, logger=logger):
        super().__init__(pool, name, logger)

    @staticmethod
    def _loader(name):
        with open(DATA_ROOT / f'{ name }.yaml') as f:
            data = yaml.load(f)

        ret = agent.process_ranked_itemlist(data)

        ret['base'] = list(data['base'])
        ret['tags'] = agent.generate_tags_entry(data['base'])
        ret['enchantments'] = agent.process_enchantment_table(data['enchantments'])

        if types.RANK[1] in data['specific']:
            ret['specific'] = agent.process_ranked_itemlist(data['specific'])
        else:
            ret['specific'] = dict()

            for key in data['specific']:
                ret['specific'][key] = agent.process_ranked_itemlist(data['specific'][key])

        return ret

    async def random(self, rank, subrank, allow_specific=True):
        return await super().random_pattern(rank, subrank, allow_specific)
