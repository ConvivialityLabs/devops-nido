from sqlalchemy import func, select

from nido_backend.db_models import DBContactMethod
from nido_backend.gql_helpers import encode_gql_id

test_new_email_query = """
mutation TestNewEmail($input: [NewEmailCMInput!] = {email: ""}) {
  contactMethods {
    newEmail(input: $input) {
      emailContacts {
        id
      }
    }
  }
}"""


def test_gql_mutation_rename_group_success(test_schema, db_session):
    old_count = db_session.scalar(select(func.count()).select_from(DBContactMethod))
    var_dir = {"input": {"email": "testunique@example.com"}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_new_email_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBContactMethod))
    assert new_count == old_count + 1


test_delete_query = """
mutation TestDelete($input: [DeleteCMInput!] = {id: ""}) {
  contactMethods {
    delete(input: $input) {
      errors {
        message
      }
    }
  }
}"""


def test_gql_mutation_delete_group_success(test_schema, db_session):
    cm_gql_id = encode_gql_id("contact_method", 1)
    old_count = db_session.scalar(select(func.count()).select_from(DBContactMethod))
    var_dir = {"input": {"id": cm_gql_id}}
    context = {"user_id": 1, "community_id": 1}
    test_schema.execute_sync(test_delete_query, var_dir, context)
    new_count = db_session.scalar(select(func.count()).select_from(DBContactMethod))
    assert new_count == old_count - 1
