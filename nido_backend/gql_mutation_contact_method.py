#  Nido gql_mutation_contact_method.py
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
from typing import List, Optional, Union

import strawberry
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from strawberry.types import Info

from .authorization import oso
from .db_models import DBContactMethod, DBEmailContact, DBUser
from .gql_errors import (
    DatabaseError,
    Error,
    NotFound,
    Unauthorized,
    parse_integrity_error,
)
from .gql_helpers import decode_gql_id
from .gql_permissions import IsAuthenticated
from .gql_query import EmailContact


@strawberry.input
class NewEmailCMInput:
    email: str


@strawberry.type
class NewEmailCMPayload:
    email_contacts: Optional[List[EmailContact]] = None
    errors: Optional[List[Error]] = None


@strawberry.input
class DeleteCMInput:
    id: strawberry.ID


@strawberry.type
class DeleteCMPayload:
    errors: Optional[List[Error]] = None


@strawberry.type
class ContactMethodMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def new_email(self, info: Info, input: List[NewEmailCMInput]) -> NewEmailCMPayload:
        email_contacts: List[EmailContact] = []
        errors: List[Error] = []

        au = info.context.active_user
        for i in input:
            new_contact = DBEmailContact(user=au, email=i.email)
            info.context.db_session.add(new_contact)
            try:
                info.context.db_session.commit()
                email_contacts.append(EmailContact(db=new_contact))
            except IntegrityError as ie:
                gql_err = parse_integrity_error(ie)
                errors.append(gql_err)
                info.context.db_session.rollback()
            except:
                errors.append(DatabaseError())
                info.context.db_session.rollback()
        return NewEmailCMPayload(email_contacts=email_contacts, errors=errors)

    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def delete(self, info: Info, input: List[DeleteCMInput]) -> DeleteCMPayload:
        errors: List[Error] = []

        au = info.context.active_user
        for i in input:
            cm_id = decode_gql_id(i.id)[1]
            cm = info.context.db_session.get(DBContactMethod, cm_id)
            if not cm:
                errors.append(NotFound())
                continue
            try:
                oso.authorize(au, "delete", cm)
            except:
                errors.append(NotFound())
                continue
            info.context.db_session.delete(cm)
            try:
                info.context.db_session.commit()
            except:
                errors.append(DatabaseError())
                info.context.db_session.rollback()
        return DeleteCMPayload(errors=errors)
