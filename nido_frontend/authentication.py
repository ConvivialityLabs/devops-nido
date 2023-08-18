#  Nido authentication.py
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

import functools

from flask import (
    Blueprint,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from nido_backend.db_models import DBAssociate, DBContactMethod, DBEmailContact, DBUser


## Create login_required decorator
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            session["next"] = request.url
            return redirect(url_for("authentication.login"))
        return view(**kwargs)

    return wrapped_view


bp = Blueprint("authentication", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident = request.form.get("ident")
        stmt = (
            select(DBAssociate.user_id, DBAssociate.community_id)
            .select_from(DBContactMethod)
            .join(
                DBAssociate,
                DBContactMethod.user_id == DBAssociate.user_id,
            )
            .distinct()
            .where(DBEmailContact.email == ident)
        )
        try:
            (user_id, community_id) = g.db_session.execute(stmt).one()
        except NoResultFound:
            pass
        except MultipleResultsFound:
            # TODO: Design what to do when a user belongs to multiple communities
            pass
        except Exception as e:
            current_app.logger.error(f"Unexpected error during login of {ident}: {e}")
        else:
            session["user_id"] = user_id
            session["community_id"] = community_id
            # The flask-login docs insist that it's necessary to validate the
            # next_url parameter, but that's for when it's a url query. Since
            # here it's passed as a secure server-generated cookie, it should
            # be fine.
            next_url = session.pop("next_url", None)
            return redirect(next_url or url_for("index"))

    return render_template("login.html")


@bp.route("/logout")
def logout():
    user_id = session.pop("user_id", None)
    community_id = session.pop("community_id", None)
    return redirect(url_for(".login"))
