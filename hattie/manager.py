from datetime import datetime
import transaction
import io
import lzma
import json
# import base64
# import tarfile

from sqlalchemy.orm.exc import NoResultFound
# from sqlalchemy import desc

# from .legistar import legistar_host
from .util import legistar_id_guid
from .util import make_true_date
from .util import convert_range_to_datetime

from .database import Department, Person
from .database import Meeting, Item, MeetingItem
from .database import ItemAction, Action, ActionVote
from .database import Attachment
from .database import AgendaItemTypeMap

from .collector.main import MainCollector
from .collector.rss import RssCollector

timeformat = '%I:%M %p'

drop_models = [Attachment, ActionVote, ItemAction, Action,
               MeetingItem, Item, Meeting, Department, Person]


def delete_all(session):
    with transaction.manager:
        for model in drop_models:
            q = session.query(model)
            q.delete()


def export_all(session):
    data = dict()
    output = io.BytesIO()
    with transaction.manager:
        with lzma.LZMAFile(output, 'w') as zfile:
            for model in drop_models:
                q = session.query(model)
                name = model.__name__
                print("Dumping {}".format(name))
                mlist = [m.serialize() for m in q]
                data[name] = mlist
                print("Exported {}".format(name))
            content = json.dumps(data).encode()
            zfile.write(content)
    del data
    return output.getvalue()


def convert_agenda_number(agenda_number):
    # original = agenda_number
    while agenda_number.startswith('.'):
        agenda_number = agenda_number[1:]
    delimiter = '.-'
    for delimiter in ['. -', '.-', '. - ', ' - ', '-']:
        if delimiter in agenda_number:
            break
    if delimiter in agenda_number:
        itemtype, order = agenda_number.split(delimiter)
        if itemtype.startswith('+'):
            itemtype = itemtype[1:]
        if itemtype in AgendaItemTypeMap:
            itemtype = AgendaItemTypeMap[itemtype]
        order = order.strip()
        while order.endswith('.'):
            order = order[:-1]
        order = int(order)
    else:
        itemtype = 'unknown'
        while agenda_number.endswith('.'):
            agenda_number = agenda_number[:-1]
        if agenda_number and agenda_number.isnumeric():
            order = int(agenda_number)
        else:
            order = None
    return itemtype, order


class ModelManager(object):
    def __init__(self, session):
        self.session = session

    def set_session(self, session):
        self.session = session

    def collector(self):
        return MainCollector()

    def _range_filter(self, query, start, end):
        query = query.filter(Meeting.date >= start)
        query = query.filter(Meeting.date <= end)
        return query

    def get_ranged_meetings(self, start, end, timestamps=False):
        if timestamps:
            start, end = convert_range_to_datetime(start, end)
        q = self.session.query(Meeting)
        q = self._range_filter(q, start, end)
        return q.all()

    # entry is rss entry
    def add_meeting_from_rss(self, entry):
        transaction.begin()
        meeting = Meeting()
        meeting.title = entry.title
        meeting.link = entry.link
        meeting.rss = entry
        meeting.id, meeting.guid = legistar_id_guid(entry.link)
        meeting.updated = datetime.now()
        self.session.add(meeting)
        self.session.flush()
        transaction.commit()

    # retrieve basic meeting info from
    # meeting details page on legistar.
    # the link is from the rss entry
    def remote_meeting(self, link):
        collector = self.collector()
        collector.set_url(link)
        collector.collect('meeting')
        return collector.meeting

    def remote_meeting_info(self, link):
        meeting = self.remote_meeting(link)
        info = meeting['info']
        return info

    def remote_meeting_items(self, link):
        meeting = self.remote_meeting(link)
        items = meeting['items']
        return items

    # link is relative from legistar prefix
    def _remote_legislation_item(self, link):
        print("using link", link)
        collector = self.collector()
        url = collector.url_prefix + link
        collector.set_url(url)
        collector.collect('item')
        return collector.item

    # link is relative url to item page
    def remote_legislation_item(self, link):
        item = self._remote_legislation_item(link)
        # add id, guid to item
        item['id'], item['guid'] = legistar_id_guid(link)
        for key in ['introduced', 'on_agenda', 'passed']:
            if key in item and item[key]:
                item[key] = make_true_date(item[key])
        key = 'action_details'
        if len(item[key]):
            item['acted_on'] = True
        else:
            item['acted_on'] = False
        return item

    # link is full url to meeting
    def remote_legislation_items(self, link):
        meeting_items = self.remote_meeting_items(link)
        print("Meeting has %d items" % len(meeting_items))
        leg_items = []
        for item in meeting_items:
            item_page = item['item_page']
            leg_item = self.remote_legislation_item(item_page)
            leg_items.append(leg_item)
        return leg_items

    def merge_remote_meeting_items(self, meeting_id):
        pass

    def merge_remote_legislation_items(self, meeting_id):
        pass

    # meeting is db object, collected is from collector
    def _merge_collected_meeting(self, meeting, collected):
        transaction.begin()
        info = collected['info']
        for key in ['id', 'guid', 'time', 'link',
                    'dept_id', 'agenda_status', 'minutes_status']:
            value = info[key]
            setattr(meeting, key, value)
        setattr(meeting, 'date', make_true_date(info['date']))
        meeting.updated = datetime.now()
        self.session.merge(meeting)
        self.session.flush()
        transaction.commit()

    def _merge_collected_meeting_items(self, meeting, collected):
        meeting_id = meeting.id
        mtmap = {619637: '_merge_2018_08_7'}
        if meeting_id in mtmap:
            return getattr(self, mtmap[meeting_id])(meeting_id, collected)
        else:
            return self._merge_pickled_meeting_items(meeting_id, collected)

    def _merge_2018_08_7(self, meeting_id, collected):
        transaction.begin()
        items = collected['items']
        item_count = 0
        for item in items:
            item_count += 1
            item_id, guid = legistar_id_guid(item['item_page'])
            query = self.session.query(MeetingItem)
            query = query.filter_by(meeting_id=meeting_id)
            query = query.filter_by(item_id=item_id)
            try:
                dbitem = query.one()
            except NoResultFound:
                dbitem = MeetingItem(meeting_id, item_id)
            agenda_num = item['agenda_num']
            ##########################################
            # # Work around       ####################
            # # irregular entries ####################
            ##########################################
            ##########################################
            if agenda_num == 'IV.':
                dbitem.agenda_num = agenda_num
                type, order = 'unknown', 1
            elif agenda_num == 'VI.':
                type = AgendaItemTypeMap['VI']
                order = 1
            elif agenda_num is not None:
                dbitem.agenda_num = agenda_num
                type, order = agenda_num.split('.-')
                if type == 'IV':
                    type = 'unknown'
                elif type in AgendaItemTypeMap:
                    type = AgendaItemTypeMap[type]
                else:
                    raise RuntimeError("Can't parse {}".format(agenda_num))
            dbitem.type, dbitem.order = type, order
            dbitem.item_order = item_count
            dbitem.version = int(item['version'])
            self.session.merge(dbitem)
            self.session.flush()
        transaction.commit()

    def _merge_pickled_meeting_items(self, meeting_id, collected):
        transaction.begin()
        items = collected['items']
        item_count = 0
        for item in items:
            item_count += 1
            item_id, guid = legistar_id_guid(item['item_page'])
            query = self.session.query(MeetingItem)
            query = query.filter_by(meeting_id=meeting_id)
            query = query.filter_by(item_id=item_id)
            try:
                dbitem = query.one()
            except NoResultFound:
                dbitem = MeetingItem(meeting_id, item_id)
            agenda_num = item['agenda_num']
            ##########################################
            # # Work around       ####################
            # # irregular entries ####################
            ##########################################
            if agenda_num == '2011-0229':
                agenda_num = None
            if agenda_num == '1.':
                agenda_num = '1'
            ##########################################
            #                     ####################
            #                     ####################
            ##########################################
            # first agenda item is missing from meeting details
            if meeting_id == 302621:
                agenda_num = '2'
            if agenda_num is not None:
                dbitem.agenda_num = agenda_num
                dbitem.type, dbitem.order = convert_agenda_number(agenda_num)
            dbitem.item_order = item_count
            dbitem.version = int(item['version'])
            self.session.merge(dbitem)
            self.session.flush()
        transaction.commit()

    def merge_meeting_from_legistar(self, id):
        collector = MainCollector()
        meeting = self.session.query(Meeting).filter_by(id=id).one()
        collector.set_url(meeting.link)
        collector.collect('meeting')
        self._merge_collected_meeting(meeting, collector.meeting)

    def add_departments(self):
        collector = MainCollector()
        collector.collect('dept')
        self.add_collected_depts(collector.result)

    def add_collected_depts(self, depts):
        transaction.begin()
        for dept_info in depts:
            id, guid, name = dept_info
            dept = Department(id, guid)
            dept.name = name
            self.session.add(dept)
        self.session.flush()
        transaction.commit()

    def update_departments(self):
        collector = MainCollector()
        collector.collect('dept')
        transaction.begin()
        for dept_info in collector.result:
            id, guid, name = dept_info
            dept = self.session.query(Department).get(id)
            if dept is None:
                dept = Department(id, guid)
                dept.name = name
                self.session.add(dept)
                continue
            dept.id = id
            dept.guid = guid
            dept.name = name
            self.session.add(dept)
        self.session.flush()
        transaction.commit()

    def add_people(self):
        collector = MainCollector()
        collector.collect('people')
        self.add_collected_people(collector.result)

    def add_collected_people(self, people):
        transaction.begin()
        for pinfo in people:
            person = Person()
            for key in pinfo:
                setattr(person, key, pinfo[key])
            self.session.add(person)
        self.session.flush()
        transaction.commit()

    def get_rss(self, url):
        collector = RssCollector()
        collector.get_rss(url)
        return collector

    def add_collected_action(self, item_id, action):
        dbaction = Action()
        action['filetype'] = action['ftype']
        main_keys = ['id', 'guid']
        if not action['roll_call']:
            main_keys += ['action', 'action_text', 'result', 'filetype']
        for key in main_keys:
            setattr(dbaction, key, action[key])
        if not action['roll_call']:
            for key in ['agenda_note', 'minutes_note']:
                value = action[key].strip()
                if not value:
                    value = None
                setattr(dbaction, key, value)
            for key in ['mover', 'seconder']:
                name, link = action[key]
                if not name:
                    continue
                id, guid = legistar_id_guid(link)
                att = '%s_id' % key
                setattr(dbaction, att, id)
            file_id, link = action['file_id']
            dbaction.file_id = file_id
        else:
            dbaction.action = 'Roll Call'
        with transaction.manager:
            self.session.add(dbaction)
            # flush here so the action can be referred by
            # foreign keys in 'item_action' and 'action_vote'
            self.session.flush()
            # make item_action object
            item_action = ItemAction(item_id, dbaction.id)
            self.session.add(item_action)
            # handle votes
            ward_num = 1
            vote_attributes = dict(action_id=dbaction.id)
            for name, link, vote in action['votes']:
                person_id, ignore = legistar_id_guid(link)
                id_key = 'ward{}_person_id'.format(ward_num)
                vote_attributes[id_key] = person_id
                vote_attributes['ward{}'.format(ward_num)] = vote
                ward_num += 1

            avote = ActionVote()
            for attribute, value in vote_attributes.items():
                setattr(avote, attribute, value)
                self.session.add(avote)

    # add the item before the actions
    def _add_collected_legislation_item(self, item):
        transaction.begin()
        dbitem = Item()
        for key in item:
            if key == 'attachments':
                continue
            value = item[key]
            setattr(dbitem, key, value)
        self.session.add(dbitem)
        if item['attachments'] is not None:
            for name, link in item['attachments']:
                id, guid = legistar_id_guid(link)
                dbobj = self.session.query(Attachment).get(id)
                if dbobj is None:
                    attachment = Attachment()
                    attachment.id, attachment.guid = id, guid
                    attachment.name = name
                    attachment.link = link
                    attachment.item_id = dbitem.id
                    self.session.add(attachment)
                else:
                    msg = 'Duplicate attachment %d' % id
                    raise RuntimeError(msg)
        transaction.commit()

    # here item is an item collected from
    # legistar
    def add_new_legislation_item(self, item):
        self._add_collected_legislation_item(item)
        for link in item['action_details']:
            collector = MainCollector()
            url = collector.url_prefix + link
            collector.set_url(url)
            collector.collect('action')
            self.add_collected_action(item['id'], collector.action)
        self.session.flush()
        transaction.commit()
