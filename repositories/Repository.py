from entities import Entities
import pony.orm as pny
from repositories import sql_queries
from util.logging_util import get_logger

"""
 Methods for interacting with database
 """
class Repository:
    logger = get_logger("logs/repository")

    def save_category(self, title, link, parent, forum):
        try:
            with pny.db_session:
                return Entities.Category(title=title, link=link,
                                         forum=forum.forum_id,
                                         parent_category=None if parent is None else parent.category_id)
        except KeyError as e:
            self.logger.error(str(e))
            self.logger.error("For element: " + str(title))

    def save_topic(self, author, date, link, parent, title):
        try:
            with pny.db_session:
                return Entities.Topic(title=title, link=link,
                                      author='' if author is None else str(author),
                                      date=date,
                                      category=parent.category_id)
        except BaseException as e:
            self.logger.error(str(e))
            self.logger.error("Title: " + title + " link: " + link + " author: " + author)

    def save_post(self, author, content, date, parent):
        try:
            with pny.db_session:
                Entities.Post(content=content, topic=parent.topic_id,
                              author='' if author is None else str(author),
                              date=date)
        except BaseException as e:
            self.logger.error("Save post: " + str(e))
            self.logger.error("Content: " + content + " parent_id: " + str(parent.topic_id))

    def save_forum(self, link):
        with pny.db_session:
            forum = Entities.Forum(link=link)
            return forum

    def find_forum(self, link):
        """
         Get forum of given link with highest id
         """
        with pny.db_session:
            forum = Entities.Forum.select(lambda p: p.link == link).order_by(pny.desc(Entities.Forum.forum_id)).first()
            return forum

    def get_categories(self, ids):
        with pny.db_session:
            categories = list(Entities.Category.select(lambda x: x.category_id in ids))
            return categories

    def get_forum_of_category(self, category):
        with pny.db_session:
            return category.forum

    def get_all_categories(self, forum):
        with pny.db_session:
            categories = list(Entities.Category.select(lambda x: x.forum.forum_id == forum.forum_id))
            return categories

    def get_posts(self, date_from, date_to, forum_id):
        with pny.db_session:
            data = Entities.db.select(sql_queries.query_all_posts(forum_id, date_from, date_to))
        return data

    def get_all_forums(self):
        with pny.db_session:
            data = list(Entities.Forum.select())
            return data