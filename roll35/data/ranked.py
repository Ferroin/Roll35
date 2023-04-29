# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for ranked item lists.'''

from . import agent


class RankedAgent(agent.Agent):
    def __init__(self, dataset, pool, name):
        super().__init__(dataset, pool, name)

    @staticmethod
    def _process_data(data):
        return agent.process_ranked_itemlist(data)

    async def random(self, **kwargs):
        return await super().random_ranked(**kwargs)
