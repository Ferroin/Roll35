# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

'''Roll35: A Python package and Discord bot for rolling random items and spells for Pathfinder 1e.

   Roll35 can be run directly as a module with `python -m roll35`, in
   which case it will start a Discord bot. When run this way it expects
   the environment variable `DISCORD_TOKEN` to contain a valid Discord
   bot account token, which it will use to connect to Discord.

   For programmatic access to the item data, see `roll35.data`.

   Items are rendered by the bot using `roll35.renderer`.

   Cogs, possibly reusable in other Discord bots, can be found in
   `roll35.cogs`.

   Note that many parts of this package use values from
   `roll35.types.Ret` as return codes in preference to raising special
   exception types.

   This package requires Python 3.10 as it makes extensive use of PEP
   634 structural pattern matching.'''

import sys

from . import cogs, common, data, parser, renderer, roller, types
from .common import VERSION

__version__ = f'{VERSION[0]}.{VERSION[1]}.{VERSION[2]}'

__all__ = [
    'cogs',
    'common',
    'data',
    'parser',
    'renderer',
    'roller',
    'types',
]

if not sys.version_info >= (3, 10):
    raise RuntimeError('roll35 requires Python 3.10 or newer.')
