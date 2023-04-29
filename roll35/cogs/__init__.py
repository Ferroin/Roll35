# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Cogs for the bot.'''

from .core import Core
from .magicitem import MagicItem
from .ordnance import Ordnance
from .settlement import Settlement
from .spell import Spell


COGS = [
    Core,
    MagicItem,
    Ordnance,
    Settlement,
    Spell,
]
