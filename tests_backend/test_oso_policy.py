import pytest

from nido_backend.authorization import oso
from nido_backend.db_models import (
    DBAssociate,
    DBCommunity,
    DBEmailContact,
    DBGroup,
    DBGroupMembership,
    DBResidenceOccupancy,
    DBRight,
    DBUser,
)
from nido_backend.enums import PermissionsFlag


def test_group_member_role_rule():
    user = DBUser(family_name="test", personal_name="example")
    user.id = 42
    associate = DBAssociate(
        community_id=21, user_id=42, family_name="test", personal_name="example"
    )
    group = DBGroup(community_id=21, name="test group")
    group.custom_members.append(associate)
    assert oso.query_rule_once("has_role", user, "member", group)


def test_group_manager_role_rule():
    user = DBUser(family_name="test", personal_name="example")
    user.id = 36
    associate = DBAssociate(
        community_id=21, user_id=36, family_name="test", personal_name="example"
    )
    parent_group = DBGroup(community_id=21, name="parent group")
    parent_group.id = 42
    child_group = DBGroup(community_id=21, name="child group")
    child_group.id = 43
    child_group.managed_by = parent_group
    parent_group.custom_members.append(associate)
    assert oso.query_rule_once("has_role", user, "manager", child_group)
