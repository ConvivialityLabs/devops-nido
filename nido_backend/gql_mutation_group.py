#  Nido gql_mutation_group.py
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

from typing import List, Optional, Union

import strawberry
from sqlalchemy import delete, select, update
from sqlalchemy.orm import noload
from strawberry.types import Info

from .authorization import oso
from .db_models import DBGroup, DBGroupMembership, DBUser
from .gql_errors import Error, Unauthorized
from .gql_helpers import decode_gql_id
from .gql_permissions import IsAuthenticated
from .gql_query import Group


@strawberry.input
class NewGroupInput:
    name: str
    custom_members: Optional[List[strawberry.ID]] = None
    managing_group: Optional[strawberry.ID] = None


@strawberry.type
class NewGroupPayload:
    groups: Optional[List[Group]] = None
    errors: Optional[List[Error]] = None


@strawberry.input
class RenameGroupInput:
    group: strawberry.ID
    name: str


@strawberry.type
class RenameGroupPayload:
    groups: Optional[List[Group]] = None
    errors: Optional[List[Error]] = None


@strawberry.input
class DeleteGroupInput:
    group: strawberry.ID


@strawberry.type
class DeleteGroupPayload:
    errors: Optional[List[Error]] = None


@strawberry.type
class GroupMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def new(self, info: Info, input: List[NewGroupInput]) -> NewGroupPayload:
        au = info.context.active_user
        community_id = info.context.community_id
        for i in input:
            if i.managing_group:
                managing_id = decode_gql_id(i.managing_group)[1]
                ng = DBGroup(name=i.name, community_id=community_id)
                ng.managing_group_id = managing_id
                info.context.db_session.add(ng)
            else:
                ng = DBGroup(name=i.name, community_id=community_id)
                info.context.db_session.add(ng)
                try:
                    info.context.db_session.flush()
                except:
                    pass
                ng.managing_group_id = ng.id
                info.context.db_session.add(ng)
            oso.authorize(au, "create", ng)
            if i.custom_members:
                for mem_id in i.custom_members:
                    entry = DBGroupMembership(
                        user_id=decode_gql_id(mem_id)[1],
                        community_id=community_id,
                        group_id=ng.id,
                    )
                    info.context.db_session.add(entry)
            else:
                entry = DBGroupMembership(
                    user_id=au.id, community_id=community_id, group_id=ng.id
                )
                info.context.db_session.add(entry)
                try:
                    info.context.db_session.commit()
                except:
                    pass
        return NewGroupPayload()

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def rename(self, info: Info, input: List[RenameGroupInput]) -> RenameGroupPayload:
        errors: List[Error] = []
        user_id = info.context.user_id
        user = info.context.db_session.get(DBUser, user_id)
        for i in input:
            group = info.context.db_session.get(DBGroup, decode_gql_id(i.group)[1])
            try:
                oso.authorize(user, "update", group)
            except:
                errors.append(Unauthorized())
            stmt = update(DBGroup).where(DBGroup.id == group.id).values(name=i.name)
            info.context.db_session.execute(stmt)
        info.context.db_session.commit()
        return RenameGroupPayload(errors=errors)

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def delete(self, info: Info, input: List[DeleteGroupInput]) -> DeleteGroupPayload:
        errors: List[Error] = []
        user_id = info.context.user_id
        user = info.context.db_session.get(DBUser, user_id)
        for i in input:
            group = info.context.db_session.get(DBGroup, decode_gql_id(i.group)[1])
            try:
                oso.authorize(user, "delete", group)
            except:
                errors.append(Unauthorized())
            stmt = delete(DBGroup).where(DBGroup.id == group.id)
            info.context.db_session.execute(stmt)

        info.context.db_session.commit()
        return DeleteGroupPayload(errors=errors)
