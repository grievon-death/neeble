"""
Database utils module.
"""
import logging

import MySQLdb
from models.quotes import Quotes
from settings.config import MYSQL_CONFIG, SQLACHEMY
from sqlalchemy.sql import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Cursor:
    """
    Context manage for database handler.
    """
    def __init__(self, config: dict) -> None:
        """
        Constructor.
        """
        self.configuration = config

    def __enter__(self) -> 'cursor':
        """
        Context manager.
        """
        self.conn = MySQLdb.connect(**self.configuration)
        self.cursor = self.conn.cursor()

        return self.cursor

    def __exit__(self, exc_type, exc_value, exc_trace) -> None:
        """
        Exit from context manager.
        """
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


def migrate() -> None:
    """
    Create tables.
    """
    _sql = '''
        create table if not exists neeble_quotes(
            id int auto_increment primary key,
            user varchar(200) not null,
            quote varchar(500) not null unique,
            date datetime not null,
            grabber varchar(100) not null,
            index quote_idx (quote)
            
        ) character set utf8mb4 collate utf8mb4_general_ci;

        create table if not exists viewed_news(
            id int auto_increment primary key,
            title varchar(500) not null unique,
            published_at date not null,
            index viewed_idx(title, published_at)
        ) character set utf8mb4 collate utf8mb4_general_ci;
    '''
    try:
        with Cursor(MYSQL_CONFIG) as cursor:
            cursor.execute(_sql)
    except Exception as ex:
        logger.error(ex.args)


def set_quote(user: str, quote: str, date: str, grabber: str) -> int:
    """
    Set a quote into database.
    """
    qt = Quotes(quote=quote, user=user, date=date, grabber=grabber)
    qtid = 0
    with Session(SQLACHEMY) as session:
        session.add(qt)
        session.flush()
        session.refresh(qt)
        qtid = qt.id
        session.commit()
    return qtid


def get_quotes(ids: list) -> tuple:
    """
    Get the saved quotes.
    ids: List of quote ID's
    """
    with Session(SQLACHEMY) as session:
        response = session.query(Quotes).filter(Quotes.id.not_in(ids)).order_by(func.random()).first()
        return response


def get_by_id(id: int) -> object:
    """
    Get one quote by ID.
    """
    with Session(SQLACHEMY) as session:
        result = [s for s in session.query(Quotes).filter(Quotes.id==id)]
        return result[0] if result else None

def get_by_user(user: str) -> object:
    """
    Get one quote by user.
    """
    with Session(SQLACHEMY) as session:
        result = session.query(Quotes).filter(Quotes.user==user).order_by(func.random()).first()
        return result

def remove_quote(_id: int) -> bool:
    """
    Delete one quote by database ID.
    """
    try:
        with Session(SQLACHEMY) as session:
            item = get_by_id(_id)
            session.delete(item)
            session.commit()
        return True
    except Exception:
        return False


def count_quotes() -> int:
    """
    Counts the amount of quotes in the database
    """
    with Session(SQLACHEMY) as session:
        response = session.query(Quotes.id).count()
    return response

def count_quotes_user():
    """
    Quote "leaderboard"
    """
    with Session(SQLACHEMY) as session:
        response = session.query(Quotes.user, func.count(Quotes.user)).group_by(Quotes.user).all()
    return response

def get_quote_contains(part: str) -> tuple:
    """
    Get quotes by part of message.
    """
    with Session(SQLACHEMY) as session:
        response = session.query(Quotes).filter(Quotes.quote.contains(part))
    return (r for r in response)
