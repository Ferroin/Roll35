# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data types used throughout roll35.'''

from __future__ import annotations

from .cog import R35Cog

from .container import R35Container
from .map import R35Map
from .list import R35List
from .range import R35Range

from .item import Item, CompoundItem, Cost, WeightedValue, Spell
from .ranks import Rank, Subrank

from .retcode import Ret, Result

from .readystate import ReadyState, check_ready

SubrankedItemList = R35Map[Subrank, R35List[Item]]
RankedItemList = R35Map[Rank, SubrankedItemList]
CompoundItemList = R35Map[Rank, R35List[CompoundItem]]

__all__ = (
    'R35Cog',
    'R35Container',
    'R35Map',
    'R35List',
    'R35Range',
    'Item',
    'CompoundItem',
    'Cost',
    'Spell',
    'WeightedValue',
    'Rank',
    'Subrank',
    'Ret',
    'Result',
    'ReadyState',
    'check_ready',
    'SubrankedItemList',
    'RankedItemList',
    'CompoundItemList',
)
