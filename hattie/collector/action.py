import re

from ..util import legistar_id_guid

from .base import BaseCollector

ACTION_DATA_IDENTIFIERS = dict(file_id='_hypFile',
                               ftype='_lblType',
                               mover='_hypMover',
                               seconder='_hypSeconder',
                               result='_lblResult',
                               agenda_note='_lblAgendaNote',
                               minutes_note='_lblMinutesNote',
                               action='_lblAction',
                               action_text='_lblActionText')


class ActionCollector(BaseCollector):
    def _get_votes(self, page):
        tables = page.find_all('table', class_='rgMasterTable')
        if len(tables) != 1:
            msg = "Problem with determining master table len(tables) = %d"
            raise RuntimeError(msg % len(tables))
        table = tables.pop()
        items = []
        for row in table.find_all('tr')[1:]:
            if 'rgNoRecords' in row['class']:
                return []
            person, vote = row.find_all('td')
            name = person.text.strip()
            link = person.a['href']
            vote = vote.text.strip()
            items.append((name, link, vote))
        return items

    def _get_action(self, page):
        markers = ACTION_DATA_IDENTIFIERS
        item_keys = list(markers.keys())
        item = {}.fromkeys(item_keys)
        item['roll_call'] = False
        found_tags = False
        for key in item_keys:
            exp = re.compile('.+%s$' % markers[key])
            tags = page.find_all('span', id=exp)
            if not tags:
                tags = page.find_all('a', id=exp)
            if not tags:
                print("NO TAGS FOR", key)
                continue
            found_tags = True
            if len(tags) > 1:
                print("len(%s) == %d" % (key, len(tags)))
            tag = tags[0]
            if markers[key].startswith('_lbl'):
                # just text with lbl
                item[key] = tag.text.strip()
            elif markers[key].startswith('_hyp'):
                name = tag.text.strip()
                link = tag['href']
                item[key] = (name, link)
            else:
                item[key] = tag
        if not found_tags:
            rollcall_id = 'ctl00_ContentPlaceHolder1_pageRollCall'
            if page.find_all('div', id=rollcall_id):
                item['roll_call'] = True
        item['votes'] = self._get_votes(page)
        return item

    def collect(self):
        self.retrieve_page(self.url)
        self.action = self._get_action(self.soup)
        self.action['id'], self.action['guid'] = legistar_id_guid(self.url)
        self.result = self.action
