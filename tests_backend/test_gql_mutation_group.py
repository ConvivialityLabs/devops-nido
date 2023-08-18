from sqlalchemy import func, select

from nido_backend.db_models import DBGroup, DBGroupMembership
from nido_backend.gql_helpers import encode_gql_id

test_new_query = """
mutation TestNew($input: [NewGroupInput!] = {name: ""}) {
  groups {
    new(input: $input) {
      groups {
        name
      }
    }
  }
}"""


def test_gql_mutation_new_group_success(test_schema, db_session):
    old_count = db_session.scalar(select(func.count()).select_from(DBGroup))
    var_dir = {"input": {"name": "Test Name"}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_new_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBGroup))
    assert new_count == old_count + 1


test_rename_query = """
mutation TestRename($input: [RenameGroupInput!] = {group: "", name: ""}) {
  groups {
    rename(input: $input) {
      groups {
        name
      }
    }
  }
}"""


def test_gql_mutation_rename_group_success(test_schema, db_session):
    group_gql_id = encode_gql_id("group", 2)
    var_dir = {"input": {"group": group_gql_id, "name": "CEO"}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_rename_query, var_dir, context)
    db_val = db_session.get(DBGroup, 2)
    assert db_val.name == "CEO"


test_add_members_query = """
mutation MyMutation($input: [AddMembersGroupInput!] = {group: "", members: ""}) {
  groups {
    addMembers(input: $input) {
      groups {
        name
      }
    }
  }
}"""


def test_gql_mutation_add_members_group_success(test_schema, db_session):
    group_gql_id = encode_gql_id("group", 2)
    user_gql_id = encode_gql_id("user", 8)
    old_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
    var_dir = {"input": {"group": group_gql_id, "members": user_gql_id}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_add_members_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
    assert new_count == old_count + 1


test_remove_members_query = """
mutation MyMutation($input: [RemoveMembersGroupInput!] = {group: "", members: ""}) {
  groups {
    removeMembers(input: $input) {
      groups {
        name
      }
    }
  }
}"""


def test_gql_mutation_remove_members_group_success(test_schema, db_session):
    group_gql_id = encode_gql_id("group", 1)
    user_gql_id = encode_gql_id("user", 3)
    old_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
    var_dir = {"input": {"group": group_gql_id, "members": user_gql_id}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_remove_members_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
    assert new_count == old_count - 1


test_delete_query = """
mutation TestDelete($input: [DeleteGroupInput!] = {group: ""}) {
  groups {
    delete(input: $input) {
      errors {
        message
      }
    }
  }
}"""


def test_gql_mutation_delete_group_success(test_schema, db_session):
    group_gql_id = encode_gql_id("group", 2)
    old_count = db_session.scalar(select(func.count()).select_from(DBGroup))
    var_dir = {"input": {"group": group_gql_id}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_delete_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBGroup))
    assert new_count == old_count - 1
