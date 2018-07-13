import transaction

from ..database import Department, Person
from .base import BaseManager


class DepartmentManager(BaseManager):
    def query(self):
        return self.session.query(Department)

    def add(self, id, guid, name):
        with transaction.manager:
            dept = Department(id, guid)
            dept.name = name
            self.session.add(dept)
        return self.session.merge(dept)


class PersonManager(BaseManager):
    def query(self):
        return self.session.query(Person)

    def _notrans_add(self, data):
        p = Person()
        for key, value in list(data.items()):
            setattr(p, key, value)
        self.session.add(p)
        return p

    def add(self, data):
        with transaction.manager:
            p = self._notrans_add(data)
        return self.session.merge(p)

    def add_people(self, people):
        plist = []
        with transaction.manager:
            for pinfo in people:
                p = self._notrans_add(pinfo)
                plist.append(p)
        return [self.session.merge(p) for p in plist]
