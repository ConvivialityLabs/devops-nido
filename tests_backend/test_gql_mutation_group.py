from sqlalchemy import func, select

from nido_backend.db_models import DBGroup, DBGroupMembership

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
    old_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
    var_dir = {"input": {"name": "Test Name"}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_new_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBGroupMembership))
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
    var_dir = {"input": {"group": "Z3JvdXA6Mg==", "name": "CEO"}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_rename_query, var_dir, context)
    db_val = db_session.get(DBGroup, 2)
    assert db_val.name == "CEO"


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
    old_count = db_session.scalar(select(func.count()).select_from(DBGroup))
    var_dir = {"input": {"group": "Z3JvdXA6Mg=="}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_delete_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBGroup))
    assert new_count == old_count - 1
