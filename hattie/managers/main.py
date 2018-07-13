from datetime import datetime

import transaction

from hattie.util import legistar_id_guid, make_true_date
from hattie.util import convert_range_to_datetime
from hattie.database import Meeting, Item, Attachment
from hattie.database import Action, ItemAction, ActionVote
from hattie.managers.base import BaseManager


class ItemManager(BaseManager):
    def query(self):
        return self.session.query(Item)

    def add(self, itemdata):
        with transaction.manager:
            i = Item()
            for key in itemdata:
                if key == 'attachments':
                    continue
                value = itemdata[key]
                setattr(i, key, value)
            self.session.add(i)
            if itemdata['attachments'] is not None:
                for name, link in itemdata['attachments']:
                    id, guid = legistar_id_guid(link)
                    if self.session.query(Attachment).get(id) is not None:
                        raise RuntimeError("Duplicate attachment %d" % id)
                    a = Attachment()
                    a.id = id
                    a.guid = guid
                    a.name = name
                    a.link = link
                    a.item_id = i.id
                    self.session.add(a)
        return self.session.merge(i)


class ActionManager(BaseManager):
    def query(self):
        return self.session.query(Action)

    def add(self, item_id, actiondata):
        with transaction.manager:
            a = Action()
            actiondata['filetype'] = actiondata['ftype']
            main_keys = ['id', 'guid']
            rollcall = actiondata['roll_call']
            if not rollcall:
                main_keys += ['action', 'action_text', 'result', 'filetype']
            for key in main_keys:
                setattr(a, key, actiondata[key])
            if not rollcall:
                for key in ['agenda_note', 'minutes_note']:
                    value = actiondata[key].strip()
                    if not value:
                        value = None
                    setattr(a, key, value)
                for key in ['mover', 'seconder']:
                    name, link = actiondata[key]
                    if not name:
                        continue
                    id, guid = legistar_id_guid(link)
                    attribute = '%s_id' % key
                    setattr(a, attribute, id)
                file_id, link = actiondata['file_id']
                a.file_id = file_id
            else:
                a.action = 'Roll Call'
            self.session.add(a)
            # flush here so the action can be referred by
            # foreign keys in 'item_action' and 'action_vote'
            self.session.flush()
            # make item_action object
            item_action = ItemAction(item_id, a.id)
            self.session.add(item_action)
            # handle votes
            for name, link, vote in actiondata['votes']:
                person_id, ignore = legistar_id_guid(link)
                avote = ActionVote(a.id, person_id, vote)
                self.session.add(avote)
        return self.session.merge(a)


class MeetingManager(BaseManager):
    def query(self):
        return self.session.query(Meeting)

    def _add(self, mdata):
        pass

    def add(self, mdata):
        pass

    def _range_filter(self, query, start, end):
        query = query.filter(Meeting.date >= start)
        query = query.filter(Meeting.date <= end)
        return query

    def get_meeting_list(self):
        query = self.session.query(Meeting).order_by(Meeting.date)
        return query.all()

    def get_ranged_meetings(self, start, end, timestamps=False):
        if timestamps:
            start, end = convert_range_to_datetime(start, end)
        q = self.session.query(Meeting)
        q = self._range_filter(q, start, end)
        return q.all()

    def _add_meeting_from_rss(self, entry):
        with transaction.manager:
            m = Meeting()
            m.title = entry.title
            m.link = entry.link
            m.rss = entry
            m.id, m.guid = legistar_id_guid(entry.link)
            m.updated = datetime.now()
            self.session.add(m)
        return self.session.merge(m)

    def _add_collected_meeting(self, meeting, collected):
        with transaction.manager:
            info = collected['info']
            for key in ['id', 'guid', 'time', 'link', 'dept_id',
                        'agenda_status', 'minutes_status']:
                value = info[key]
                setattr(meeting, key, value)
            meeting.date = make_true_date(info['date'])
            meeting.updated = datetime.now()
            m = self.session.merge(meeting)
        return m
