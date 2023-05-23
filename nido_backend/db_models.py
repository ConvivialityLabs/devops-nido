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
from dataclasses import field, make_dataclass
from functools import reduce
from typing import List, Optional

import sqlalchemy.schema as sql_schema
import sqlalchemy.types as sql_types
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from .enums import PermissionsFlag


class BooleanFlag(sql_types.TypeDecorator):
    impl = sql_types.Boolean
    cache_ok = True

    def __init__(self, true_flag, false_flag, *arg, **kw):
        self.true_flag = true_flag
        self.false_flag = false_flag
        sql_types.TypeDecorator.__init__(self, *arg, **kw)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        try:
            return value & self.true_flag == self.true_flag
        except:
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif value is True:
            return self.true_flag
        else:
            return self.false_flag


class Base(DeclarativeBase, MappedAsDataclass):
    pass


class DBCommunity(Base):
    __tablename__ = "community"

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    name: Mapped[str]

    residences: Mapped[List["DBResidence"]] = relationship(
        back_populates="community", init=False, repr=False
    )
    groups: Mapped[List["DBGroup"]] = relationship(
        back_populates="community", viewonly=True, init=False, repr=False
    )
    rights: Mapped[List["DBRight"]] = relationship(
        back_populates="community", viewonly=True, init=False, repr=False
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
    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id", ondelete="CASCADE")
    )

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
            ondelete="RESTRICT",
        ),
    )
    # CASCADE when community is deleted, because deleting the community can
    # only mean that they are no longer interested in using the service. But
    # if a residence known to have occupants is deleted, what does that mean?
    # Unclear, so RESTRICT and have the programmer delete the occupancy first
    # if the deletion is intentional. Same reason for user_id RESTRICT.

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id", ondelete="CASCADE"), primary_key=True
    )
    residence_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="RESTRICT"), primary_key=True
    )


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
    groups: Mapped[List["DBGroup"]] = relationship(
        secondary="group_membership",
        back_populates="custom_members",
        init=False,
        repr=False,
    )


class DBGroup(Base):
    __tablename__ = "group"
    __table_args__ = (
        sql_schema.UniqueConstraint("id", "community_id"),
        sql_schema.UniqueConstraint("community_id", "name"),
        sql_schema.ForeignKeyConstraint(
            ["managing_group_id", "community_id"],
            ["group.id", "group.community_id"],
            # DEFERRABLE INITIALLY DEFERRED is necessary in sqlite for defered
            # enforcement of this foreign key constraint. Defered enforcement
            # is needed to correctly build the row when a group manages itself.
            deferrable=True,
            initially="DEFERRED",
            # Use ON DELETE SET DEFAULT with nonsense defaults in the columns.
            # ON DELETE CASCADE is the wrong behavior; we don't want users
            # unthinkingly deleting a parent group and unintentionally deleting
            # all child groups.
            # ON DELETE RESTRICT and ON DELETE SET NULL don't work well with
            # rows that self-reference.
            ondelete="SET DEFAULT",
        ),
        sql_schema.ForeignKeyConstraint(
            ["right_id", "community_id"],
            ["right.id", "right.community_id"],
            # ON DELETE NO ACTION because the right_id single column constraint
            # will set the column to NULL and community_id shouldn't be changed
            ondelete="NO ACTION",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id", ondelete="CASCADE"), server_default="0"
    )
    managing_group_id: Mapped[int] = mapped_column(server_default="0", init=False)
    right_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("right.id", ondelete="SET NULL"), init=False
    )

    name: Mapped[str]

    community: Mapped[DBCommunity] = relationship(
        back_populates="groups", viewonly=True, init=False, repr=False
    )
    managed_by: Mapped["DBGroup"] = relationship(
        back_populates="manages",
        remote_side=[id, community_id],
        passive_deletes="all",
        init=False,
        repr=False,
    )
    manages: Mapped[List["DBGroup"]] = relationship(
        back_populates="managed_by",
        passive_deletes="all",
        init=False,
        repr=False,
    )
    right: Mapped[Optional["DBRight"]] = relationship(
        back_populates="groups",
        foreign_keys=[right_id],
        init=False,
        repr=False,
    )
    custom_members: Mapped[List[DBUser]] = relationship(
        secondary="group_membership",
        back_populates="groups",
        init=False,
        repr=False,
    )


class DBGroupMembership(Base):
    __tablename__ = "group_membership"
    __table_args__ = (
        sql_schema.ForeignKeyConstraint(
            ["group_id", "community_id"],
            ["group.id", "group.community_id"],
            ondelete="CASCADE",
        ),
    )

    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )


# Creates a class with SQLALchemy mapped Boolean columns for each member
# of PermissionsFlag.
PermissionsMixin = make_dataclass(
    "PermissionsMixin",
    [
        (
            member.name.lower(),
            Mapped[BooleanFlag],
            field(
                default=mapped_column(
                    BooleanFlag(member, PermissionsFlag(0)),
                    default=PermissionsFlag(0),
                    init=False,
                )
            ),
        )
        for member in PermissionsFlag
        if member.name is not None
    ],
    bases=(MappedAsDataclass,),
)


class DBRight(Base, PermissionsMixin):  # type: ignore
    __tablename__ = "right"
    __table_args__ = (
        sql_schema.UniqueConstraint("id", "community_id"),
        sql_schema.UniqueConstraint("community_id", "name"),
        sql_schema.ForeignKeyConstraint(
            ["parent_right_id", "community_id"],
            ["right.id", "right.community_id"],
            # DEFERRABLE INITIALLY DEFERRED is necessary in sqlite for defered
            # enforcement of this foreign key constraint. Defered enforcement is
            # needed to correctly build the row when a right is its own parent.
            deferrable=True,
            initially="DEFERRED",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    community_id: Mapped[int] = mapped_column(
        ForeignKey("community.id", ondelete="CASCADE"), server_default="0"
    )
    parent_right_id: Mapped[int] = mapped_column(server_default="0", init=False)

    name: Mapped[str]

    @hybrid_property
    def permissions(self):
        return reduce(
            lambda a, b: a | b, [getattr(self, m.name.lower()) for m in PermissionsFlag]
        )

    @permissions.inplace.expression
    @classmethod
    def _permissions_expression(cls):
        return reduce(
            lambda a, b: a + b,
            [m.value for m in PermissionsFlag if getattr(cls, m.name.lower())],
        )

    @permissions.inplace.setter
    def _permissions_setter(self, value: PermissionsFlag):
        for member in PermissionsFlag:
            setattr(self, member.name.lower(), member & value)  # type: ignore

    @hybrid_method
    def permits(self, request):
        return self.permissions & request == request

    community: Mapped[DBCommunity] = relationship(
        back_populates="rights", viewonly=True, init=False, repr=False
    )
    parent_right: Mapped["DBRight"] = relationship(
        back_populates="child_rights",
        remote_side=[id, community_id],
        passive_deletes="all",
        init=False,
        repr=False,
    )
    child_rights: Mapped[List["DBRight"]] = relationship(
        back_populates="parent_right",
        passive_deletes="all",
        init=False,
        repr=False,
    )
    groups: Mapped[List[DBGroup]] = relationship(
        back_populates="right",
        foreign_keys=[DBGroup.right_id],
        init=False,
        repr=False,
    )


class ContactType(enum.Enum):
    Email = 1


class DBContactMethod(Base):
    __tablename__ = "contact_method"

    id: Mapped[int] = mapped_column(primary_key=True, init=False, repr=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
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
        "polymorphic_load": "inline",
    }
