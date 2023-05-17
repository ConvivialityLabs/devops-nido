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

from typing import List, Optional

import strawberry
from sqlalchemy import delete, select, update
from sqlalchemy.orm import noload
from strawberry.types import Info

from .authorization import oso
from .db_models import (
    DBCommunity,
    DBContactMethod,
    DBEmailContact,
    DBGroup,
    DBGroupMembership,
    DBResidenceOccupancy,
    DBUser,
)
from .gql_helpers import decode_gql_id
from .gql_permissions import IsAuthenticated


@strawberry.type
class Authentication:
    @strawberry.mutation
    def login(self, info: Info, email: str) -> bool:
        stmt = (
            select(DBEmailContact.user_id, DBResidenceOccupancy.community_id)
            .join(DBUser, DBUser.id == DBEmailContact.user_id)
            .join(DBResidenceOccupancy, DBResidenceOccupancy.user_id == DBUser.id)
            .where(DBEmailContact.email == email)
        )
        try:
            # XXX It is possible for a user to belong to multiple communities; what to do?
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


@strawberry.input
class NewGroupInput:
    name: str
    custom_members: Optional[List[strawberry.ID]] = None
    managing_group: Optional[strawberry.ID] = None


@strawberry.input
class RenameGroupInput:
    group: strawberry.ID
    name: str


@strawberry.input
class DeleteGroupInput:
    group: strawberry.ID


@strawberry.type
class GroupMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def new_group(self, info: Info, input: List[NewGroupInput]) -> bool:
        user_id = info.context["request"].cookies["user_id"]
        community_id = info.context["request"].cookies["community_id"]
        for i in input:
            if i.managing_group:
                managing_id = decode_gql_id(i.managing_group)[1]
                ng = DBGroup(name=i.name, community_id=community_id)
                ng.managing_group_id = managing_id
                info.context["db_session"].add(ng)
            else:
                ng = DBGroup(name=i.name, community_id=community_id)
                info.context["db_session"].add(ng)
                info.context["db_session"].flush()
                ng.managing_group_id = ng.id
                info.context["db_session"].add(ng)
            if i.custom_members:
                for mem_id in i.custom_members:
                    entry = DBGroupMembership(
                        user_id=decode_gql_id(mem_id)[1],
                        community_id=community_id,
                        group_id=ng.id,
                    )
                    info.context["db_session"].add(entry)
            else:
                entry = DBGroupMembership(
                    user_id=user_id, community_id=community_id, group_id=ng.id
                )
                info.context["db_session"].add(entry)

        info.context["db_session"].commit()
        return True

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def rename_group(self, info: Info, input: List[RenameGroupInput]) -> bool:
        user_id = info.context["request"].cookies["user_id"]
        user = info.context["db_session"].get(DBUser, user_id)
        for i in input:
            group = info.context["db_session"].get(DBGroup, decode_gql_id(i.group)[1])
            oso.authorize(user, "update", group)
            stmt = update(DBGroup).where(DBGroup.id == group.id).values(name=i.name)
            info.context["db_session"].execute(stmt)
        info.context["db_session"].commit()
        return True

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def delete_group(self, info: Info, input: List[DeleteGroupInput]) -> bool:
        user_id = info.context["request"].cookies["user_id"]
        user = info.context["db_session"].get(DBUser, user_id)
        for i in input:
            group = info.context["db_session"].get(DBGroup, decode_gql_id(i.group)[1])
            oso.authorize(user, "delete", group)
            stmt = delete(DBGroup).where(DBGroup.id == group.id)
            info.context["db_session"].execute(stmt)
        info.context["db_session"].commit()
        return True


@strawberry.type
class Mutation:
    authentication: Authentication = strawberry.field(resolver=lambda: Authentication())
    contact_methods: ContactMethodMutations = strawberry.field(
        resolver=lambda: ContactMethodMutations()
    )
    groups: GroupMutations = strawberry.field(resolver=lambda: GroupMutations())
