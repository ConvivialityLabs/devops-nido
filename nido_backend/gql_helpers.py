#  Nido gql_helpers.py
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

import base64
from typing import Any, List, Tuple

import strawberry
from sqlalchemy.orm import ColumnProperty, Relationship, load_only, selectinload
from strawberry.types import Info


def encode_gql_id(tablename: str, id: int):
    return base64.b64encode(f"{tablename}:{id}".encode()).decode()


def decode_gql_id(id: str) -> Tuple[str, int]:
    data = base64.b64decode(id.encode("ascii")).decode("ascii").split(":")
    return (data[0], int(data[1]))


def prepare_orm_query(column: Any, info: Info, cols: List[Any], rels: List[Any]):
    for field in info.selected_fields[0].selections:
        # XXX selected_fields comes in camelCase but the SQL fields are in
        # snake_case. This is a mess, hopefully a future library includes
        # snake_case on the selected_fields object.
        pyname = (
            info.schema._schema.type_map[column.__name__[2:]]
            .fields[field.name]  # type: ignore
            .extensions["strawberry-definition"]
            .name
        )
        sql_field = getattr(column, pyname)
        if isinstance(sql_field.property, ColumnProperty):
            cols.append(sql_field)
        elif isinstance(sql_field.property, Relationship):
            rels.append(sql_field)
            # XXX Recurse to filter child's fields

    opts = []
    if len(cols) > 0:
        opts.append(load_only(*cols))
    if len(rels) > 0:
        opts.append(selectinload(*rels))
    return opts
