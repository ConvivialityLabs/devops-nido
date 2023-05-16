#  Nido db_models.py
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

import enum
from typing import List, Optional

import sqlalchemy.schema as sql_schema
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase, MappedAsDataclass):
    pass


class DBCommunity(Base):
    __tablename__ = "community"

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    name: Mapped[str]

    residences: Mapped[List["DBResidence"]] = relationship(
        back_populates="community", init=False, repr=False
    )

    users: Mapped[List["DBUser"]] = relationship(
        secondary="residence_occupancy",
        viewonly=True,
        init=False,
        repr=False,
    )


class DBResidence(Base):
    __tablename__ = "residence"
    __table_args__ = (sql_schema.UniqueConstraint("id", "community_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    community_id: Mapped[int] = mapped_column(ForeignKey("community.id"))

    unit_no: Mapped[Optional[str]]
    street: Mapped[str]
    locality: Mapped[str]
    postcode: Mapped[str]
    region: Mapped[str]

    community: Mapped[DBCommunity] = relationship(
        back_populates="residences", init=False, repr=False
    )
    occupants: Mapped[List["DBUser"]] = relationship(
        secondary="residence_occupancy",
        back_populates="residences",
        init=False,
        repr=False,
    )


class DBResidenceOccupancy(Base):
    __tablename__ = "residence_occupancy"
    __table_args__ = (
        sql_schema.ForeignKeyConstraint(
            ["residence_id", "community_id"],
            ["residence.id", "residence.community_id"],
        ),
    )

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id"), primary_key=True
    )
    residence_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)


class DBUser(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    personal_name: Mapped[str]
    family_name: Mapped[str]

    residences: Mapped[List[DBResidence]] = relationship(
        secondary="residence_occupancy",
        back_populates="occupants",
        init=False,
        repr=False,
    )
    contact_methods: Mapped[List["DBContactMethod"]] = relationship(
        back_populates="user", init=False, repr=False
    )


class ContactType(enum.Enum):
    Email = 1


class DBContactMethod(Base):
    __tablename__ = "contact_method"

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    type: Mapped[ContactType] = mapped_column(init=False, repr=False)

    user: Mapped[DBUser] = relationship(
        back_populates="contact_methods", init=False, repr=False
    )

    __mapper_args__ = {
        "polymorphic_on": "type",
    }


class DBEmailContact(DBContactMethod):
    email: Mapped[str] = mapped_column(unique=True, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": ContactType.Email,
    }
