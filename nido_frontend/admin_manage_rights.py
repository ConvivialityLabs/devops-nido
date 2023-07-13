#  Nido admin_manage_rights.py
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

from typing import Dict, List, Optional, Union

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from nido_backend.enums import PermissionsFlag

from .authentication import login_required
from .main_menu import get_admin_menu

bp = Blueprint("admin_rights", __name__)


@bp.route("/")
@login_required
def index():
    gql_query = """
query ManageRights {
  activeCommunity {
    rights {
      edges {
        node {
          id
          name
          groups {
            name
          }
          canRevoke: isAllowed(action: "revoke")
        }
      }
    }
  }
}"""
    gql_result = g.gql_client.execute_query(gql_query)
    rights = [edge.node for edge in gql_result.data.active_community.rights.edges]
    main_menu_links = get_admin_menu()
    return render_template(
        "manage-rights.html",
        main_menu_links=main_menu_links,
        rights=rights,
    )


@bp.post("/")
@login_required
def index_post():
    gql_mutation = """
mutation RevokeRight($input: [RevokeRightInput!]!) {
  rights {
    revoke(input: $input) {
      errors {
        message
      }
    }
  }
}"""
    gql_vars = {"input": {"right": request.form["right-id"]}}
    gql_result = g.gql_client.execute_query(gql_mutation, gql_vars)
    return redirect(url_for(".index"))


@bp.route("/new-group/")
@login_required
def new_right():
    gql_query = """
query NewRight {
  activeUser {
    groups {
      right {
        id
        name
        permissions
      }
    }
  }
}"""
    gql_result = g.gql_client.execute_query(gql_query)
    rights = [
        group.right
        for group in gql_result.data.active_user.groups
        if group.right and "CAN_DELEGATE" in group.right["permissions"]
    ]
    main_menu_links = get_admin_menu()
    return render_template(
        "new-right.html",
        main_menu_links=main_menu_links,
        parents=rights,
        perms=PermissionsFlag,
    )


@bp.post("/new-group/")
@login_required
def new_group_post():
    gql_mutation = """
mutation DelegateRight($input: [DelegateRightInput!]!) {
  rights {
    delegate(input: $input) {
      errors {
        message
      }
    }
  }
}"""
    gql_vars = {
        "input": {"name": request.form["name"], "parentId": request.form["parent-id"]}
    }
    perm_list = []
    for member in PermissionsFlag:
        if request.form.get(member.name):
            perm_list.append(member.name)
    gql_vars["input"]["permissions"] = perm_list
    gql_result = g.gql_client.execute_query(gql_mutation, gql_vars)
    return redirect(url_for(".index"))
