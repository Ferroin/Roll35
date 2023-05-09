# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Data types used throughout roll35.'''

from __future__ import annotations

from .cog import R35Cog

from .container import R35Container
from .map import R35Map
from .list import R35List
from .range import R35Range, RangeMember

from .base import WeightedEntry, Rank, Subrank, ItemEntry
from .item import Item

from .retcode import Ret, Result

SubrankedItemList = R35Map[Subrank, R35List[Item | WeightedEntry]]
RankedItemList = R35Map[Rank, SubrankedItemList]
CompoundItemList = R35Map[Rank, R35List[WeightedEntry]]
