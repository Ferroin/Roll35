#!python
#
# Copyright (c) 2023 Austin S. Hemmelgarn
# SPDX-License-Identifier: MITNFA

import logging
import logging.config
import os

import roll35

TOKEN = os.environ['DISCORD_TOKEN']

if 'LOG_LEVEL' in os.environ:
    LOG_LEVEL = os.environ['LOG_LEVEL']
else:
    LOG_LEVEL = 'INFO'

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'basic': {
            'format': '%(asctime)s %(levelname)-8s %(name)-15s %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'basic',
            'level': LOG_LEVEL,
        },
    },
    'root': {
        'handlers': [
            'console'
        ],
        'level': LOG_LEVEL,
    },
    'disable_existing_loggers': False,
})
logging.basicConfig(level=logging.INFO)

roll35.main(TOKEN)
