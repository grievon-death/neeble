"""
Bot management.
"""
import logging
from argparse import ArgumentParser

from settings.config import DISCORD_BOT_TOKEN
from utils.commands import client
from utils.database import migrate

logger = logging.getLogger(__name__)

    
manage = ArgumentParser(
    description='Neeble discord bot.'
)
manage.add_argument(
    'command',
    type=str,
)
command = manage.parse_args()

if command.command == 'run':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except Exception as ex:
        logger.error(ex.args[0])
elif command.command == 'migrate':
    migrate()
