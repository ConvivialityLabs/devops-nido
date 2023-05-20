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


def prepare_orm_query(info: Info, db_model_class: Any, gql_field: Any):
    db_column_loads = []
    db_relationship_loads = []
    for field in gql_field.selections:
        # XXX SelectedField.name comes in camelCase but the db columns are in
        # snake_case. The line below converts them. It's a mess, hopefully a
        # future library version includes a attribute with snake_case on the
        # SelectedField object.
        pyname = (
            info.schema._schema.type_map[db_model_class.__name__[2:]]
            .fields[field.name]  # type: ignore
            .extensions["strawberry-definition"]
            .name
        )
        db_model_attr = getattr(db_model_class, pyname, None)
        if db_model_attr is None:
            continue
        elif isinstance(db_model_attr.property, ColumnProperty):
            db_column_loads.append(db_model_attr)
        elif isinstance(db_model_attr.property, Relationship):
            sub_opts = prepare_orm_query(info, db_model_attr.mapper.class_, field)
            db_relationship_loads.append(selectinload(db_model_attr).options(*sub_opts))

    opts = []
    if len(db_column_loads) > 0:
        opts.append(load_only(*db_column_loads))
    else:
        opts.append(load_only(db_model_class.id))
    if len(db_relationship_loads) > 0:
        opts.extend(db_relationship_loads)
    return opts
