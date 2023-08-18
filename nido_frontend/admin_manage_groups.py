#  Nido admin_manage_groups.py
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

from .authentication import login_required
from .main_menu import get_admin_menu

bp = Blueprint("admin_groups", __name__)


@bp.route("/")
@login_required
def index():
    gql_query = """
query ManageGroups {
  activeCommunity {
    groups {
      edges {
        node {
          name
          members: customMembers {
            fullName
          }
          canUpdate: isAllowed(action: "update")
        }
      }
    }
  }
}"""
    gql_result = g.gql_client.execute_query(gql_query)
    groups = [edge.node for edge in gql_result.data.active_community.groups.edges]
    main_menu_links = get_admin_menu()
    return render_template(
        "manage-groups.html",
        main_menu_links=main_menu_links,
        groups=groups,
    )


@bp.route("/new-group/")
@login_required
def new_group():
    gql_query = """
query NewGroup {
  activeUser {
    id
    groups {
      id
      name
      right {
        id
        name
        childRights {
          id
          name
        }
      }
    }
  }
  activeCommunity {
    associates {
      edges {
        node {
          id
          collationName
        }
      }
    }
  }
}"""
    gql_result = g.gql_client.execute_query(gql_query)
    groups = gql_result.data.active_user.groups
    rights = [cr for group in groups if group.right for cr in group.right.child_rights]
    rights.extend([group.right for group in groups if group.right])
    associates = [
        edge.node for edge in gql_result.data.active_community.associates.edges
    ]
    main_menu_links = get_admin_menu()
    return render_template(
        "new-group.html",
        main_menu_links=main_menu_links,
        parent_groups=groups,
        rights=rights,
        users=associates,
        au_id=gql_result.data.active_user.id,
    )


@bp.post("/new-group/")
@login_required
def new_group_post():
    gql_mutation = """
mutation NewGroupPost($input: [NewGroupInput!]!) {
  groups {
    new(input: $input) {
      errors {
        message
      }
    }
  }
}"""
    gql_vars = {"input": {"name": request.form["name"]}}
    if right_id := request.form.get("right-id"):
        gql_vars["input"]["right"] = right_id
    if managing_group_id := request.form.get("managing-group-id"):
        gql_vars["input"]["managingGroup"] = managing_group_id
    if user_ids := request.form.getlist("user-id"):
        gql_vars["input"]["customMembers"] = user_ids
    gql_result = g.gql_client.execute_query(gql_mutation, gql_vars)
    return redirect(url_for(".index"))


def filter_users(user_id: str, member_list) -> bool:
    for member in member_list:
        if member["id"] == user_id:
            return False
    return True


@bp.route("/<group_name>/")
@login_required
def edit_group(group_name: str):
    gql_query = """
query EditGroup($name: String!) {
  activeCommunity {
    groups(filter: {name: $name}) {
      edges {
        node {
          id
          name
          managedBy {
            id
          }
          members: customMembers {
            id
            collationName
          }
          canUpdate: isAllowed(action: "update")
        }
      }
    }
    associates {
      edges {
        node {
          id
          collationName
        }
      }
    }
  }
  activeUser {
    id
    groups {
      id
      name
    }
  }
}"""
    gql_vars = {"name": group_name}
    gql_result = g.gql_client.execute_query(gql_query, gql_vars)
    if len(gql_result.data.active_community.groups["edges"]) != 1:
        abort(404)
    group = gql_result.data.active_community.groups.edges[0].node
    if not group.can_update:
        abort(403)
    nonmembers = [
        edge.node
        for edge in gql_result.data.active_community.associates.edges
        if filter_users(edge.node.id, group["members"])
    ]
    parent_groups = gql_result.data.active_user.groups

    main_menu_links = get_admin_menu()
    return render_template(
        "edit-group.html",
        main_menu_links=main_menu_links,
        group=group,
        nonmember_list=nonmembers,
        parent_groups=parent_groups,
    )


@bp.post("/<group_name>/")
@login_required
def edit_group_post(group_name: str):
    gql_variables: Dict[str, Dict[str, Union[str, List[str]]]]
    action = request.form.get("action")
    if action == "rename":
        gql_mutation = """
mutation ChangeSettingsPost(
  $input1: [RenameGroupInput!]!,
  $input2: [ChangeManagedByGroupInput!]!
) {
  groups {
    rename(input: $input1) {
      errors {
        message
      }
    }
    changeManagedBy(input: $input2) {
      errors {
        message
      }
    }
  }
}"""
        gql_variables = {
            "input1": {"group": request.form["group-id"], "name": request.form["name"]},
            "input2": {
                "group": request.form["group-id"],
                "managingGroup": request.form["managing-group-id"],
            },
        }
        group_name = request.form["name"]
    elif action == "add":
        gql_mutation = """
mutation AddMembersPost($input: [AddMembersGroupInput!]!) {
  groups {
    addMembers(input: $input) {
      errors {
        message
      }
    }
  }
}"""
        gql_variables = {
            "input": {
                "group": request.form["group-id"],
                "members": request.form.getlist("user-id"),
            }
        }
    elif action == "remove":
        gql_mutation = """
mutation RemoveMembersPost($input: [RemoveMembersGroupInput!]!) {
  groups {
    removeMembers(input: $input) {
      errors {
        message
      }
    }
  }
}"""
        gql_variables = {
            "input": {
                "group": request.form["group-id"],
                "members": request.form.getlist("user-id"),
            }
        }
    elif action == "delete":
        gql_mutation = """
mutation DeletePost($input: [DeleteGroupInput!]!) {
  groups {
    delete(input: $input) {
      errors {
        message
      }
    }
  }
}"""
        gql_variables = {"input": {"group": request.form["group-id"]}}
    else:
        abort(400)
    gql_result = g.gql_client.execute_query(gql_mutation, gql_variables)
    if action == "delete":
        return redirect(url_for(".index"))
    else:
        return redirect(url_for(".edit_group", group_name=group_name))
