from typing import TYPE_CHECKING, Any

from sqlalchemy.event import listen, remove


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SQLAlchemyQueryCounter:
    """Check SQLAlchemy query count.

    Usage:
        with DBStatementCounter(session, 2) as ctr:
            conn.execute("SELECT 1")
            conn.execute("SELECT 1")

    """

    def __init__(self, session: "Session", query_count: int) -> None:
        self.engine = session.get_bind()
        self._query_count = query_count
        self.count = 0

    def __enter__(self) -> "SQLAlchemyQueryCounter":
        listen(self.engine, "after_execute", self._callback)
        return self

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> None:
        remove(self.engine, "after_execute", self._callback)
        assert self.count == self._query_count, (
            "Executed: "
            + str(self.count)
            + " != Required: "
            + str(self._query_count)
        )

    def _callback(self, *_: Any) -> None:
        self.count += 1
