import feedparser
import requests


class RssCollector(object):
    def __init__(self):
        self.rss = None
        self.info = None
        self.entries = []

    def get_rss(self, url, content=None):
        if content is None:
            r = requests.get(url)
            self.content = r.content
            self.info = r.header
        else:
            self.content = content
        self.rss = feedparser.parse(self.content)
        self.entries = self.rss.entries
