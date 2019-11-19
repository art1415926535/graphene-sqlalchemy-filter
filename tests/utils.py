# Database
from sqlalchemy.event import listen, remove


class SQLAlchemyQueryCounter:
    """
    Check SQLAlchemy query count.

    Usage:
        with DBStatementCounter(session, 2) as ctr:
            conn.execute("SELECT 1")
            conn.execute("SELECT 1")

    """

    def __init__(self, session, query_count):
        self.engine = session.get_bind()
        self._query_count = query_count
        self.count = 0

    def __enter__(self):
        listen(self.engine, 'after_execute', self._callback)
        return self

    def __exit__(self, *_):
        remove(self.engine, 'after_execute', self._callback)
        assert self.count == self._query_count, (
            'Executed: '
            + str(self.count)
            + ' != Required: '
            + str(self._query_count)
        )

    def _callback(self, *_):
        self.count += 1
