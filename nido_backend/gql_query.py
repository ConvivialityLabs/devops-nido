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
from strawberry.types import Info
from strawberry.types.nodes import SelectedField

from .authorization import oso
from .db_models import (
    DBCommunity,
    DBContactMethod,
    DBEmailContact,
    DBGroup,
    DBResidence,
    DBRight,
    DBUser,
)
from .enums import PermissionsFlag
from .gql_helpers import encode_gql_id, prepare_orm_query
from .gql_permissions import IsAuthenticated


@strawberry.type
class Community:
    db: strawberry.Private[DBCommunity]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(DBCommunity.__tablename__, self.db.id)

    @strawberry.field
    def name(self) -> str:
        return self.db.name

    @strawberry.field
    def residences(self) -> Optional[List["Residence"]]:
        return [Residence(db=r) for r in self.db.residences]

    @strawberry.field
    def groups(self) -> Optional[List["Group"]]:
        return [Group(db=g) for g in self.db.groups]

    @strawberry.field
    def rights(self) -> Optional[List["Right"]]:
        return [Right(db=r) for r in self.db.rights]

    @strawberry.field
    def users(self) -> Optional[List["User"]]:
        return [User(db=u) for u in self.db.users]


@strawberry.type
class Residence:
    db: strawberry.Private[DBResidence]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(DBResidence.__tablename__, self.db.id)

    @strawberry.field
    def unit_no(self) -> Optional[str]:
        return self.db.unit_no

    @strawberry.field
    def street(self) -> str:
        return self.db.street

    @strawberry.field
    def locality(self) -> str:
        return self.db.locality

    @strawberry.field
    def postcode(self) -> str:
        return self.db.postcode

    @strawberry.field
    def region(self) -> str:
        return self.db.region

    @strawberry.field
    def community(self) -> Optional[Community]:
        return Community(db=self.db.community)

    @strawberry.field
    def occupants(self) -> Optional[List["User"]]:
        return [User(db=u) for u in self.db.occupants]


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
    def contact_methods(self, info: Info) -> List["ContactMethod"]:
        au = info.context.active_user
        if au:
            return [
                EmailContact(db=cm)
                for cm in self.db.contact_methods
                if isinstance(cm, DBEmailContact) and oso.is_allowed(au, "read", cm)
            ]
        else:
            return []


@strawberry.type
class Group:
    db: strawberry.Private[DBGroup]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(DBGroup.__tablename__, self.db.id)

    @strawberry.field
    def name(self) -> str:
        return self.db.name

    @strawberry.field
    def community(self) -> Optional[Community]:
        return Community(db=self.db.community)

    @strawberry.field
    def managed_by(self) -> Optional["Group"]:
        return Group(db=self.db.managed_by)

    @strawberry.field
    def manages(self) -> Optional[List["Group"]]:
        return [Group(db=g) for g in self.db.manages]

    @strawberry.field
    def right(self) -> Optional["Right"]:
        return Right(db=self.db.right) if self.db.right else None

    @strawberry.field
    def custom_members(self) -> Optional[List[User]]:
        return [User(db=u) for u in self.db.custom_members]


@strawberry.type
class Right:
    db: strawberry.Private[DBRight]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(DBRight.__tablename__, self.db.id)

    @strawberry.field
    def name(self) -> str:
        return self.db.name

    @strawberry.field
    def permissions(self) -> List[PermissionsFlag]:
        return [m for m in self.db.permissions]

    @strawberry.field
    def community(self) -> Optional[Community]:
        return Community(db=self.db.community)

    @strawberry.field
    def parent_right(self) -> Optional["Right"]:
        return Right(db=self.db.parent_right)

    @strawberry.field
    def child_rights(self) -> Optional[List["Right"]]:
        return [Right(db=r) for r in self.db.child_rights]

    @strawberry.field
    def groups(self) -> Optional[List[Group]]:
        return [Group(db=g) for g in self.db.groups]


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
        user_id = info.context.user_id
        au_field = None
        for field in info.selected_fields:
            if isinstance(field, SelectedField) and field.name == "activeUser":
                au_field = field
                break
        opts = prepare_orm_query(info, DBUser, au_field)
        u = info.context.db_session.get(DBUser, user_id, options=opts)
        if u:
            return User(db=u)
        else:
            return None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def active_community(self, info: Info) -> Optional[Community]:
        community_id = info.context.community_id
        ac_field = None
        for field in info.selected_fields:
            if isinstance(field, SelectedField) and field.name == "activeCommunity":
                ac_field = field
                break
        opts = prepare_orm_query(info, DBCommunity, ac_field)
        c = info.context.db_session.get(DBCommunity, community_id, options=opts)
        if c:
            return Community(db=c)
        else:
            return None
