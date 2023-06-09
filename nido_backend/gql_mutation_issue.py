#  Nido gql_mutation_issue.py
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

from .gql_errors import Error
from .gql_permissions import IsAuthenticated
from .gql_query import Issue


@strawberry.input
class NewIssueInput:
    description: str


@strawberry.type
class NewIssuePayload:
    issues: Optional[List[Issue]] = None
    errors: Optional[List[Error]] = None


@strawberry.type
class IssueMutations:
    @strawberry.mutation(permission_classes=[IsAuthenticated])
    def new(self, info: Info, input: List[NewIssueInput]) -> NewIssuePayload:
        new_issues: List[Issue] = []
        errors: List[Error] = []

        au = info.context.active_user
        community_id = info.context.community_id
        for i in input:
            new_issue = Issue(is_open=True, description=i.description)
            info.context.dev_issue_list.append(new_issue)
        return NewIssuePayload(issues=new_issues, errors=errors)
