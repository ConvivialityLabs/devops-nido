#  Nido signatures.py
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
    DBSignatureAssignment,
    DBSignatureRecord,
    DBSignatureTemplate,
    DBUser,
)

from .authentication import login_required
from .main_menu import get_main_menu

bp = Blueprint("signatures", __name__)


@bp.route("/")
@login_required
def index():
    gql_query = """
query  {
  activeUser {
    isAdmin
  }
}"""
    community_id = session.get("community_id")
    user_id = session.get("user_id")
    stmt = (
        select(DBSignatureAssignment)
        .where(
            DBSignatureAssignment.community_id == community_id,
            DBSignatureAssignment.user_id == user_id,
        )
        .options(
            joinedload(DBSignatureAssignment.signature_template).options(
                load_only(DBSignatureTemplate.name)
            )
        )
    )
    pending_sigs = g.db_session.execute(stmt).scalars().all()
    gql_result = g.gql_client.execute_query(gql_query)
    main_menu_links = get_main_menu(gql_result.data.active_user.is_admin)
    return render_template(
        "signatures.html",
        main_menu_links=main_menu_links,
        pending_sigs=pending_sigs,
    )


@bp.route("/sign/<doc_name>/")
@login_required
def sign_doc(doc_name: str):
    gql_query = """
query  {
  activeUser {
    isAdmin
    fullName
  }
}"""
    community_id = session.get("community_id")
    user_id = session.get("user_id")
    stmt = (
        select(DBSignatureTemplate)
        .select_from(DBSignatureAssignment)
        .join(DBSignatureAssignment.signature_template)
        .where(
            DBSignatureTemplate.community_id == community_id,
            DBSignatureAssignment.user_id == user_id,
            DBSignatureTemplate.name == doc_name,
        )
    )
    try:
        doc = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    b64url = f"data:application/pdf;base64," + base64.b64encode(doc.data).decode(
        encoding="utf-8"
    )
    gql_result = g.gql_client.execute_query(gql_query)
    main_menu_links = get_main_menu(gql_result.data.active_user.is_admin)
    return render_template(
        "sign-docs.html",
        doc=doc,
        b64url=b64url,
        user_name=gql_result.data.active_user.full_name,
        main_menu_links=main_menu_links,
    )


@bp.post("/sign/<doc_name>/")
@login_required
def sign_doc_post(doc_name: str):
    community_id = session.get("community_id")
    assert community_id is not None
    user_id = session.get("user_id")
    assert user_id is not None
    stmt = (
        select(DBSignatureTemplate)
        .select_from(DBSignatureAssignment)
        .join(DBSignatureAssignment.signature_template)
        .where(
            DBSignatureTemplate.community_id == community_id,
            DBSignatureAssignment.user_id == user_id,
            DBSignatureTemplate.name == doc_name,
        )
    )
    try:
        doc = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    try:
        user_name = request.form["user-name"]
    except:
        abort(403)

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
    record = DBSignatureRecord(
        community_id=community_id,
        user_id=user_id,
        data=out.read(),
        name=doc_name,
        signature_date=datetime.date.today(),
    )
    g.db_session.add(record)
    g.db_session.execute(
        delete(DBSignatureAssignment).where(
            DBSignatureAssignment.community_id == community_id,
            DBSignatureAssignment.user_id == user_id,
            DBSignatureAssignment.template_id == doc.id,
        )
    )
    g.db_session.commit()
    return redirect(url_for(".index"))


@bp.route("/view/")
@login_required
def view_docs():
    gql_query = """
query  {
  activeUser {
    isAdmin
  }
}"""
    community_id = session.get("community_id")
    user_id = session.get("user_id")
    stmt = (
        select(DBSignatureRecord)
        .where(
            DBSignatureRecord.community_id == community_id,
            DBSignatureRecord.user_id == user_id,
        )
        .options(defer(DBSignatureRecord.data))
    )
    signed_docs = g.db_session.execute(stmt).scalars().all()
    gql_result = g.gql_client.execute_query(gql_query)
    main_menu_links = get_main_menu(gql_result.data.active_user.is_admin)
    return render_template(
        "my-signatures.html",
        docs=signed_docs,
        main_menu_links=main_menu_links,
    )


@bp.route("/view/<doc_name>/")
@login_required
def view_single(doc_name: str):
    gql_query = """
query  {
  activeUser {
    isAdmin
  }
}"""
    community_id = session.get("community_id")
    user_id = session.get("user_id")
    stmt = select(DBSignatureRecord).where(
        DBSignatureRecord.community_id == community_id,
        DBSignatureRecord.user_id == user_id,
        DBSignatureRecord.name == doc_name,
    )
    try:
        doc = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    b64url = f"data:application/pdf;base64," + base64.b64encode(doc.data).decode(
        encoding="utf-8"
    )
    gql_result = g.gql_client.execute_query(gql_query)
    main_menu_links = get_main_menu(gql_result.data.active_user.is_admin)
    return render_template(
        "view-signed-doc.html",
        doc=doc,
        b64url=b64url,
        main_menu_links=main_menu_links,
    )
