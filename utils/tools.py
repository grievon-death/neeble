"""
Tools module.
"""
import logging
from datetime import datetime

import pytz

logger = logging.getLogger(__name__)


def kbytes_to_gbytes(value: float) -> str:
    """
    Transform Kb into Gb.
    """
    _value = value / (1024 ** 3)
    return "{:.2f}".format(_value)


def datetime_to_string(_datetime: datetime) -> str:
    """
    Transform datetime in string DD/MM/AAAA HH:MM:SS
    """
    try:
        dt = datetime.fromisoformat(
            _datetime
        )
    except ValueError:
        dt = datetime.strptime(
            _datetime,
            '%Y-%m-%dT%H:%M:%Sz'
        )
    except Exception as e:
        logger.error(e) 
        return dt

    try:
        dt = dt.astimezone(pytz.timezone('America/Sao_Paulo'))
    except Exception as e:
        logger.error(e)
    else:
        return dt.date().isoformat()
