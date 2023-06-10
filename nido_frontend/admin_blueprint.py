#  Nido admin_blueprint.py
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

from flask import Blueprint

from .admin_dashboard import bp as dash_bp
from .admin_dashboard import index as dash_index

bp = Blueprint("admin", __name__)

bp.register_blueprint(dash_bp, url_prefix="/dashboard")
bp.add_url_rule("/", endpoint="index", view_func=dash_index)
