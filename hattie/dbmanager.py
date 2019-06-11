from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy import extract

import feedparser

from .database import Meeting, Item, Action
from .database import Person, Department

from .manager import ModelManager, delete_all, export_all


from .util import legistar_id_guid


def check_dupe_item(session, item):
    Dupe = True
    # FIXME straighten this out
    if 'id' not in item:
        print("Bad item", item)
        import pdb ; pdb.set_trace() # noqa
        return Dupe
    dbitem = session.query(Item).get(item['id'])
    if dbitem is None:
        return False
    filtered_keys = ['attachments', 'action_details']
    keys = [k for k in list(item.keys()) if k not in filtered_keys]
    for key in keys:
        if getattr(dbitem, key) != item[key]:
            Dupe = False
    return Dupe


class DatabaseManager(object):
    def __init__(self, session, collector):
        self.session = session
        self.collector = collector
        self.manager = ModelManager(self.session)
        self.meeting = None
        self.parsed = None

    @property
    def collecter(self):
        # FIXME collecter should be collector
        import warnings
        warnings.warn("Please use .collector instead.", stacklevel=2)
        return self.collector

    def add_collected_people(self, people):
        return self.manager.add_collected_people(people)

    def add_people(self):
        people = self.session.query(Person).all()
        if not len(people):
            print("adding people........")
            people = self.collector.collect('people')
            self.add_collected_people(people)

    def add_collected_depts(self, depts):
        return self.manager.add_collected_depts(depts)

    def add_departments(self):
        depts = self.session.query(Department).all()
        if not len(depts):
            print("adding departments.....")
            depts = self.collector.collect('depts')
            self.add_collected_depts(depts)

    def add_rss_meetings(self, url, rss=None):
        if rss is None:
            rss = self.manager.get_rss(url)
        for entry in rss.entries:
            id, guid = legistar_id_guid(entry.link)
            meeting = self.session.query(Meeting).get(id)
            if meeting is None:
                print("adding meeting {} from rss".format(id))
                try:
                    self.manager.add_meeting_from_rss(entry)
                except IntegrityError:
                    pass
            else:
                print("Meeting {} already present.".format(id))

    def set_meeting(self, meeting):
        self.meeting = meeting
        self.parsed = self.collector.collect('meeting', link=self.meeting.link)

    def add_meetings(self, year=None):
        """This adds full meetings which have been added to
        meetings table by rss."""
        query = self.session.query(Meeting)
        if year is not None:
            # https://stackoverflow.com/a/1453610/1869821
            query = query.filter(extract('year', Meeting.date) == year)
        for meeting in query:
            self.set_meeting(meeting)
            self.add_meeting(meeting)

    def add_zipped_meetings(self):
        """This adds full meetings which have been added to
        meetings table by rss."""
        rssfiles = [f for f in self.collector.zfile.namelist()
                    if f.endswith('.rss')]
        if len(rssfiles) != 1:
            # FIXME return a better error
            raise RuntimeError("bad rssfiles {}".format(rssfiles))
        rssname = rssfiles[0]
        rss_content = self.collector.get_content(rssname)
        parsed = feedparser.parse(rss_content)
        for entry in parsed.entries:
            self.set_meeting(entry)
            meeting_id = self.parsed['info']['id']
            meeting = self.session.query(Meeting).get(meeting_id)
            self.add_meeting(meeting)
            del self.parsed

    def add_meeting(self, meeting):
        print("Merging meeting {}".format(meeting.title))
        for item in self.parsed['items']:
            self.add_meeting_item(item)
        self.manager._merge_collected_meeting_items(meeting, self.parsed)
        self.manager._merge_collected_meeting(meeting, self.parsed)

    def add_pickled_meeting(self, meeting):
        meeting_id = meeting['info']['id']
        for item in meeting['items']:
            self.add_collected_item(item)
        self.manager._merge_pickled_meeting_items(meeting_id, meeting['items'])

    def merge_nonfinal(self):
        filtered = or_(Meeting.minutes_status == None, # noqa
                       Meeting.minutes_status != 'Final')
        qmeetings = self.session.query(Meeting).filter(filtered)
        meetings = qmeetings.all()
        for meeting in meetings:
            collected = self.collector.collect('meeting', link=meeting.link)
            self.manager._merge_collected_meeting(meeting, collected)
            print("Merging meeting %d" % meeting.id)

    def convert_binary_item(self, item):
        if b'id' in item:
            sitem = {}
            for key in item:
                sitem[key.decode()] = item[key]
            item = sitem
        return item

    def add_collected_actions(self, item_id, actions):
        for action in actions:
            dbaction = self.session.query(Action).get(action['id'])
            if dbaction is None:
                print("adding action %d to database." % action['id'])
                self.manager.add_collected_action(item_id, action)

    def add_collected_item(self, item):
        item = self.convert_binary_item(item)
        if not check_dupe_item(self.session, item):
            print("adding item %d to database." % item['id'])
            self.manager._add_collected_legislation_item(item)
        self.add_collected_actions(item['id'], item['actions'])

    def add_meeting_item(self, parsed_item):
        item = self.collector.collect('item', link=parsed_item['item_page'])
        item = self.convert_binary_item(item)
        if not check_dupe_item(self.session, item):
            print("adding item %d to database." % item['id'])
            self.manager._add_collected_legislation_item(item)
        if 'action_details' not in item:
            action_details = []
        else:
            action_details = item['action_details']
        self.add_item_actions(item['id'], action_details)

    def add_item_actions(self, item_id, action_details):
        for link in action_details:
            action = self.collector.collect('action', link=link)
            dbaction = self.session.query(Action).get(action['id'])
            if dbaction is None:
                print("adding action %d to database." % action['id'])
                self.manager.add_collected_action(item_id, action)

    def delete_all(self):
        delete_all(self.session)

    def export_all(self):
        return export_all(self.session)

    def add_meetings_for_year(self, year):
        content = self.collector.get_rss_content(year)
        rss = feedparser.parse(content)
        self.add_rss_meetings('ignore', rss=rss)
