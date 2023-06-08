import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from strawberry import Schema

from generate_mock_data import seed_db
from nido_backend.db_models import Base
from nido_backend.gql_schema import SchemaContext, create_schema


class TestSchema(Schema):
    def __init__(self, db_session, *args, **kwargs):
        self.db_session = db_session
        super().__init__(*args, **kwargs)

    def execute_sync(
        self, query, variable_values=None, context_value={}, *args, **kwargs
    ):
        context = SchemaContext([], self.db_session, **context_value)
        return super().execute_sync(query, variable_values, context, *args, **kwargs)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db_session:
        seed_db(db_session)

    yield engine

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()

    yield scoped_session(sessionmaker(autoflush=False, bind=connection))

    # If the line below changes its line number, it will start raising
    # warnings. Update pyproject.toml to silence.
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_schema(db_session):
    return create_schema(TestSchema, db_session=db_session)
