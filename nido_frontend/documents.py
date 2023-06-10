#  Nido documents.py
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
from typing import Optional

from flask import Blueprint, abort, g, make_response, redirect, render_template, session
from sqlalchemy import select

from nido_backend.db_models import DBDirFile, DBDirFolder

from .authentication import login_required
from .main_menu import get_main_menu

bp = Blueprint("documents", __name__)


def find_subfolder(name: str, folder: DBDirFolder) -> Optional[DBDirFolder]:
    for subfolder in folder.subfolders:
        if subfolder.name == name:
            return subfolder
    return None


@bp.route("/")
@bp.route("/<file_name>")
@bp.route("/<path:folder_path>/")
@bp.route("/<path:folder_path>/<file_name>")
@login_required
def index(folder_path=None, file_name=None):
    gql_query = """
query Documents {
  activeUser {
    isAdmin
  }
}"""
    community_id = session.get("community_id")
    gql_result = g.gql_client.execute_query(gql_query)
    stmt = select(DBDirFolder).where(
        DBDirFolder.community_id == community_id, DBDirFolder.parent_folder_id == None
    )
    folder = g.db_session.scalars(stmt).one()
    if folder_path is not None:
        for dir_name in folder_path.replace("_", " ").split("/"):
            maybe_folder = find_subfolder(dir_name, folder)
            if maybe_folder is not None:
                folder = maybe_folder
            else:
                abort(404)
    if file_name is None:
        main_menu_links = get_main_menu(gql_result.data.active_user.is_admin)
        return render_template(
            "documents.html",
            main_menu_links=main_menu_links,
            folder=folder,
            folder_path=folder_path,
        )

    doc = None
    for file in folder.files:
        if file.name == file_name.replace("_", " "):
            doc = file
    if doc is None:
        abort(404)
    if doc.url:
        return redirect(doc.url)
    elif doc.data:
        response = make_response(doc.data)
        response.headers.remove("Content-Type")
        return response
