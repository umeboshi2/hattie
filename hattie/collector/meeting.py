import re

# from ..util import onclick_link
from ..util import legistar_id_guid

from .base import BaseCollector

SPANIDS = dict(agenda_status='_lblAgendaStatus',
               minutes_status='_lblMinutesStatus',
               date='_lblDate',
               time='_lblTime')

ANCHORIDS = dict(agenda='_hypAgenda',
                 minutes='_hypMinutes',
                 dept='_hypName')


MEETING_ITEM_COLUMNS = ['file_id',
                        'version',
                        'agenda_num',
                        'name',
                        'type',
                        'title',
                        'action',
                        'result',
                        'action_details',
                        'video'
                        ]


class MeetingCollector(BaseCollector):
    def _get_meeting_info(self, page):
        info = {'anchors': {},
                'spans': {}
                }
        for key in SPANIDS:
            exp = re.compile('.+%s$' % SPANIDS[key])
            spans = page.find_all('span', id=exp)
            if len(spans) != 1:
                print("No span for %s" % key)
            info['spans'][key] = spans[0]
        for key in ANCHORIDS:
            exp = re.compile('.+%s$' % ANCHORIDS[key])
            anchors = page.find_all('a', id=exp)
            if len(anchors) != 1:
                raise RuntimeError("No anchor for %s" % key)
            info['anchors'][key] = anchors[0]
        return info

    def _prepare_meeting_info(self, info):
        newinfo = {}
        for key in list(info['anchors'].keys()):
            if 'href' in info['anchors'][key].attrs:
                newinfo[key] = info['anchors'][key]['href']
            else:
                newinfo[key] = None
        for key in list(info['spans'].keys()):
            newinfo[key] = info['spans'][key].text
        return newinfo

    def get_meeting_info(self, page):
        info = self._get_meeting_info(page)
        return self._prepare_meeting_info(info)

    def _make_meeting_item(self, row):
        colnames = MEETING_ITEM_COLUMNS
        cols = row.find_all('td')
        item = {}.fromkeys(colnames)
        item['item_page'] = cols[0].a['href']
        # generic parsing from file_id to title
        for index in range(len(colnames)):
            text = cols[index].text.strip()
            if text:
                item[colnames[index]] = text
        return item

    def get_meeting_items(self, page):
        tables = page.find_all('table', class_='rgMasterTable')
        if len(tables) > 1:
            msg = "Problem with determining master table len(tables) = %d"
            raise RuntimeError(msg % len(tables))
        elif not tables:
            return []
        table = tables.pop()
        items = []
        # skip the head row
        for row in table.find_all('tr')[1:]:
            # skip a table with no records
            if 'class' in row.attrs and row.attrs['class'] == ['rgNoRecords']:
                continue
            item = self._make_meeting_item(row)
            items.append(item)
        return items

    def get_meeting(self, page):
        items = self.get_meeting_items(page)
        info = self.get_meeting_info(page)
        # FIXME: THIS DEPENDS ON USING collect()
        info['id'], info['guid'] = legistar_id_guid(self.url)
        info['link'] = self.url
        id, guid = legistar_id_guid(info['dept'])
        info['dept_id'] = id
        return dict(items=items, info=info)

    def collect(self):
        self.retrieve_page(url=self.url)
        self.meeting = self.get_meeting(self.soup)
        self.result = self.meeting
