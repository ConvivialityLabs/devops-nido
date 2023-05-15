import pytest
from sqlalchemy.exc import IntegrityError

from nido_backend.db_models import DBEmailContact, DBUser


def test_user_community_foreign_key(db_session):
    user = DBUser(community_id=100000, personal_name="John", family_name="Doe")
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_email_constraint(db_session):
    dup_email = DBEmailContact(user_id=2, email="ccaban0@google.co.jp")
    db_session.add(dup_email)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_contact_method_user_foreign_key(db_session):
    email = DBEmailContact(user_id=1000000, email="testunique@example.com")
    db_session.add(email)
    with pytest.raises(IntegrityError):
        db_session.commit()
