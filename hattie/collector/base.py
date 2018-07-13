import robobrowser


class BaseCollector(object):
    def __init__(self):
        self.browser = robobrowser.RoboBrowser(parser='lxml')
        self.url = None
        self.response = None
        self.pageinfo = None
        self.content = ''
        self.soup = None
        self.url_prefix = 'https://hattiesburg.legistar.com/'

    def retrieve_page(self, url=None):
        if url is None:
            url = self.url
        else:
            self.url = url
        if url is None:
            raise RuntimeError("No url set.")
        self.response = self.browser.open(url)
        self.info = self.browser.response.headers
        self.content = self.browser.response.content
        self.soup = self.browser.parsed

    def set_url(self, url):
        self.url = url
        self.response = None
        self.pageinfo = None
        self.content = ''
        self.soup = None

    def collect(self):
        pass
