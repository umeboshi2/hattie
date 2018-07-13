import re

from ..util import legistar_id_guid

from .base import BaseCollector


class DeptCollector(BaseCollector):
    def __init__(self):
        BaseCollector.__init__(self)
        url = 'https://hattiesburg.legistar.com/Departments.aspx'
        self.set_url(url)

    def _get_depts(self, page):
        depts = []
        # each entry is a tuple (id, guid, name)
        anchors = page.find_all('a', id=re.compile('.+_hypBody$'))
        for anchor in anchors:
            id, guid = legistar_id_guid(anchor['href'])
            name = anchor.text.strip()
            depts.append((id, guid, name))
        return depts

    def collect(self):
        self.retrieve_page(self.url)
        self.depts = self._get_depts(self.soup)
        self.result = self.depts
