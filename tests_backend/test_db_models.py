import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from nido_backend.db_models import (
    DBCommunity,
    DBEmailContact,
    DBGroup,
    DBGroupMembership,
    DBResidenceOccupancy,
    DBRight,
)
from nido_backend.enums import PermissionsFlag


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


def test_group_ondelete_constraint(db_session):
    group = db_session.get(DBGroup, 1)
    db_session.delete(group)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_group_membership_delete_cascade(db_session):
    group = db_session.get(DBGroup, 2)
    old_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
    db_session.delete(group)
    db_session.commit()
    new_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
    assert old_count > new_count


def test_right_permissions_attr_on_object():
    new_right = DBRight(community_id=0, name="Unlimited Right")
    for member in PermissionsFlag:
        setattr(new_right, member.name.lower(), member)
    assert new_right.permissions == ~PermissionsFlag(0)


def test_right_permissions_attr_on_class(db_session):
    all_permissions = ~PermissionsFlag(0)
    community_count = db_session.scalar(select(func.count()).select_from(DBCommunity))
    right_count = db_session.scalar(
        select(func.count())
        .select_from(DBRight)
        .where(DBRight.permissions == all_permissions.value)
    )
    assert right_count == community_count


def test_right_permits_hybrid_method_on_class(db_session):
    some_permissions = PermissionsFlag.CAN_DELEGATE | PermissionsFlag.CREATE_GROUPS
    right_count = db_session.scalar(
        select(func.count())
        .select_from(DBRight)
        .where(DBRight.permits(some_permissions.value))
    )
    assert right_count > 0
