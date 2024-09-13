# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data types used throughout roll35.'''

from __future__ import annotations

from .cog import R35Cog
from .container import R35Container
from .item import CompoundItem, CompoundSpellItem, Cost, Item, Spell, WeightedValue
from .list import R35List
from .map import R35Map
from .range import R35Range
from .ranks import Rank, Subrank
from .readystate import ReadyState, check_ready, check_ready_async
from .retcode import Result, Ret

SubrankedItemList = R35Map[Subrank, R35List[Item]]
RankedItemList = R35Map[Rank, SubrankedItemList]
CompoundItemSublist = R35List[CompoundItem | CompoundSpellItem]
CompoundItemList = R35Map[Rank, CompoundItemSublist]

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
    'check_ready_async',
    'SubrankedItemList',
    'RankedItemList',
    'CompoundItemSublist',
    'CompoundItemList',
)
