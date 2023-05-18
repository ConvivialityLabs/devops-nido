#  Nido main.py
#  Copyright (C) John Arnold
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
from typing import Any, Optional, Union

import strawberry
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from strawberry.asgi import GraphQL, Request, Response, WebSocket
from strawberry.extensions import SchemaExtension

from .gql_mutation import Mutation
from .gql_query import EmailContact, Query


class GraphQLWithDB(GraphQL):
    def __init__(self, db_engine: Engine, *args, **kwargs) -> None:
        self.Session = scoped_session(sessionmaker(db_engine))
        super().__init__(*args, **kwargs)

    async def get_context(
        self, request: Union[Request, WebSocket], response: Optional[Response] = None
    ) -> Any:
        return {
            "db_session": self.Session,
            "request": request,
            "response": response,
            "user_id": request.cookies.get("user_id"),
            "community_id": request.cookies.get("community_id"),
        }


class DBSessionExtension(SchemaExtension):
    def on_operation(self):
        yield
        self.execution_context.context["db_session"].remove()


def create_app():
    db_engine = create_engine(os.environ["DATABASE_URL"], echo=True)
    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        types=[EmailContact],
        extensions=[DBSessionExtension],
    )
    return GraphQLWithDB(db_engine, schema)
