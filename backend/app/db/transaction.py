from contextlib import contextmanager
from collections.abc import Iterator
from sqlalchemy.orm import Session


@contextmanager
def transaction(db: Session) -> Iterator[Session]:
    """Execute a logical unit of work atomically.

    Services that coordinate multiple repositories/domain operations can use this
    helper so a failure rolls the whole unit back instead of leaving partial state.
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
