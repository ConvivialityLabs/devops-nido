#  Nido gql_mutation_authentication.py
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

from enum import Enum, auto
from typing import Union

import strawberry
from sqlalchemy import select
from strawberry.types import Info

from .db_models import DBEmailContact, DBResidenceOccupancy, DBUser
from .gql_query import User


@strawberry.input
class LoginInput:
    email: str


@strawberry.enum
class LoginErrorType(Enum):
    DATABASE_ERROR = auto()
    NOT_FOUND = auto()
    MULTIPLE_COMMUNITIES = auto()


@strawberry.type
class LoginError:
    type: LoginErrorType


@strawberry.type
class Authentication:
    @strawberry.mutation
    def login(self, info: Info, input: LoginInput) -> Union[User, LoginError]:
        stmt = (
            select(DBUser, DBResidenceOccupancy.community_id)
            .select_from(DBEmailContact)
            .join(DBUser, DBUser.id == DBEmailContact.user_id)
            .join(DBResidenceOccupancy, DBResidenceOccupancy.user_id == DBUser.id)
            .where(DBEmailContact.email == input.email)
        )
        try:
            rows = info.context["db_session"].execute(stmt).all()
        except:
            return LoginError(type=LoginErrorType.DATABASE_ERROR)
        count = len(rows)
        if count == 0:
            return LoginError(type=LoginErrorType.NOT_FOUND)
        elif count == 1:
            (user, community_id) = rows[0]
            info.context["response"].set_cookie(key="user_id", value=user.id)
            info.context["response"].set_cookie(key="community_id", value=community_id)
            return User(db=user)
        else:
            # XXX It is possible for a user to belong to multiple communities,
            # what should be done?
            return LoginError(type=LoginErrorType.MULTIPLE_COMMUNITIES)

    @strawberry.mutation
    def logout(self, info: Info) -> bool:
        cookies = info.context["request"].cookies
        if "user_id" in cookies or "community_id" in cookies:
            info.context["response"].delete_cookie("user_id")
            info.context["response"].delete_cookie("community_id")
            return True
        return False
