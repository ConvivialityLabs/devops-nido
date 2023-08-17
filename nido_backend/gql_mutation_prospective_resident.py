#  Nido gql_mutation_prospective_resident.py
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
from sqlalchemy import delete
from strawberry.types import Info

from .authorization import AuthorizationError, oso
from .db_models import DBProspectiveResident
from .gql_errors import DatabaseError, Error, NotFound, Unauthorized
from .gql_helpers import gql_id_to_table_id_unchecked
from .gql_permissions import IsAuthenticated
from .gql_query import ProspectiveResident


@strawberry.input
class NewPRInput:
    personal_name: str
    family_name: str
    residence_id: strawberry.ID
    sponsor_id: Optional[strawberry.ID] = None


@strawberry.type
class NewPRPayload:
    prospective_residents: Optional[List[ProspectiveResident]] = None
    errors: Optional[List[Error]] = None


@strawberry.type
class ProspectiveResidentMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def new(self, info: Info, input: List[NewPRInput]) -> NewPRPayload:
        new_prs: List[ProspectiveResident] = []
        errors: List[Error] = []

        community_id = info.context.community_id
        for i in input:
            residence_id = gql_id_to_table_id_unchecked(i.residence_id)
            new_pr = DBProspectiveResident(
                community_id=community_id,
                residence_id=residence_id,
                personal_name=i.personal_name,
                family_name=i.family_name,
            )
            if i.sponsor_id:
                new_pr.sponsor_id = gql_id_to_table_id_unchecked(i.sponsor_id)
            info.context.db_session.add(new_pr)
            try:
                info.context.db_session.commit()
                new_prs.append(ProspectiveResident(db=new_pr))
            except:
                errors.append(DatabaseError())
                info.context.db_session.rollback()
        return NewPRPayload(prospective_residents=new_prs, errors=errors)
