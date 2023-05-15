#  Nido gql_query.py
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

from typing import List, Optional

import strawberry
from sqlalchemy import select
from strawberry.types import Info

from .db_models import DBCommunity, DBContactMethod, DBEmailContact, DBUser
from .gql_helpers import encode_gql_id, prepare_orm_query
from .gql_permissions import IsAuthenticated


def get_users(
    root: Optional["Community"],
    info: Info,
) -> Optional[List["User"]]:
    if root:
        return [User(db=u) for u in root.db.users]
    else:
        community_id = info.context["request"].cookies.get("community_id")
        stmt = select(DBUser).where(DBUser.community_id == community_id)
        opts = prepare_orm_query(DBUser, info, [], [])
        stmt = stmt.options(*opts)
        users = info.context["db_session"].scalars(stmt).all()
        return [User(db=u) for u in users]


@strawberry.type
class Community:
    db: strawberry.Private[DBCommunity]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(DBCommunity.__tablename__, self.db.id)

    @strawberry.field
    def name(self) -> str:
        return self.db.name

    users: Optional[List["User"]] = strawberry.field(resolver=get_users)


@strawberry.type
class User:
    db: strawberry.Private[DBUser]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(DBUser.__tablename__, self.db.id)

    @strawberry.field
    def personal_name(self) -> str:
        return self.db.personal_name

    @strawberry.field
    def family_name(self) -> str:
        return self.db.family_name

    @strawberry.field
    def full_name(self) -> str:
        return f"{self.db.personal_name} {self.db.family_name}"

    @strawberry.field
    def collation_name(self) -> str:
        return f"{self.db.family_name}, {self.db.personal_name}"

    @strawberry.field
    def contact_methods(self) -> List["ContactMethod"]:
        return [
            EmailContact(db=cm)
            for cm in self.db.contact_methods
            if isinstance(cm, DBEmailContact)
        ]


@strawberry.interface
class ContactMethod:
    db: strawberry.Private[DBContactMethod]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(DBContactMethod.__tablename__, self.db.id)

    @strawberry.field
    def user(self) -> User:
        return User(db=self.db.user)


@strawberry.type
class EmailContact(ContactMethod):
    db: strawberry.Private[DBEmailContact]

    @strawberry.field
    def email(self) -> str:
        return self.db.email


@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def active_user(self, info: Info) -> Optional[User]:
        user_id = info.context["request"].cookies.get("user_id")
        u = info.context["db_session"].get(DBUser, user_id)
        return User(db=u)

    @strawberry.field(permission_classes=[IsAuthenticated])
    def community(self, info: Info) -> Optional[Community]:
        community_id = info.context["request"].cookies.get("community_id")
        c = info.context["db_session"].get(DBCommunity, community_id)
        return Community(db=c)

    users: Optional[List["User"]] = strawberry.field(resolver=get_users)
