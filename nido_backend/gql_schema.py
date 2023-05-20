#  Nido gql_schema.py
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

from dataclasses import dataclass
from typing import Optional, Type

from sqlalchemy.orm import scoped_session
from strawberry import Schema
from strawberry.extensions import SchemaExtension

from .db_models import DBCommunity, DBUser
from .gql_errors import AlreadyTaken, DatabaseError, NotFound, Unauthorized
from .gql_mutation import Mutation
from .gql_query import EmailContact, Query


@dataclass
class SchemaContext:
    db_session: scoped_session
    user_id: Optional[int] = None
    community_id: Optional[int] = None

    @property
    def active_user(self):
        if self.user_id:
            return self.db_session().get(DBUser, self.user_id)
        else:
            return None

    @property
    def active_community(self):
        if self.community_id:
            return self.db_session().get(DBCommunity, self.community_id)
        else:
            return None


class DBSessionExtension(SchemaExtension):
    def on_operation(self):
        yield
        self.execution_context.context.db_session.remove()


def create_schema(SchemaClass: Type[Schema] = Schema, **kwargs) -> Schema:
    return SchemaClass(
        query=Query,
        mutation=Mutation,
        types=[EmailContact, AlreadyTaken, DatabaseError, NotFound, Unauthorized],
        extensions=[DBSessionExtension],
        **kwargs
    )
