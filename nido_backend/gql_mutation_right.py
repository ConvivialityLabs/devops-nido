#  Nido gql_mutation_right.py
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

from functools import reduce
from typing import List, Optional

import strawberry
from sqlalchemy.exc import IntegrityError
from strawberry.types import Info

from .authorization import AuthorizationError, oso
from .db_models import DBRight
from .enums import PermissionsFlag
from .gql_errors import (
    DatabaseError,
    Error,
    NotFound,
    Unauthorized,
    parse_integrity_error,
)
from .gql_helpers import gql_id_to_table_id_unchecked
from .gql_permissions import IsAuthenticated
from .gql_query import Right


@strawberry.input
class DelegateRightInput:
    parent_id: strawberry.ID
    permissions: List[PermissionsFlag]
    name: str


@strawberry.type
class DelegateRightPayload:
    new_rights: Optional[List[Right]] = None
    errors: Optional[List[Error]] = None


@strawberry.type
class RightMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def delegate(
        self, info: Info, input: List[DelegateRightInput]
    ) -> DelegateRightPayload:
        new_rights: List[Right] = []
        errors: List[Error] = []

        au = info.context.active_user
        for i in input:
            parent_id = gql_id_to_table_id_unchecked(i.parent_id)
            parent_right = info.context.db_session.get(DBRight, parent_id)
            new_right = DBRight(name=i.name, community_id=info.context.community_id)
            new_right.parent_right = parent_right
            new_right.permissions = reduce(lambda a, b: a | b, i.permissions)
            info.context.db_session.add(new_right)
            info.context.db_session.flush()
            try:
                oso.authorize(au, "delegate", new_right)
            except AuthorizationError as err:
                errors.append(Unauthorized())
                continue
            try:
                info.context.db_session.commit()
                new_rights.append(Right(db=new_right))
            except IntegrityError as ie:
                gql_err = parse_integrity_error(ie)
                errors.append(gql_err)
                info.context.db_session.rollback()
            except:
                errors.append(DatabaseError())
                info.context.db_session.rollback()
        return DelegateRightPayload(new_rights=new_rights, errors=errors)
