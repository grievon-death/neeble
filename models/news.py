from settings.config import SQLACHEMY
from sqlalchemy import Table
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ViewedNews(Base):
    """
    Viewed news model class.
    """
    __table__ = Table(
        "viewed_news",
        Base.metadata,
        autoload=True,
        autoload_with=SQLACHEMY
    )
