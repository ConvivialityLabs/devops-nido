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

import strawberry

from .gql_mutation_contact_method import ContactMethodMutations
from .gql_mutation_group import GroupMutations


@strawberry.type
class Mutation:
    contact_methods: ContactMethodMutations = strawberry.field(
        resolver=lambda: ContactMethodMutations()
    )
    groups: GroupMutations = strawberry.field(resolver=lambda: GroupMutations())
