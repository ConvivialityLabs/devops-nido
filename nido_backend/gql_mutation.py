#  Nido gql_mutation.py
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

import strawberry
from sqlalchemy import delete, select
from strawberry.types import Info

from .db_models import DBCommunity, DBContactMethod, DBEmailContact, DBUser
from .gql_helpers import decode_gql_id
from .gql_permissions import IsAuthenticated


@strawberry.type
class Authentication:
    @strawberry.mutation
    def login(self, info: Info, email: str) -> bool:
        stmt = (
            select(DBEmailContact.user_id, DBUser.community_id)
            .join(DBUser)
            .where(DBEmailContact.email == email)
        )
        try:
            (user_id, community_id) = info.context["db_session"].execute(stmt).one()
            info.context["response"].set_cookie(key="user_id", value=user_id)
            info.context["response"].set_cookie(key="community_id", value=community_id)
            return True
        except:
            return False

    @strawberry.mutation
    def logout(self, info: Info) -> bool:
        cookies = info.context["request"].cookies
        if "user_id" in cookies or "community_id" in cookies:
            info.context["response"].delete_cookie("user_id")
            info.context["response"].delete_cookie("community_id")
            return True
        return False


@strawberry.type
class ContactMethodMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def new_email_contact(self, info: Info, email: str) -> bool:
        user_id = info.context["request"].cookies.get("user_id")
        new_contact = DBEmailContact(user_id=user_id, email=email)
        info.context["db_session"].add(new_contact)
        info.context["db_session"].commit()
        return True

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def delete_contact(self, info: Info, id: strawberry.ID) -> bool:
        user_id = info.context["request"].cookies.get("user_id")
        cm_id = decode_gql_id(id)[1]
        stmt = delete(DBContactMethod).where(
            DBContactMethod.id == cm_id, DBContactMethod.user_id == user_id
        )
        try:
            info.context["db_session"].execute(stmt)
            info.context["db_session"].commit()
            return True
        except:
            return False


@strawberry.type
class Mutation:
    authentication: Authentication = strawberry.field(resolver=lambda: Authentication())
    contact_methods: ContactMethodMutations = strawberry.field(
        resolver=lambda: ContactMethodMutations()
    )
