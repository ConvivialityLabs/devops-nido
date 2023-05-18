def test_gql_response(test_schema):
    query = "{activeUser{personalName}}"
    context = {"user_id": 1, "community_id": 1}
    result = test_schema.execute_sync(query, context_value=context)
    assert result.data["activeUser"]["personalName"] == "Dylan"
