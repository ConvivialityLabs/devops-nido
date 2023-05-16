import pytest
from sqlalchemy.exc import IntegrityError

from nido_backend.db_models import DBEmailContact, DBResidenceOccupancy


def test_residence_occupany_foreign_key(db_session):
    invalid_entry = DBResidenceOccupancy(community_id=2, residence_id=1, user_id=1)
    db_session.add(invalid_entry)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_email_constraint(db_session):
    original = db_session.get(DBEmailContact, 1)
    dup_email = DBEmailContact(user_id=original.user_id + 1, email=original.email)
    db_session.add(dup_email)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_contact_method_user_foreign_key(db_session):
    email = DBEmailContact(user_id=1000000, email="testunique@example.com")
    db_session.add(email)
    with pytest.raises(IntegrityError):
        db_session.commit()
