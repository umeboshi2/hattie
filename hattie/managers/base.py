
class BaseManager(object):
    def __init__(self, session):
        self.session = session

    def set_session(self, session):
        self.session = session

    def _range_filter(self, query, column, start, end):
        query = query.filter(column >= start)
        query = query.filter(column <= end)
        return query

    def query(self):
        raise NotImplementedError("Override me")

    def get(self, id):
        return self.query().get(id)

    def all(self):
        return self.query().all()
