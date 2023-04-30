# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data handling for spell classes.'''

from . import agent
from ..common import check_ready


class ClassesAgent(agent.Agent):
    '''A data agent for spellcasting class data.'''
    @staticmethod
    def _process_data(data):
        return data

    async def W_classdata(self):
        '''Return the bulk data, but wait until the agent is ready.'''
        await self._ready.wait()
        return self._data

    @check_ready
    async def classdata(self):
        '''Return the bulk data.'''
        return self._data

    @check_ready
    async def classes(self):
        '''Return the list of classes.'''
        return list(self._data.keys())

    @check_ready
    async def get_class(self, cls):
        '''Return the data for a specific class, by name.'''
        return self._data[cls]
