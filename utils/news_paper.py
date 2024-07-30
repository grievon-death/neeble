import logging
from datetime import datetime

import requests
from models.news import ViewedNews
from settings.config import GOOGLE_NEWS, SQLACHEMY
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class News:
    """
    Get the information in IBGE API.
    """
    _url = f'{GOOGLE_NEWS["url"]}everything?'\
        f'sources={",".join(GOOGLE_NEWS["sources"])}'\
        f'&apiKey={GOOGLE_NEWS["token"]}'

    def __init__(self, quantity: int=5) -> None:
        """
        Constructor.
        """
        self.quantity = int(quantity)

    def _date_convert(self, _date) -> datetime:
        """
        Convert new datetime.
        """
        try:
            _date = datetime.fromisoformat(_date)
        except ValueError:
            _date = datetime.strptime(_date, '%Y-%m-%dT%H:%M:%Sz')
        except Exception as e:
            logger.error(e)

        return _date

    def _remove_viewed_news(self, articles: list) -> list:
        """
        Remove the viewed news. 
        """
        with Session(SQLACHEMY) as session:
            for idx, new in enumerate(articles):
                viewed = session.query(ViewedNews).filter(
                    ViewedNews.title==new['title'],
                    ViewedNews.published_at==self._date_convert(new['publishedAt']).date()
                )

                if list(viewed):
                    articles.pop(idx)

        return articles

    def _set_viewed_news(self, articles: list) -> None:
        """
        Set viewed news in data base.
        """
        with Session(SQLACHEMY) as session:
            for article in articles:
                _date = self._date_convert(article['publishedAt'])
                new = ViewedNews(title=article['title'], published_at=_date.date())
                session.add(new)

                try:
                    session.commit()
                except IntegrityError:
                    logger.warning('Duplicated entry.\nTitle: %s' % (article['title']))
                    continue
                except Exception as e:
                    logger.error(e.args[0])
                    pass

    def news(self) -> list:
        """
        Get the information based in self.quantity attribute.
        """
        _response = requests.get(url=self._url)
        content, status = _response.json(), _response.status_code

        if not status == 200:
            logger.error(content)
            raise Exception(content)

        # Remove viewed news.
        response = self._remove_viewed_news(content['articles'])[:self.quantity]
        # Save news into a blacklist.
        self._set_viewed_news(response)

        return response

    def filter(self, phrase: str) -> list:
        """
        Filter content by keywords.
        """
        _url = f'{self._url}&q={phrase if phrase else ""}'
        _response = requests.get(url=_url)
        content, status = _response.json(), _response.status_code

        if not status == 200:
            logger.error(content)
            raise Exception(content)

        return content['articles'][:self.quantity]
