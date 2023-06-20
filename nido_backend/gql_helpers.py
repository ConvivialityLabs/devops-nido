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
from itertools import groupby
from typing import Any, List, Tuple, Type

import strawberry
from sqlalchemy import Row, Select
from sqlalchemy import func as sql_func
from sqlalchemy import inspect, select
from sqlalchemy.orm import (
    ColumnProperty,
    InstrumentedAttribute,
    MapperProperty,
    Relationship,
    aliased,
    attributes,
    load_only,
)
from strawberry.types import Info
from strawberry.types.nodes import InlineFragment, SelectedField

from .db_models import DBNode


def encode_gql_id(tablename: str, id: int):
    return base64.b64encode(f"{tablename}:{id}".encode()).decode()


def decode_gql_id(id: str) -> Tuple[str, int]:
    data = base64.b64decode(id.encode("ascii")).decode("ascii").split(":")
    return (data[0], int(data[1]))


def convert_gqlname_to_pyname(
    info: Info, gql_class_name: str, gql_field_name: str
) -> str:
    # XXX SelectedField.name comes in camelCase but the db columns are in
    # snake_case. The line below converts them. It's a mess, hopefully a
    # future library version includes a attribute with snake_case on the
    # SelectedField object.
    return (
        info.schema._schema.type_map[gql_class_name]
        .fields[gql_field_name]  # type: ignore
        .extensions["strawberry-definition"]
        .name
    )


def recursive_eager_load(
    info: Info, stmt: Select, DBModelClass: Type[DBNode], gql_field: SelectedField
):
    db_column_loads = []
    db_relationship_loads = []
    inspection = inspect(DBModelClass)
    assert inspection is not None
    gql_class_name = inspection.class_.__name__[2:]

    for subfield in gql_field.selections:
        if not isinstance(subfield, SelectedField):
            # TODO: Handle the case of Fragments and InlineFragments
            continue
        pyname = convert_gqlname_to_pyname(info, gql_class_name, subfield.name)
        db_model_attr = getattr(DBModelClass, pyname, None)
        if db_model_attr is None or not hasattr(db_model_attr, "property"):
            continue
        elif isinstance(db_model_attr.property, ColumnProperty):
            db_column_loads.append(db_model_attr)
        elif isinstance(db_model_attr.property, Relationship):
            db_relationship_loads.append((db_model_attr, subfield))

    if len(db_column_loads) > 0:
        lo = load_only(*db_column_loads)
    else:
        lo = load_only(DBModelClass.id)
    rows = info.context.db_session.execute(stmt.options(lo)).all()

    for relationship_attr, gql_subfield in db_relationship_loads:
        load_relationship(
            info, inspection.class_, relationship_attr, gql_subfield, rows
        )

    return rows


def get_best_parent_id_col(relationship: MapperProperty, ParentDBClass: Type[DBNode]):
    for column in relationship.remote_side:
        if ParentDBClass.id in [fk.column for fk in column.foreign_keys]:
            return column
    return ParentDBClass.id


def load_relationship(
    info: Info,
    ParentDBClass: Type[DBNode],
    relationship_attr: InstrumentedAttribute,
    gql_subfield: SelectedField,
    parent_rows: List[Row],
):
    ChildDBClass = relationship_attr.mapper.class_
    parent_ids = [row[0].id for row in parent_rows]

    parent_id_col = get_best_parent_id_col(relationship_attr.property, ParentDBClass)
    child_stmt = select(ChildDBClass, parent_id_col.label("parent_id"))

    if relationship_attr.property.secondary is not None:
        child_stmt = child_stmt.join(relationship_attr.property.secondary)
    elif parent_id_col == ParentDBClass.id and ParentDBClass == ChildDBClass:
        ChildDBClass = aliased(ChildDBClass)
        child_stmt = select(ChildDBClass, parent_id_col.label("parent_id"))
        child_stmt = child_stmt.join(ChildDBClass, relationship_attr)
    elif parent_id_col == ParentDBClass.id:
        child_stmt = child_stmt.join(relationship_attr)

    load_number = gql_subfield.arguments.get("first")

    for maybe_edges_field in gql_subfield.selections:
        if (
            isinstance(maybe_edges_field, SelectedField)
            and maybe_edges_field.name == "edges"
        ):
            for maybe_node_field in maybe_edges_field.selections:
                if (
                    isinstance(maybe_node_field, SelectedField)
                    and maybe_node_field.name == "node"
                ):
                    gql_subfield = maybe_node_field

    child_stmt = child_stmt.where(parent_id_col.in_(parent_ids))

    if load_number:
        cte = child_stmt.add_columns(
            sql_func.row_number()
            .over(partition_by=parent_id_col, order_by=ChildDBClass.id)
            .label("rn")
        ).cte()
        ChildDBClass = aliased(ChildDBClass, cte)  # type: ignore
        parent_id_col = cte.c.parent_id
        child_stmt = select(ChildDBClass, cte.c.parent_id).where(
            cte.c.rn <= int(load_number)
        )

    child_stmt = child_stmt.order_by(parent_id_col, ChildDBClass.id)

    child_rows = recursive_eager_load(info, child_stmt, ChildDBClass, gql_subfield)
    for k, g in groupby(child_rows, lambda row: row[1]):
        p = info.context.db_session.get(ParentDBClass, k)
        parent_ids.remove(k)
        gl = [row[0] for row in g]
        if relationship_attr.property.direction.name == "MANYTOONE":
            assert len(gl) == 1
            gl = gl[0]
        attributes.set_committed_value(p, relationship_attr.key, gl)

    # Handle the remaining parents that don't have any children
    for k in parent_ids:
        p = info.context.db_session.get(ParentDBClass, k)
        if relationship_attr.property.direction.name == "MANYTOONE":
            attributes.set_committed_value(p, relationship_attr.key, None)
        else:
            attributes.set_committed_value(p, relationship_attr.key, [])
