from settings.config import SQLACHEMY
from sqlalchemy import Table
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Quotes(Base):
    """
    Quotes model class.
    """
    __table__ = Table(
        "neeble_quotes",
        Base.metadata,
        autoload=True,
        autoload_with=SQLACHEMY
    )
