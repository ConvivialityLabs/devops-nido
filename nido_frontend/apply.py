#  Nido apply.py
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

import base64
import datetime
import io

from flask import (
    Blueprint,
    abort,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from pyhanko import stamp
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko.sign.fields import SigSeedSubFilter
from pyhanko_certvalidator import ValidationContext
from sqlalchemy import delete, select
from sqlalchemy.orm import defer, joinedload, load_only

from nido_backend.db_models import (
    DBAssociate,
    DBOccupancyApplication,
    DBSignatureAssignment,
    DBSignatureRecord,
    DBSignatureTemplate,
    DBUser,
)
from nido_backend.enums import ApplicationStatus

from .authentication import login_required
from .main_menu import get_main_menu

bp = Blueprint("apply", __name__)


@bp.route("/sign")
def sign_doc():
    app_id = request.args.get("id")
    if not app_id:
        return abort(404)
    stmt = (
        select(DBAssociate)
        .join(DBOccupancyApplication)
        .where(
            DBOccupancyApplication.id == app_id,
            DBOccupancyApplication.application_status
            == ApplicationStatus.AWAITING_APPLICANT_SIGNATURE,
        )
    )
    try:
        applicant = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    doc_stmt = (
        select(DBSignatureTemplate)
        .select_from(DBSignatureAssignment)
        .join(DBSignatureAssignment.signature_template)
        .where(DBSignatureAssignment.signer_id == applicant.id)
    )
    try:
        doc = g.db_session.execute(doc_stmt).scalars().one()
    except:
        return abort(404)
    b64url = f"data:application/pdf;base64," + base64.b64encode(doc.data).decode(
        encoding="utf-8"
    )
    return render_template(
        "sign-docs.html",
        doc=doc,
        b64url=b64url,
        user_name=applicant.full_name,
    )


@bp.post("/sign")
def sign_doc_post():
    app_id = request.args.get("id")
    if not app_id:
        return abort(404)
    stmt = select(DBOccupancyApplication).where(
        DBOccupancyApplication.id == app_id,
        DBOccupancyApplication.application_status
        == ApplicationStatus.AWAITING_APPLICANT_SIGNATURE,
    )
    try:
        app = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    doc_stmt = (
        select(DBSignatureTemplate)
        .select_from(DBSignatureAssignment)
        .join(DBSignatureAssignment.signature_template)
        .where(DBSignatureAssignment.signer_id == app.applicant_id)
    )
    try:
        doc = g.db_session.execute(doc_stmt).scalars().one()
    except:
        return abort(404)

    try:
        user_name = request.form["user-name"]
    except:
        return abort(403)
    signer = getattr(g, "cms_signer", None)
    if signer is None:
        return abort(500)
    tsa_client = getattr(g, "tsa_client", None)

    pdf_writer = IncrementalPdfFileWriter(io.BytesIO(doc.data))

    signature_meta = signers.PdfSignatureMetadata(
        field_name=doc.signature_field_name,
        name=user_name,
        md_algorithm="sha256",
        subfilter=SigSeedSubFilter.PADES,
        use_pades_lta=True,
    )
    stamp_style = stamp.TextStampStyle(
        stamp_text=f"Signed by: %(signer)s\nTime: %(ts)s",
        border_width=0,
        background_opacity=0,
    )

    out = signers.PdfSigner(
        signer=signer,
        stamp_style=stamp_style,
        timestamper=tsa_client,
        signature_meta=signature_meta,
    ).sign_pdf(
        pdf_writer,
        existing_fields_only=True,
        in_place=True,
    )
    app.application_status = ApplicationStatus.AWAITING_MOVEIN
    g.db_session.add(app)
    record = DBSignatureRecord(
        community_id=app.community_id,
        signer_id=app.applicant.id,
        data=out.read(),
        name=doc.name,
        signature_date=datetime.date.today(),
    )
    g.db_session.add(record)
    g.db_session.execute(
        delete(DBSignatureAssignment).where(
            DBSignatureAssignment.community_id == app.community_id,
            DBSignatureAssignment.signer_id == app.applicant.id,
            DBSignatureAssignment.template_id == doc.id,
        )
    )
    g.db_session.commit()
    session["record_id"] = record.id
    return redirect(url_for(".view"))


@bp.route("/view")
def view():
    try:
        doc = g.db_session.get(DBSignatureRecord, session["record_id"])
        assert doc is not None
    except:
        return abort(404)

    b64url = f"data:application/pdf;base64," + base64.b64encode(doc.data).decode(
        encoding="utf-8"
    )
    return render_template(
        "view-signed-doc.html",
        doc=doc,
        b64url=b64url,
    )
