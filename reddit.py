"""Module handling contact with Reddit APIs."""
import logging
import os
from typing import List, Optional

import attr
import praw
import urllib.parse

import api_module

REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
REDDIT_USER = os.environ.get('REDDIT_USER')
REDDIT_PASSWORD = os.environ.get('REDDIT_PASSWORD')

USERAGENT = 'gabenizer'

TARGET_SUBREDDIT = 'gentlemanboners'
OUR_SUBREDDIT = 'gentlemangabers'


@attr.s(auto_attribs=True)
class Post:
    title: str
    url: str
    permalink: str

    @staticmethod
    def from_submission(submission: praw.reddit.models.Submission):
        """Construct a Post from a PRAW Submission object."""
        return Post(
            title=submission.title,
            url=submission.url,
            permalink=submission.permalink
        )


_reddit_instance = None


def reddit() -> praw.Reddit:
    """Lazily fetch singleton PRAW instance."""
    global _reddit_instance

    assert REDDIT_CLIENT_ID
    assert REDDIT_CLIENT_SECRET
    assert REDDIT_USER
    assert REDDIT_PASSWORD

    if not _reddit_instance:
        _reddit_instance = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=USERAGENT,
            username=REDDIT_USER,
            password=REDDIT_PASSWORD,
        )
    return _reddit_instance


class SubredditFetcher:
    """Gets list of recent posts from a subreddit."""
    
    def get_recent_posts(self, target_subreddit: str = TARGET_SUBREDDIT, limit_target: int = 10) -> List[Post]:
        target_recent = self.fetch(target_subreddit, limit=limit_target, fetch_type='hot')

        posts = []
        for post in target_recent:
            post.url = self._get_normalized_url_or_none(post.url)
            if post.url:
                posts.append(post)

        logging.info('Got posts: %r', posts)
        return posts

    @staticmethod
    def _get_normalized_url_or_none(url: str) -> Optional[str]:
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc == 'i.imgur.com':
            return parsed.geturl()
        if parsed.netloc == 'imgur.com' and not parsed.path.startswith('/a/'):
            return parsed.geturl() + '.png'
        return None

    @api_module.register
    def fetch(self, subreddit: str, limit: int, fetch_type: str = 'hot') -> List[Post]:
        sub_instance = reddit().subreddit(subreddit)
        if fetch_type == 'hot':
            return [Post.from_submission(submission) for submission in sub_instance.hot(limit=limit)]
        elif fetch_type == 'new':
            return [Post.from_submission(submission) for submission in sub_instance.new(limit=limit)]
        else:
            raise NotImplementedError('unknown value for fetch_type: %s' % fetch_type)

    def mocked_fetch(self, subreddit: str, limit: int, fetch_type: str = 'hot') -> List[Post]:
        return [
            Post(title='Fake %d' % i, url='https://i.imgur.com/ZClFAdK.jpg',
                 permalink='https://www.reddit.com/fakepermalink')
            for i in range(limit)]


class LinkSubmitter:

    def post_link(self, url: str, title: str, source: str, subreddit: str = OUR_SUBREDDIT) -> None:
        self.submit(url=url, title=title, comment=LinkSubmitter._format_comment(source=source), subreddit=subreddit)

    @staticmethod
    def _format_comment(source: str) -> str:
        return '[Source](%s)' % source

    @api_module.register
    def submit(self, url: str, title: str, comment: str, subreddit: str) -> None:
        logging.info('Posting submission for %s.', url)
        # TODO: use submit_image in place of image_uploader module
        submission = reddit().subreddit(subreddit).submit(
            title=title,
            url=url,
        )

        logging.info('Posting comment %s.', comment)
        submission.reply(comment)

    def mocked_submit(self, url: str, title: str, comment: str, subreddit: str) -> None:
        pass
