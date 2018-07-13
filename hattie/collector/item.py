import re

from ..util import onclick_link
from ..util import make_true_date
from ..util import legistar_id_guid


from .base import BaseCollector

ITEM_DATA_IDENTIFIERS = dict(file_id='_lblFile2',
                             name='_lblName2',
                             filetype='_lblType2',
                             status='_lblStatus2',
                             introduced='_lblIntroduced2',
                             on_agenda='_lblOnAgenda2',
                             attachments='_lblAttachments2',
                             title='_lblTitle2',
                             passed='_lblPassed2',
                             action_details='_hypDetails')


class ItemCollector(BaseCollector):
    def _get_item(self, page):
        markers = ITEM_DATA_IDENTIFIERS
        item_keys = list(markers.keys())
        item = {}.fromkeys(item_keys)
        item['action_details'] = []
        for key in item_keys:
            exp = re.compile('.+%s$' % markers[key])
            tags = page.find_all('span', id=exp)
            if not tags:
                tags = page.find_all('a', id=exp)
            if not tags and key == 'action_details':
                continue
            if len(tags) > 1:
                print("len(%s) == %d" % (key, len(tags)))
            if key == 'action_details':
                for a in tags:
                    if 'onclick' in a.attrs:
                        item[key].append(onclick_link(a['onclick']))
                continue
            if key == 'attachments' and len(tags):
                chunk = tags[0]
                attachments = []
                for anchor in chunk.find_all('a'):
                    name = anchor.text.strip()
                    link = anchor['href']
                    attachments.append((name, link))
                item[key] = attachments
                continue
            if not len(tags) and key == 'attachments':
                continue
            value = tags[0].text.strip()
            if value:
                item[key] = value
            else:
                item[key] = None
        return item

    def collect(self):
        self.retrieve_page(self.url)
        if b'Invalid parameters!' in self.content:
            item = dict()
            item['action_details'] = []
            item['bad_url'] = self.url
            self.item = item
            self.result = self.item
            print("Invalid parameters found", self.result)
            return
        self.item = self._get_item(self.soup)
        for key in ['passed', 'introduced', 'on_agenda']:
            if key in self.item and not self.item[key]:
                self.item[key] = None
            else:
                self.item[key] = make_true_date(self.item[key])
        if len(self.item['action_details']):
            self.item['acted_on'] = True
        else:
            self.item['acted_on'] = False
        self.item['id'], self.item['guid'] = legistar_id_guid(self.url)
        self.result = self.item
