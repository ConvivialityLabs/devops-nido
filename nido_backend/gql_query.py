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

import datetime
from dataclasses import dataclass, field
from typing import Generic, List, Optional, Type, TypeVar

import strawberry
from sqlalchemy import func as sql_func
from sqlalchemy import select
from strawberry.types import Info
from strawberry.types.nodes import SelectedField

from .authorization import oso
from .db_models import (
    Base,
    DBAssociate,
    DBBillingCharge,
    DBBillingPayment,
    DBCommunity,
    DBContactMethod,
    DBEmailContact,
    DBGroup,
    DBGroupMembership,
    DBNode,
    DBResidence,
    DBRight,
    DBUser,
)
from .enums import ApplicationStatus, PermissionsFlag
from .gql_helpers import (
    encode_gql_id,
    gql_id_to_table_id_unchecked,
    recursive_eager_load,
)
from .gql_permissions import IsAuthenticated

DB = TypeVar("DB", bound=DBNode)


@strawberry.interface
class Node(Generic[DB]):
    db: strawberry.Private[DB]
    dbtype: strawberry.Private[Type[Base]] = field(init=False, repr=False)

    @strawberry.field
    def id(self) -> strawberry.ID:
        return encode_gql_id(self.dbtype.__tablename__, self.db.id)


N = TypeVar("N", bound=Node)


@strawberry.type
class Edge(Generic[N]):
    node: N

    @strawberry.field
    def cursor(self) -> str:
        return self.node.id


@strawberry.type
class Connection(Generic[N]):
    edges: List[Edge[N]]


@strawberry.input
class ResidenceFilter:
    not_: Optional["ResidenceFilter"] = strawberry.UNSET
    or_: Optional[List["ResidenceFilter"]] = strawberry.UNSET
    unit_no: Optional[str] = strawberry.UNSET
    street: Optional[str] = strawberry.UNSET
    locality: Optional[str] = strawberry.UNSET
    postcode: Optional[str] = strawberry.UNSET
    region: Optional[str] = strawberry.UNSET


@strawberry.input
class BillingChargeFilter:
    not_: Optional["BillingChargeFilter"] = strawberry.UNSET
    or_: Optional[List["BillingChargeFilter"]] = strawberry.UNSET
    name: Optional[str] = strawberry.UNSET
    amount: Optional[str] = strawberry.UNSET
    remainingBalance: Optional[str] = strawberry.UNSET
    chargeDate: Optional[str] = strawberry.UNSET
    dueDate: Optional[str] = strawberry.UNSET


@strawberry.input
class GroupFilter:
    not_: Optional["GroupFilter"] = strawberry.UNSET
    or_: Optional[List["GroupFilter"]] = strawberry.UNSET
    name: Optional[str] = strawberry.UNSET


@strawberry.type
class Community(Node[DBCommunity]):
    dbtype = DBCommunity

    @strawberry.field
    def name(self) -> str:
        return self.db.name

    @strawberry.field
    def residences(
        self,
        first: Optional[int] = strawberry.UNSET,
        filter: Optional[ResidenceFilter] = strawberry.UNSET,
    ) -> Optional[Connection["Residence"]]:
        return Connection(
            edges=[Edge(node=Residence(db=r)) for r in self.db.residences]
        )

    @strawberry.field
    def billing_charges(
        self,
        info: Info,
        filter: Optional[BillingChargeFilter] = strawberry.UNSET,
    ) -> Optional[Connection["BillingCharge"]]:
        au = info.context.active_user
        return Connection(
            edges=[
                Edge(node=BillingCharge(db=bc))
                for bc in self.db.billing_charges
                if oso.is_allowed(au, "query", bc)
            ]
        )

    @strawberry.field
    def billing_payments(self) -> Optional[Connection["BillingPayment"]]:
        return Connection(
            edges=[Edge(node=BillingPayment(db=bp)) for bp in self.db.billing_payments]
        )

    @strawberry.field
    def groups(
        self,
        info: Info,
        filter: Optional[GroupFilter] = strawberry.UNSET,
    ) -> Optional[Connection["Group"]]:
        au = info.context.active_user
        return Connection(
            edges=[
                Edge(node=Group(db=g))
                for g in self.db.groups
                if oso.is_allowed(au, "query", g)
            ]
        )

    @strawberry.field
    def rights(self) -> Optional[Connection["Right"]]:
        return Connection(edges=[Edge(node=Right(db=r)) for r in self.db.rights])

    @strawberry.field
    def associates(self) -> Optional[Connection["Associate"]]:
        return Connection(
            edges=[Edge(node=Associate(db=a)) for a in self.db.associates]
        )


@strawberry.type
class Associate(Node[DBAssociate]):
    dbtype = DBAssociate

    @strawberry.field
    def personal_name(self) -> str:
        return self.db.personal_name

    @strawberry.field
    def family_name(self) -> str:
        return self.db.family_name

    @strawberry.field
    def full_name(self) -> str:
        return self.db.full_name

    @strawberry.field
    def collation_name(self) -> str:
        return self.db.collation_name

    @strawberry.field
    def contact_methods(self, info: Info) -> List["ContactMethod"]:
        au = info.context.active_user
        if au:
            return [
                EmailContact(db=cm)
                for cm in self.db.contact_methods
                if isinstance(cm, DBEmailContact) and oso.is_allowed(au, "query", cm)
            ]
        else:
            return []

    @strawberry.field
    def residences(self) -> Optional[Connection["Residence"]]:
        return Connection(
            edges=[Edge(node=Residence(db=r)) for r in self.db.residences]
        )

    @strawberry.field
    def groups(self, info: Info) -> Optional[List["Group"]]:
        return [Group(db=g) for g in self.db.groups]


@strawberry.type
class Residence(Node[DBResidence]):
    dbtype = DBResidence

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
    def occupants(self) -> Optional[Connection["Associate"]]:
        return Connection(edges=[Edge(node=Associate(db=a)) for a in self.db.occupants])

    @strawberry.field
    def billing_charges(
        self,
        info: Info,
        filter: Optional[BillingChargeFilter] = strawberry.UNSET,
    ) -> Optional[Connection["BillingCharge"]]:
        au = info.context.active_user
        return Connection(
            edges=[
                Edge(node=BillingCharge(db=bc))
                for bc in self.db.billing_charges
                if oso.is_allowed(au, "query", bc)
            ]
        )

    @strawberry.field
    def issues(self, info: Info) -> Optional[List["Issue"]]:
        return info.context.dev_issue_list


# TODO This is just a development mockup to try out different Issue designs.
# A production implementation should come from db or an external service.
@strawberry.type
class Issue:
    is_open: bool
    description: str
    status_msg: Optional[str] = None


@strawberry.type
class User(Node[DBUser]):
    dbtype = DBUser
    reference_community_id: strawberry.Private[Optional[int]] = None

    @strawberry.field
    def personal_name(self) -> str:
        return self.db.personal_name

    @strawberry.field
    def family_name(self) -> str:
        return self.db.family_name

    @strawberry.field
    def full_name(self) -> str:
        return self.db.full_name

    @strawberry.field
    def collation_name(self) -> str:
        return self.db.collation_name

    @strawberry.field
    def contact_methods(self, info: Info) -> List["ContactMethod"]:
        au = info.context.active_user
        if au:
            return [
                EmailContact(db=cm)
                for cm in self.db.contact_methods
                if isinstance(cm, DBEmailContact) and oso.is_allowed(au, "query", cm)
            ]
        else:
            return []

    @strawberry.field
    def residences(self, info: Info) -> Optional[Connection["Residence"]]:
        stmt = (
            select(DBResidence)
            .select_from(DBAssociate)
            .join(DBAssociate.residences)
            .where(DBAssociate.user_id == self.db.id)
        )
        if self.reference_community_id:
            stmt = stmt.where(DBAssociate.community_id == self.reference_community_id)
        result = info.context.db_session.execute(stmt).scalars()
        return Connection(edges=[Edge(node=Residence(db=r)) for r in result])

    @strawberry.field
    def groups(
        self,
        info: Info,
    ) -> Optional[List["Group"]]:
        stmt = (
            select(DBGroup)
            .select_from(DBAssociate)
            .join(DBAssociate.groups)
            .where(DBAssociate.user_id == self.db.id)
        )
        if self.reference_community_id:
            stmt = stmt.where(DBAssociate.community_id == self.reference_community_id)
        result = info.context.db_session.execute(stmt).scalars()
        return [Group(db=g) for g in result]

    @strawberry.field
    def is_admin(self, info: Info) -> bool:
        stmt = (
            select(DBGroupMembership.community_id, sql_func.count(DBRight.id))
            .select_from(DBGroupMembership)
            .join(DBGroup, DBGroupMembership.group_id == DBGroup.id)
            .join(DBRight, DBGroup.right_id == DBRight.id)
            .join(DBAssociate, DBGroupMembership.member_id == DBAssociate.id)
            .where(DBAssociate.user_id == self.db.id)
            .group_by(DBGroupMembership.community_id)
        )
        result = info.context.db_session.execute(stmt)
        # TODO: The conditional below gives the right answer the majority of
        # the time but is wrong in principle; it ought to compare against a
        # particular community_id
        for res in result:
            if res[1] > 0:
                return True
        return False


@strawberry.type
class Group(Node[DBGroup]):
    dbtype = DBGroup

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
    def custom_members(self) -> Optional[List[Associate]]:
        return [Associate(db=a) for a in self.db.custom_members]

    @strawberry.field
    def is_allowed(self, info: Info, action: str) -> bool:
        au = info.context.active_user
        return oso.is_allowed(au, action, self.db)


@strawberry.type
class Right(Node[DBRight]):
    dbtype = DBRight

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
        if self.db.parent_right != self.db:
            return Right(db=self.db.parent_right)
        else:
            return None

    @strawberry.field
    def child_rights(self) -> Optional[List["Right"]]:
        return [Right(db=r) for r in self.db.child_rights if r != self.db]

    @strawberry.field
    def groups(self, info: Info) -> Optional[List[Group]]:
        au = info.context.active_user
        return [Group(db=g) for g in self.db.groups if oso.is_allowed(au, "query", g)]

    @strawberry.field
    def is_allowed(self, info: Info, action: str) -> bool:
        au = info.context.active_user
        return oso.is_allowed(au, action, self.db)


@strawberry.interface
class ContactMethod(Node[DBContactMethod]):
    dbtype = DBContactMethod

    @strawberry.field
    def user(self) -> Optional[User]:
        return User(db=self.db.user) if self.db.user else None


@strawberry.type
class EmailContact(ContactMethod):
    db: strawberry.Private[DBEmailContact]

    @strawberry.field
    def email(self) -> str:
        return self.db.email


@strawberry.type
class BillingPayment(Node[DBBillingPayment]):
    dbtype = DBBillingPayment

    @strawberry.field
    def amount(self) -> int:
        return self.db.amount

    @strawberry.field
    def remaining_balance(self) -> int:
        return self.db.remaining_balance

    @strawberry.field
    def payment_date(self) -> datetime.datetime:
        return self.db.payment_date

    @strawberry.field
    def charges(
        self,
        info: Info,
        filter: Optional[BillingChargeFilter] = strawberry.UNSET,
    ) -> Optional[Connection["BillingCharge"]]:
        au = info.context.active_user
        return Connection(
            edges=[
                Edge(node=BillingCharge(db=bc))
                for bc in self.db.charges
                if oso.is_allowed(au, "query", bc)
            ]
        )


@strawberry.type
class BillingCharge(Node[DBBillingCharge]):
    dbtype = DBBillingCharge

    @strawberry.field
    def name(self) -> str:
        return self.db.name

    @strawberry.field
    def amount(self) -> int:
        return self.db.amount

    @strawberry.field
    def remaining_balance(self) -> int:
        return self.db.remaining_balance

    @strawberry.field
    def charge_date(self) -> datetime.datetime:
        return self.db.charge_date

    @strawberry.field
    def due_date(self) -> datetime.date:
        return self.db.due_date

    @strawberry.field
    def payments(self) -> Optional[List[BillingPayment]]:
        return [BillingPayment(db=p) for p in self.db.payments]


@strawberry.type
class Query:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def active_user(
        self, info: Info, reference_community: Optional[strawberry.ID] = None
    ) -> Optional[User]:
        user_id = info.context.user_id
        au_field = None
        for field in info.selected_fields:
            if isinstance(field, SelectedField) and field.name == "activeUser":
                au_field = field
                break
        assert au_field is not None
        stmt = select(DBUser).where(DBUser.id == user_id)
        rows = recursive_eager_load(info, stmt, DBUser, au_field)
        c_id = (
            gql_id_to_table_id_unchecked(reference_community)
            if reference_community
            else None
        )
        if len(rows) == 1:
            return User(db=rows[0][0], reference_community_id=c_id)
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
        assert ac_field is not None
        stmt = select(DBCommunity).where(DBCommunity.id == community_id)
        rows = recursive_eager_load(info, stmt, DBCommunity, ac_field)
        if len(rows) == 1:
            return Community(db=rows[0][0])
        else:
            return None
