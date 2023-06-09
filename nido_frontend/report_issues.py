#  Nido report_issues.py
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

from functools import reduce

from flask import Blueprint, g, redirect, render_template, request, url_for

from .authentication import login_required
from .main_menu import get_main_menu

bp = Blueprint("report_issues", __name__)


@bp.route("/")
@login_required
def index():
    gql_query = """
query Issues {
  activeUser {
    residences {
      issues {
        statusMsg
        isOpen
        description
      }
    }
  }
}"""
    gql_result = g.gql_client.execute_query(gql_query)
    residences = gql_result.data.active_user.residences
    open_issues = []
    closed_issues = []
    for residence in residences:
        for issue in residence.issues:
            if issue.is_open:
                open_issues.append(issue)
            else:
                closed_issues.append(issue)
    main_menu_links = get_main_menu()
    return render_template(
        "report-issues.html",
        main_menu_links=main_menu_links,
        open_issues=open_issues,
        closed_issues=closed_issues,
    )


@bp.route("/new-issue", methods=["GET", "POST"])
@login_required
def new_issue():
    gql_query = """
mutation NewIssue($description: String!) {
  issues {
    new(input: {description: $description}) {
      errors {
        message
      }
    }
  }
}"""
    if request.method == "POST":
        gql_vars = {"description": request.form["issue_description"]}
        gql_result = g.gql_client.execute_query(gql_query, gql_vars)
        return redirect(url_for(".index"))
    main_menu_links = get_main_menu()
    return render_template(
        "new-issue.html",
        main_menu_links=main_menu_links,
    )
