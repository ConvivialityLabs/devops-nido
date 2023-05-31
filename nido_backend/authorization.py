#  Nido authorization.py
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
from oso import AuthorizationError, ForbiddenError, NotFoundError, Oso

from .db_models import DBBillingCharge, DBContactMethod, DBGroup, DBRight, DBUser
from .enums import PermissionsFlag

oso = Oso(read_action="query")

oso.register_class(DBBillingCharge, name="BillingCharge")
oso.register_class(DBContactMethod, name="ContactMethod")
oso.register_class(DBGroup, name="Group")
oso.register_class(DBRight, name="Right")
oso.register_class(DBUser, name="User")

oso.register_class(PermissionsFlag, name="Permissions")

oso.load_files(["nido_backend/auth_rules.polar"])
