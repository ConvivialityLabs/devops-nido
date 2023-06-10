#  Nido admin_dashboard.py
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

from flask import Blueprint, abort, g, render_template

from .authentication import login_required
from .main_menu import get_admin_menu

bp = Blueprint("admin_dashboard", __name__)


@bp.route("/")
@login_required
def index():
    gql_query = """
query AdminDash {
  activeUser {
    isAdmin
  }
}"""

    gql_result = g.gql_client.execute_query(gql_query)
    if not gql_result.data.active_user.is_admin:
        abort(403)
    main_menu_links = get_admin_menu()
    return render_template("admin-dash.html", main_menu_links=main_menu_links)
