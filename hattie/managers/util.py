from datetime import datetime

from ..database import AgendaItemTypeMap


def convert_range_to_datetime(start, end):
    "start and end are timestamps"
    start = datetime.fromtimestamp(float(start))
    end = datetime.fromtimestamp(float(end))
    return start, end


def convert_agenda_number(agenda_number):
    delimiter = '.-'
    for delimiter in ['.-', '. - ', ' - ', '-']:
        if delimiter in agenda_number:
            break
    if delimiter in agenda_number:
        itemtype, order = agenda_number.split(delimiter)
        itemtype = AgendaItemTypeMap[itemtype]
        order = int(order)
    else:
        itemtype = 'unknown'
        if agenda_number:
            order = int(agenda_number)
        else:
            order = None
    print("ITEM", itemtype, order)
    return itemtype, order
