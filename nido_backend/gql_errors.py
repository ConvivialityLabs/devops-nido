#  Nido gql_errors.py
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

from sqlite3 import IntegrityError as SQLiteIntegrityError
from typing import Optional

import strawberry
from sqlalchemy.exc import IntegrityError as SQLAlchIntegrityError


@strawberry.interface
class Error:
    message: str
    source: Optional["Error"] = None


@strawberry.type
class AlreadyTaken(Error):
    message: str = "The data you submitted was already taken"


@strawberry.type
class NotFound(Error):
    message: str = "The data you submitted could not be found"


@strawberry.type
class Unauthorized(Error):
    message: str = "Unauthorized"


@strawberry.type
class DatabaseError(Error):
    message: str = "Unknown Database Error"


def parse_integrity_error(db_error: SQLAlchIntegrityError) -> Error:
    if isinstance(db_error.orig, SQLiteIntegrityError):
        err_str = str(db_error.orig)
        if err_str.startswith("UNIQUE"):
            return AlreadyTaken(message=err_str)
        else:
            return DatabaseError()
    else:
        return DatabaseError()
