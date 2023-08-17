#  Nido admin_manage_moveins.py
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

import datetime

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
from sqlalchemy import delete, select
from sqlalchemy.orm import defer, selectinload

from nido_backend.db_models import (
    DBProspectiveResident,
    DBResidenceOccupancy,
    DBSignatureTemplate,
    DBUser,
)
from nido_backend.enums import ApplicationStatus
from nido_backend.gql_helpers import gql_id_to_table_id_unchecked

from .authentication import login_required
from .main_menu import get_admin_menu

bp = Blueprint("admin_moveins", __name__)


@bp.route("/")
@login_required
def index():
    # TODO refactor this to use GQL api when available
    community_id = session.get("community_id")
    stmt = (
        select(DBProspectiveResident)
        .where(DBProspectiveResident.community_id == community_id)
        .options(
            selectinload(DBProspectiveResident.residence),
            selectinload(DBProspectiveResident.signature_template).options(
                defer(DBSignatureTemplate.data)
            ),
        )
    )
    prs = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    return render_template(
        "manage-moveins.html",
        prospective_residents=prs,
        main_menu_links=main_menu_links,
    )


@bp.route("/register-prospect/")
@login_required
def add_prospie():
    # TODO refactor this to use GQL api when available
    community_id = session.get("community_id")
    docs_stmt = (
        select(DBSignatureTemplate)
        .where(DBSignatureTemplate.community_id == community_id)
        .options(defer(DBSignatureTemplate.data))
    )
    docs = g.db_session.execute(docs_stmt).scalars().all()
    gql_query = """
query AddProspective {
  activeCommunity {
    residences {
      edges {
        node {
          id
          unitNo
          street
        }
      }
    }
  }
}"""
    gql_result = g.gql_client.execute_query(gql_query)
    residences = [
        edge.node for edge in gql_result.data.active_community.residences.edges
    ]
    main_menu_links = get_admin_menu()
    return render_template(
        "register-prospective.html",
        residences=residences,
        sig_templates=docs,
        main_menu_links=main_menu_links,
    )


@bp.post("/register-prospect/")
@login_required
def add_prospie_post():
    community_id = session.get("community_id")
    residence_id = gql_id_to_table_id_unchecked(request.form["residence-id"])
    new_prospect = DBProspectiveResident(
        community_id=community_id,
        residence_id=residence_id,
        personal_name=request.form["personal-name"],
        family_name=request.form["family-name"],
        application_status=ApplicationStatus.AWAITING_MOVEIN,
    )
    try:
        begin_date = datetime.date.fromisoformat(request.form["begin-date"])
        new_prospect.scheduled_occupancy_start_date = begin_date
    except:
        pass

    if template_id := request.form.get("doc-id"):
        new_prospect.template_id = template_id
        new_prospect.application_status = ApplicationStatus.AWAITING_APPLICANT_SIGNATURE
    g.db_session.add(new_prospect)
    g.db_session.commit()
    return redirect(url_for(".index"))


@bp.route("/prospect-details")
@login_required
def prospect_details():
    pr_id = request.args.get("id")
    if not pr_id:
        return redirect(url_for(".index"))
    community_id = session.get("community_id")
    stmt = (
        select(DBProspectiveResident)
        .where(
            DBProspectiveResident.community_id == community_id,
            DBProspectiveResident.id == pr_id,
        )
        .options(
            selectinload(DBProspectiveResident.residence),
            selectinload(DBProspectiveResident.signature_template).options(
                defer(DBSignatureTemplate.data)
            ),
        )
    )
    try:
        prospect = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    main_menu_links = get_admin_menu()
    return render_template(
        "prospect-details.html",
        prospect=prospect,
        statuses=ApplicationStatus,
        main_menu_links=main_menu_links,
    )


@bp.route("/confirm-movein/")
@login_required
def confirm_movein():
    community_id = session.get("community_id")
    stmt = (
        select(DBProspectiveResident)
        .where(
            DBProspectiveResident.community_id == community_id,
        )
        .order_by(
            DBProspectiveResident.scheduled_occupancy_start_date,
            DBProspectiveResident.collation_name,
        )
    )
    prs = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    today = datetime.date.today()
    return render_template(
        "confirm-movement.html",
        action="Move-in",
        default_date=today,
        users=prs,
        main_menu_links=main_menu_links,
    )


@bp.post("/confirm-movein/")
@login_required
def confirm_movein_post():
    pr_id = request.form.get("user-id")
    if not pr_id:
        return abort(400)
    community_id = session.get("community_id")
    stmt = select(DBProspectiveResident).where(
        DBProspectiveResident.community_id == community_id,
        DBProspectiveResident.id == pr_id,
    )
    try:
        prospect: DBProspectiveResident = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    try:
        begin_date = datetime.date.fromisoformat(request.form["date"])
    except:
        return abort(400)
    if prospect.user_self_id is None:
        prospect.user_self = DBUser(
            personal_name=prospect.personal_name,
            family_name=prospect.family_name,
        )
        g.db_session.add(prospect.user_self)
        g.db_session.flush()
    occupancy = DBResidenceOccupancy(
        user_id=prospect.user_self.id,
        community_id=community_id,
        residence_id=prospect.residence_id,
        date_begun=begin_date,
    )
    g.db_session.add(occupancy)
    g.db_session.delete(prospect)
    g.db_session.commit()
    return redirect(url_for(".index"))


@bp.route("/confirm-moveout/")
@login_required
def confirm_moveout():
    community_id = session.get("community_id")
    stmt = (
        select(DBUser)
        .join(DBResidenceOccupancy, DBResidenceOccupancy.user_id == DBUser.id)
        .where(
            DBResidenceOccupancy.community_id == community_id,
        )
        .order_by(DBResidenceOccupancy.date_ended, DBUser.collation_name)
    )
    users = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    today = datetime.date.today()
    return render_template(
        "confirm-movement.html",
        action="Move-out",
        default_date=today,
        users=users,
        main_menu_links=main_menu_links,
    )


@bp.post("/confirm-moveout/")
@login_required
def confirm_moveout_post():
    user_id = request.form.get("user-id")
    if not user_id:
        return abort(400)
    community_id = session.get("community_id")
    # XXX This is probably the best thing to do given the present state of the
    # codebase, but once the DB models are appropriately changed, this should
    # mark the occupancy end date and set it to inactive, not delete it.
    g.db_session.execute(
        delete(DBResidenceOccupancy).where(
            DBResidenceOccupancy.user_id == user_id,
            DBResidenceOccupancy.community_id == community_id,
        )
    )
    g.db_session.commit()
    return redirect(url_for(".index"))
