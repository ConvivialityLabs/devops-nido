#  Nido gql_mutation_billing_charge.py
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
from typing import List, Optional

import strawberry
from strawberry.types import Info

from .authorization import AuthorizationError, oso
from .db_models import DBBillingCharge
from .gql_errors import DatabaseError, Error, NotFound, Unauthorized
from .gql_helpers import decode_gql_id
from .gql_permissions import IsAuthenticated
from .gql_query import BillingCharge


@strawberry.input
class NewBillingChargeInput:
    name: str
    amount: int
    due_date: datetime.date
    charged_to: strawberry.ID


@strawberry.type
class NewBillingChargePayload:
    new_charges: Optional[List[BillingCharge]] = None
    errors: Optional[List[Error]] = None


@strawberry.input
class EditBillingChargeInput:
    charge: strawberry.ID
    name: Optional[str] = strawberry.UNSET
    amount: Optional[int] = strawberry.UNSET
    due_date: Optional[datetime.date] = strawberry.UNSET


@strawberry.type
class EditBillingChargePayload:
    charges: Optional[List[BillingCharge]] = None
    errors: Optional[List[Error]] = None


@strawberry.input
class DeleteBillingChargeInput:
    charge: strawberry.ID


@strawberry.type
class DeleteBillingChargePayload:
    errors: Optional[List[Error]] = None


@strawberry.type
class BillingChargeMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def new(
        self, info: Info, input: List[NewBillingChargeInput]
    ) -> NewBillingChargePayload:
        new_charges: List[BillingCharge] = []
        errors: List[Error] = []

        au = info.context.active_user
        community_id = info.context.community_id
        for i in input:
            (charged_to_type, charged_to_id) = decode_gql_id(i.charged_to)
            new_charge = DBBillingCharge(
                name=i.name,
                community_id=community_id,
                amount=i.amount,
                due_date=i.due_date,
            )
            if charged_to_type == "user":
                new_charge.user_id = charged_to_id
            elif charged_to_type == "residence":
                new_charge.residence_id = charged_to_id
            try:
                oso.authorize(au, "create", new_charge)
            except AuthorizationError as err:
                errors.append(Unauthorized())
                continue
            info.context.db_session.add(new_charge)
            try:
                info.context.db_session.commit()
                new_charges.append(BillingCharge(db=new_charge))
            except:
                errors.append(DatabaseError())
                info.context.db_session.rollback()
        return NewBillingChargePayload(new_charges=new_charges, errors=errors)

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def edit(
        self, info: Info, input: List[EditBillingChargeInput]
    ) -> EditBillingChargePayload:
        charges: List[BillingCharge] = []
        errors: List[Error] = []

        user = info.context.active_user
        for i in input:
            charge = info.context.db_session.get(
                DBBillingCharge, decode_gql_id(i.charge)[1]
            )
            try:
                oso.authorize(user, "edit", charge)
            except AuthorizationError as err:
                errors.append(Unauthorized())
                continue
            if i.name is not strawberry.UNSET:
                charge.name = i.name
            if i.amount is not strawberry.UNSET:
                charge.amount = i.amount
            if i.due_date is not strawberry.UNSET:
                charge.due_date = i.due_date
            info.context.db_session.add(charge)
            try:
                info.context.db_session.commit()
                charges.append(BillingCharge(db=charge))
            except:
                errors.append(DatabaseError())
                info.context.db_session.rollback()
        return EditBillingChargePayload(charges=charges, errors=errors)

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def delete(
        self, info: Info, input: List[DeleteBillingChargeInput]
    ) -> DeleteBillingChargePayload:
        errors: List[Error] = []
        user = info.context.active_user
        for i in input:
            group = info.context.db_session.get(
                DBBillingCharge, decode_gql_id(i.charge)[1]
            )
            if not group:
                errors.append(NotFound())
                continue
            try:
                oso.authorize(user, "delete", group)
            except AuthorizationError as err:
                errors.append(Unauthorized())
                continue
            info.context.db_session.delete(group)
            try:
                info.context.db_session.commit()
            except:
                errors.append(DatabaseError())
                info.context.db_session.rollback()
        return DeleteBillingChargePayload(errors=errors)
