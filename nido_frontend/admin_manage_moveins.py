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
    DBAssociate,
    DBOccupancyApplication,
    DBResidenceOccupancy,
    DBSignatureAssignment,
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
        select(DBOccupancyApplication)
        .where(DBOccupancyApplication.community_id == community_id)
        .options(
            selectinload(DBOccupancyApplication.applicant),
            selectinload(DBOccupancyApplication.residence),
        )
    )
    applications = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    return render_template(
        "manage-moveins.html",
        applications=applications,
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
    application = DBOccupancyApplication(
        community_id=community_id,
        residence_id=residence_id,
    )
    applicant = DBAssociate(
        community_id=community_id,
        personal_name=request.form["personal-name"],
        family_name=request.form["family-name"],
    )
    application.applicant = applicant
    try:
        begin_date = datetime.date.fromisoformat(request.form["begin-date"])
        application.scheduled_occupancy_start_date = begin_date
    except:
        pass

    if template_id := request.form.get("doc-id"):
        application.application_status = ApplicationStatus.AWAITING_APPLICANT_SIGNATURE
        sig_assign = DBSignatureAssignment(community_id, template_id, None)
        sig_assign.signer = applicant
        g.db_session.add(sig_assign)
    g.db_session.add(application)
    g.db_session.commit()
    return redirect(url_for(".index"))


@bp.route("/prospect-details")
@login_required
def prospect_details():
    app_id = request.args.get("id")
    if not app_id:
        return redirect(url_for(".index"))
    community_id = session.get("community_id")
    stmt = select(DBOccupancyApplication).where(
        DBOccupancyApplication.community_id == community_id,
        DBOccupancyApplication.id == app_id,
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
        select(DBAssociate)
        .join(DBAssociate.occupancy_applications)
        .where(
            DBOccupancyApplication.community_id == community_id,
        )
        .order_by(
            DBOccupancyApplication.scheduled_occupancy_start_date,
            DBAssociate.collation_name,
        )
    )
    applicants = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    today = datetime.date.today()
    return render_template(
        "confirm-movement.html",
        action="Move-in",
        default_date=today,
        associates=applicants,
        main_menu_links=main_menu_links,
    )


@bp.post("/confirm-movein/")
@login_required
def confirm_movein_post():
    a_id = request.form.get("associate-id")
    if not a_id:
        return abort(400)
    community_id = session.get("community_id")
    # TODO This isn't rigorous enough filtering; consider when the same person
    # has multiple applications.
    stmt = select(DBOccupancyApplication).where(
        DBOccupancyApplication.community_id == community_id,
        DBOccupancyApplication.applicant_id == a_id,
    )
    try:
        application: DBOccupancyApplication = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    try:
        begin_date = datetime.date.fromisoformat(request.form["date"])
    except:
        return abort(400)
    occupancy = DBResidenceOccupancy(
        occupant_id=a_id,
        community_id=community_id,
        residence_id=application.residence_id,
        date_begun=begin_date,
    )
    g.db_session.add(occupancy)
    g.db_session.delete(application)
    g.db_session.commit()
    return redirect(url_for(".index"))


@bp.route("/confirm-moveout/")
@login_required
def confirm_moveout():
    community_id = session.get("community_id")
    stmt = (
        select(DBAssociate)
        .join(DBResidenceOccupancy, DBResidenceOccupancy.occupant_id == DBAssociate.id)
        .where(
            DBResidenceOccupancy.community_id == community_id,
        )
        .order_by(DBResidenceOccupancy.date_ended, DBAssociate.collation_name)
    )
    occupants = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    today = datetime.date.today()
    return render_template(
        "confirm-movement.html",
        action="Move-out",
        default_date=today,
        associates=occupants,
        main_menu_links=main_menu_links,
    )


@bp.post("/confirm-moveout/")
@login_required
def confirm_moveout_post():
    a_id = request.form.get("associate-id")
    if not a_id:
        return abort(400)
    community_id = session.get("community_id")
    # XXX This is probably the best thing to do given the present state of the
    # codebase, but once the DB models are appropriately changed, this should
    # mark the occupancy end date and set it to inactive, not delete it.
    g.db_session.execute(
        delete(DBResidenceOccupancy).where(
            DBResidenceOccupancy.occupant_id == a_id,
            DBResidenceOccupancy.community_id == community_id,
        )
    )
    g.db_session.commit()
    return redirect(url_for(".index"))
