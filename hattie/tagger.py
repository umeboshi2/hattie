# from sqlalchemy.orm import joinedload
# from sqlalchemy.orm import joinedload_all
# from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.exc import NoResultFound

from .database import Item
from .database import Tag, ItemTag

import transaction


DEFAULT_TAGNAMES = [
    'PlanningCommission',
    'NuncProTunc',
    'Ordinance',
    'CDBG',
    'Entitlement',
    'HOME',
    'ClaimsDocket',
    'MonthlyBudgetReport',
    'FEMA',
    'HomelandSecurity',
    'Appointment',
    ]


def add_tag_names(session):
    for name in DEFAULT_TAGNAMES:
        query = session.query(Tag).filter(Tag.name == name)
        try:
            tag = query.one()
        except NoResultFound:
            # print "adding", name
            tag = Tag()
            tag.name = name
            session.add(tag)
            transaction.commit()


def tag_item(session, item, tagname):
    query = session.query(ItemTag).filter(ItemTag.id == item.id)
    query = query.filter(ItemTag.tag == tagname)
    try:
        item_tag = query.one()
        # msg = "Skipping tagging %s to item %s"
        # print msg % (tagname, item.file_id)
    except NoResultFound:
        item_tag = ItemTag()
        item_tag.id = item.id
        item_tag.tag = tagname
        # msg = "Tagging %s to item %s"
        # print msg % (tagname, item.file_id)
        session.add(item_tag)


def tag_item_for_ordinance(session, item):
    title = item.title
    title = title.lower()
    if 'ordinance' in title:
        tag_item(session, item, 'Ordinance')
        transaction.commit()


def tag_item_for_planning_commission(session, item):
    title = item.title
    if "Hattiesburg Planning Commission" in title:
        tag_item(session, item, 'PlanningCommission')


def tag_item_for_nunc_pro_tunc(session, item):
    title = item.title
    title = title.lower()
    if '(nunc pro tunc)' in title:
        tag_item(session, item, 'NuncProTunc')


def tag_item_for_entitlement(session, item):
    title = item.title
    title = title.lower()
    if '{entitlement}' in title:
        tag_item(session, item, 'Entitlement')


def tag_item_for_cdbg(session, item):
    title = item.title
    if 'CDBG' in title:
        tag_item(session, item, 'CDBG')
    if 'Community Development Block Grant' in title:
        tag_item(session, item, 'CDBG')


def tag_item_for_cdbg_and_entitlement(session, item):
    title = item.title
    if '{Entitlement - CDBG}' in title:
        tag_item(session, item, 'CDBG')
        tag_item(session, item, 'Entitlement')


def tag_item_for_HOME(session, item):
    title = item.title
    if 'HOME Program' in title:
        tag_item(session, item, 'HOME')


def tag_item_for_Claims_Docket(session, item):
    title = item.title
    title = title.lower()
    if 'claims docket' in title:
        tag_item(session, item, 'ClaimsDocket')


def tag_item_for_monthly_budget_report(session, item):
    title = item.title
    title = title.lower()
    if 'monthly budget report' in title:
        tag_item(session, item, 'MonthlyBudgetReport')


def tag_item_for_FEMA(session, item):
    title = item.title
    if ' FEMA ' in title:
        tag_item(session, item, 'FEMA')


def tag_item_for_Homeland_Security(session, item):
    title = item.title
    if 'Homeland Security' in title:
        tag_item(session, item, 'HomelandSecurity')


def tag_item_for_appointment(session, item):
    title = item.title
    title = title.lower()
    if 'appoint' in title:
        tag_item(session, item, 'Appointment')

    pass


TAGGERS = [
    tag_item_for_ordinance,
    tag_item_for_planning_commission,
    tag_item_for_nunc_pro_tunc,
    tag_item_for_entitlement,
    tag_item_for_cdbg,
    tag_item_for_cdbg_and_entitlement,
    tag_item_for_HOME,
    tag_item_for_Claims_Docket,
    tag_item_for_monthly_budget_report,
    tag_item_for_FEMA,
    tag_item_for_appointment,
    ]


def tag_items(session, items):
    for item in items:
        for tagger in TAGGERS:
            tagger(session, item)
        transaction.commit()


def tag_all_items(session):
    query = session.query(Item)
    tag_items(session, query)
