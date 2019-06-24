from datetime import datetime, date

from sqlalchemy import Column, ForeignKey

# column types
from sqlalchemy import Integer, String, Unicode
from sqlalchemy import Boolean, Date, LargeBinary
from sqlalchemy import PickleType
from sqlalchemy import Enum
from sqlalchemy import DateTime

from sqlalchemy.orm import relationship, backref

from sqlalchemy.ext.declarative import declarative_base

from .legistar import legistar_host

Base = declarative_base()

####################################
# Data Types                      ##
####################################


FileType = Enum('agenda', 'minutes', 'attachment',
                name='lgr_file_type_enum')

AgendaItemType = Enum('public', 'presentation', 'policy', 'routine', 'unknown',
                      name='agenda_item_type_enum')

VoteType = Enum('Yea', 'Nay', 'Abstain', 'Absent', 'Present',
                'TEL-No Vote', 'Recuse',
                name='lgr_vote_type_enum')

AgendaItemTypeMap = dict(V='presentation', VI='policy',
                         VII='routine', IV='unknown')
AgendaItemTypeMap['I'] = 'public'


CacheType = Enum('action', 'departments', 'item', 'meeting',
                 'people', 'rss-2011', 'rss-2012', 'rss-2013',
                 'rss-this-month',
                 name='lgr_cache_type_enum')


class SerialBase(object):
    def serialize(self):
        data = dict()
        table = self.__table__
        for column in table.columns:
            name = column.name
            try:
                pytype = column.type.python_type
            except NotImplementedError:
                print("NOTIMPLEMENTEDERROR", column.type)
            value = getattr(self, name)
            if pytype is datetime or pytype is date:
                if value is not None:
                    value = value.isoformat()
            data[name] = value
        return data
####################################
#  Tables                         ##
####################################


class MainCache(Base, SerialBase):
    __tablename__ = 'lgr_main_cache'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(200), unique=True)
    retrieved = Column(DateTime)
    updated = Column(DateTime)
    content = Column(PickleType)


class Department(Base, SerialBase):
    __tablename__ = 'lgr_departments'
    id = Column(Integer, primary_key=True)
    guid = Column(String)
    name = Column(String)

    def __init__(self, id, guid):
        self.id = id
        self.guid = guid
        self.name = None

    def __repr__(self):
        return '<Dept: %d - %s>' % (self.id, self.name)


class Person(Base, SerialBase):
    __tablename__ = 'lgr_people'

    id = Column(Integer, primary_key=True)
    guid = Column(String)
    firstname = Column(String)
    lastname = Column(String)
    website = Column(String)
    photo_link = Column(String)
    notes = Column(String)

    def __init__(self):
        self.id = None
        self.guid = None
        self.firstname = None
        self.lastname = None
        self.website = None
        self.photo_link = None
        self.notes = None

    def __repr__(self):
        msg = '<Person: {} ({} {})>'
        return msg.format(self.id, self.firstname, self.lastname)


class Meeting(Base, SerialBase):
    __tablename__ = 'lgr_meetings'

    id = Column(Integer, primary_key=True)
    guid = Column(String)
    title = Column(String)
    date = Column(Date)
    time = Column(String)
    link = Column(String)
    dept_id = Column(Integer, ForeignKey('lgr_departments.id'))
    agenda_status = Column(String)
    minutes_status = Column(String)
    rss = Column(PickleType)
    updated = Column(DateTime)

    def __init__(self):
        self.id = None
        self.guid = None
        self.title = None
        self.date = None
        self.time = None
        self.link = None
        self.dept_id = None
        self.agenda_link = None
        self.agenda_status = None
        self.minutes_link = None
        self.minutes_status = None
        self.rss = None
        self.updated = None

    def __repr__(self):
        return "<Meeting(%d): '%s'>" % (self.id, self.title)


class Item(Base, SerialBase):
    __tablename__ = 'lgr_items'

    id = Column(Integer, primary_key=True)
    guid = Column(String)
    file_id = Column(String)
    filetype = Column(String)
    name = Column(Unicode)
    title = Column(Unicode)
    status = Column(String)
    passed = Column(Date)
    on_agenda = Column(Date)
    introduced = Column(Date)
    acted_on = Column(Boolean)

    def __init__(self):
        self.id = None
        self.guid = None
        self.file_id = None
        self.filetype = None
        self.name = None
        self.title = None
        self.status = None
        self.passed = None
        self.on_agenda = None
        self.introduced = None
        self.acted_on = False

    def __repr__(self):
        return "<Item: %s, id: %d>" % (self.file_id, self.id)

    def link(self):
        tmpl = 'LegislationDetail.aspx?ID=%d&GUID=%s&Options=&Search='
        return tmpl % (self.id, self.guid)


class MeetingItem(Base, SerialBase):
    __tablename__ = 'lgr_meeting_item'

    meeting_id = Column('meeting_id', Integer,
                        ForeignKey('lgr_meetings.id'),
                        primary_key=True)
    item_id = Column('item_id', Integer,
                     ForeignKey('lgr_items.id'),
                     primary_key=True)

    agenda_num = Column(String)
    # type = Column('type', AgendaItemType)
    type = Column('type', String)
    # order is by type
    order = Column('order', Integer)
    # item order is order of all items
    # this allows unknown council letter to mayor
    # to stay on top of meeting items for sept 18 2012
    item_order = Column('item_order', Integer)
    # I decided to consider keeping track of item
    # versions, and it probably should go in the
    # items table, but for now it is here.
    version = Column('version', Integer)

    def __init__(self, meeting_id, item_id):
        self.meeting_id = meeting_id
        self.item_id = item_id
        self.agenda_num = None
        self.type = None
        self.order = None
        self.item_order = None

    def __repr__(self):
        return "<MeetingItem %d:%d>" % (self.meeting_id, self.item_id)


class Action(Base, SerialBase):
    __tablename__ = 'lgr_actions'

    id = Column(Integer, primary_key=True)
    guid = Column(String)
    file_id = Column(String)
    filetype = Column(String)
    mover_id = Column(Integer, ForeignKey('lgr_people.id'))
    seconder_id = Column(Integer, ForeignKey('lgr_people.id'))
    result = Column(String)
    agenda_note = Column(String)
    minutes_note = Column(String)
    action = Column(String)
    action_text = Column(Unicode)
    # item_id = Column(Integer, ForeignKey('items.id'))

    # related

    def __init__(self):
        self.id = None
        self.guid = None
        self.file_id = None
        self.filetype = None
        self.mover_id = None
        self.seconder_id = None
        self.result = None
        self.agenda_note = None
        self.minutes_note = None
        self.action = None
        self.action_text = None

    def __repr__(self):
        return "<Action: %s, id: %d>" % (self.file_id, self.id)


class ItemAction(Base, SerialBase):
    __tablename__ = 'lgr_item_action'

    item_id = Column('item_id', Integer,
                     ForeignKey('lgr_items.id'),
                     primary_key=True)
    action_id = Column('action_id', Integer,
                       ForeignKey('lgr_actions.id'),
                       primary_key=True)

    def __init__(self, item_id, action_id):
        self.item_id = item_id
        self.action_id = action_id

    def __repr__(self):
        return "<ItemAction %d:%d>" % (self.item_id, self.action_id)


class ActionVote(Base, SerialBase):
    __tablename__ = 'lgr_action_vote'

    action_id = Column('action_id', Integer,
                       ForeignKey('lgr_actions.id'),
                       primary_key=True)
    ward1 = Column('ward1', VoteType)
    ward1_person_id = Column('ward1_person_id', Integer,
                             ForeignKey('lgr_people.id'))

    ward2 = Column('ward2', VoteType)
    ward2_person_id = Column('ward2_person_id', Integer,
                             ForeignKey('lgr_people.id'))
    ward3 = Column('ward3', VoteType)
    ward3_person_id = Column('ward3_person_id', Integer,
                             ForeignKey('lgr_people.id'))
    ward4 = Column('ward4', VoteType)
    ward4_person_id = Column('ward4_person_id', Integer,
                             ForeignKey('lgr_people.id'))
    ward5 = Column('ward5', VoteType)
    ward5_person_id = Column('ward5_person_id', Integer,
                             ForeignKey('lgr_people.id'))


class File(Base, SerialBase):
    __tablename__ = 'lgr_files'

    id = Column(Integer,
                primary_key=True)
    http_info = Column(PickleType)
    content = Column(LargeBinary)
    link = Column(String)

    def __init__(self):
        self.id = None
        self.http_info = None
        self.content = None
        self.link = None

    def __repr__(self):
        return "<File:  id: %d>" % self.id


class Agenda(Base, SerialBase):
    __tablename__ = 'lgr_agendas'

    id = Column(Integer, ForeignKey('lgr_meetings.id'),
                primary_key=True)
    guid = Column(String)
    http_info = Column(PickleType)
    content = Column(LargeBinary)
    link = Column(String)

    def __init__(self):
        self.id = None
        self.guid = None
        self.http_info = None
        self.content = None
        self.link = None

    def __repr__(self):
        return "<Agenda:  id: %d>" % self.id


class Minutes(Base, SerialBase):
    __tablename__ = 'lgr_minutes'

    id = Column(Integer, ForeignKey('lgr_meetings.id'),
                primary_key=True)
    guid = Column(String)
    http_info = Column(PickleType)
    content = Column(LargeBinary)
    link = Column(String)

    def __init__(self):
        self.id = None
        self.guid = None
        self.http_info = None
        self.content = None
        self.link = None

    def __repr__(self):
        return "<Minutes:  id: %d>" % self.id


class Attachment(Base, SerialBase):
    __tablename__ = 'lgr_attachments'

    id = Column(Integer, primary_key=True)
    guid = Column(String)
    name = Column(String)
    http_info = Column(PickleType)
    content = Column(LargeBinary)
    link = Column(String)
    item_id = Column(Integer, ForeignKey('lgr_items.id'))

    def __init__(self):
        self.id = None
        self.guid = None
        self.name = None
        self.http_info = None
        self.content = None
        self.link = None
        self.item_id = None

    def __repr__(self):
        return "<Attachment:  id: %d>" % self.id

    def get_link(self):
        return 'https://%s/%s' % (legistar_host, self.link)


class Tag(Base, SerialBase):
    __tablename__ = 'lgr_tagnames'

    name = Column(String, primary_key=True)

    def __init__(self):
        self.name = None

    def __repr__(self):
        return "<Tag: %s>" % self.name


class ItemTag(Base, SerialBase):
    __tablename__ = 'lgr_item_tags'

    id = Column(Integer, ForeignKey('lgr_items.id'),
                primary_key=True)
    tag = Column(String, ForeignKey('lgr_tagnames.name'),
                 primary_key=True)

    def __init__(self):
        self.id = None
        self.tag = None

    def __repr__(self):
        return "<ItemTag: %s:%s>" % (self.id, self.tag)


# ItemTag relationships
Tag.items = relationship(Item, backref='tags',
                         order_by=Item.id,
                         secondary='lgr_item_tags')


#######################################################
#######################################################

Department.meetings = relationship(Meeting, order_by=Meeting.date)

# Meeting relationships
meeting_backref = backref('meeting', uselist=False)

Meeting.dept = relationship(Department)


Meeting.items = relationship(Item, backref='meetings',
                             secondary='lgr_meeting_item')

Meeting.meeting_items = relationship(MeetingItem,
                                     order_by=MeetingItem.item_order)

Meeting.agenda = relationship(Agenda, uselist=False,
                              backref=meeting_backref)
Meeting.minutes = relationship(Minutes, uselist=False,
                               backref=meeting_backref)


# MeetingItem relationships
MeetingItem.meeting = relationship(Meeting)
MeetingItem.item = relationship(Item)


# Item relationships
Item.actions = relationship(Action, backref='items',
                            order_by=Action.id,
                            secondary='lgr_item_action')

Item.attachments = relationship(Attachment, backref='item',
                                order_by=Attachment.id)


# Action relationships
Action.item = relationship(Item, backref='items',
                           secondary='lgr_item_action')

Action.mover = relationship(Person, primaryjoin='Action.mover_id == Person.id')
Action.seconder = relationship(Person,
                               primaryjoin='Action.seconder_id == Person.id')
