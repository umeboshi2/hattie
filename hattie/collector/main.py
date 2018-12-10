import os
import pickle as Pickle
from datetime import datetime
import zipfile

from ..util import legistar_id_guid

from .people import PeopleCollector
from .departments import DeptCollector
from .meeting import MeetingCollector
from .item import ItemCollector
from .action import ActionCollector


class PickleCollector(object):
    def __init__(self):
        self.people = PeopleCollector()
        self.depts = DeptCollector()
        self.meeting = MeetingCollector()
        self.item = ItemCollector()
        self.action = ActionCollector()
        self.dir = 'data'

        self._collectors = dict(people=self.people,
                                depts=self.depts,
                                meeting=self.meeting,
                                item=self.item,
                                action=self.action)

    def _collector(self, type):
        return self._collectors[type]

    def _filename(self, type, id=None):
        if type == 'people':
            filename = 'people.pickle'
        elif type == 'depts':
            filename = 'departments.pickle'
        elif type == 'meeting':
            filename = 'meeting-%d.pickle' % id
        elif type == 'item':
            filename = 'item-%d.pickle' % id
        elif type == 'action':
            filename = 'action-%d.pickle' % id
        else:
            raise RuntimeError('unknown type')
        return os.path.join(self.dir, filename)

    def get_filename(self, type, id):
        return self._filename(type, id)

    def _dbname(self, type, id=None):
        if type == 'people':
            dbname = 'people'
        elif type == 'depts':
            dbname = 'departments'
        elif type == 'meeting':
            dbname = 'meeting-%d' % id
        elif type == 'item':
            dbname = 'item-%d' % id
        elif type == 'action':
            dbname = 'action-%d' % id
        else:
            raise RuntimeError('unknown type')
        return dbname

    def make_cache_object(self, type, link=None):
        from ..database import MainCache
        id = None
        if type in ['meeting', 'item', 'action']:
            id, guid = legistar_id_guid(link)
        filename = self._filename(type, id)
        dbname = self._dbname(type, id)
        if os.path.isfile(filename):
            content = Pickle.load(open(filename, 'rb'), encoding='utf-8')
            now = datetime.now()
            mc = MainCache()
            mc.name = dbname
            mc.retrieved = now
            mc.updated = now
            mc.content = content
        else:
            raise RuntimeError("No file present %s" % filename)
        return mc

    def collect(self, type, link=None):
        id = None
        if type in ['meeting', 'item', 'action']:
            id, guid = legistar_id_guid(link)
        filename = self._filename(type, id)
        if not os.path.isfile(filename):
            print("Retrieving %s from legistar..." % filename)
            collector = self._collector(type)
            if link is not None:
                if not link.startswith('http'):
                    link = collector.url_prefix + link
                else:
                    if type != 'meeting':
                        raise RuntimeError("BAD LINK", link)
                print("Retrieving", link)
                collector.set_url(link)
            collector.collect()
            data = dict(result=collector.result, content=collector.content)
            Pickle.dump(data, open(filename, 'wb'))
        try:
            data = Pickle.load(open(filename, 'rb'))
        except UnicodeDecodeError:
            data = Pickle.load(open(filename, 'rb'), encoding='bytes')
        return data['result']


class _MainCollector(PeopleCollector, DeptCollector,
                     MeetingCollector, ItemCollector,
                     ActionCollector):
    pass


class MainCollector(_MainCollector):
    def __init__(self):
        _MainCollector.__init__(self)
        self.dept_url = 'https://hattiesburg.legistar.com/Departments.aspx'
        self.people_url = 'https://hattiesburg.legistar.com/People.aspx'
        self.url_prefix = 'https://hattiesburg.legistar.com/'
        self._map = dict(people=PeopleCollector,
                         dept=DeptCollector,
                         meeting=MeetingCollector,
                         item=ItemCollector,
                         action=ActionCollector)

    def collect(self, ctype):
        self._map[ctype].collect(self)


class ZipCollector(PickleCollector):
    def __init__(self, fileobj):
        super(ZipCollector, self).__init__()
        self.zfile = zipfile.ZipFile(fileobj)

    def collect(self, type, link=None):
        id = None
        if type in ['meeting', 'item', 'action']:
            id, guid = legistar_id_guid(link)
        filename = self._filename(type, id)
        data = Pickle.load(self.zfile.open(filename))
        r = data['result']
        del data
        return r

    def get_content(self, filename):
        return self.zfile.read(filename)

    def get_rss_content(self, year):
        filename = "data/rss-{}.rss".format(year)
        return self.get_content(filename)
