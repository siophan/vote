from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session


def insert_ignore(db: Session, model):
    """Dialect-aware INSERT ... ON CONFLICT DO NOTHING builder."""
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return postgresql.insert(model)
    if dialect == "sqlite":
        return sqlite.insert(model)
    raise RuntimeError(f"unsupported dialect: {dialect}")
