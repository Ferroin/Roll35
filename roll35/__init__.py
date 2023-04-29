# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import sys

from .common import VERSION

BOT_HELP = '''Roll items and spells for first-edition Pathfinder.

Note that currently we do not support:

- Rolling random materials for magic armor and weapons.
- Rolling stored spells for items capable of storing spells.
- Rolling for whether an item is intelligent or not.
- Rolling for whether magic items have special markings or not.
- Rolling skills for items that provide skill ranks.

This bot is capable of responding to direct messages, though you will
still need to use the command prefix.

Commands, and most of ther parameters, are case-insensitive.

Supported commands, grouped by category:
'''

__version__ = f'{ VERSION[0] }.{ VERSION[1] }.{ VERSION[2] }'

__all__ = [
    'cogs',
    'common',
    'data',
    'parser',
    'renderer',
    'retcode',
    'types',
]

if not sys.version_info >= (3, 10):
    raise RuntimeError('roll35 requires Python 3.10 or newer.')
