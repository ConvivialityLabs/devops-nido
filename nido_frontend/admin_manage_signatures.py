#  Nido admin_manage_signatures.py
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
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import defer, joinedload

from nido_backend.db_models import (
    DBResidenceOccupancy,
    DBSignatureAssignment,
    DBSignatureRecord,
    DBSignatureTemplate,
    DBUser,
)

from .authentication import login_required
from .main_menu import get_admin_menu

bp = Blueprint("admin_signatures", __name__)


@bp.route("/")
@login_required
def index():
    community_id = session.get("community_id")
    docs_stmt = (
        select(DBSignatureTemplate)
        .where(DBSignatureTemplate.community_id == community_id)
        .options(defer(DBSignatureTemplate.data))
    )
    docs = g.db_session.execute(docs_stmt).scalars().all()
    stmt = (
        select(DBSignatureAssignment)
        .where(DBSignatureAssignment.community_id == community_id)
        .options(
            joinedload(DBSignatureAssignment.signature_template).options(
                defer(DBSignatureTemplate.data)
            )
        )
    )
    pending_sigs = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    return render_template(
        "manage-signatures.html",
        docs=docs,
        pending_sigs=pending_sigs,
        main_menu_links=main_menu_links,
    )


@bp.route("/upload-document/")
@login_required
def upload_document():
    main_menu_links = get_admin_menu()
    return render_template(
        "upload-unsigned.html",
        main_menu_links=main_menu_links,
    )


@bp.post("/upload-document/")
@login_required
def upload_document_post():
    community_id = session.get("community_id")
    file = request.files["pdf-file"]
    w = IncrementalPdfFileWriter(file)
    page = int(request.form["page"])
    x1 = int(request.form["x1"])
    y1 = int(request.form["y1"])
    x2 = int(request.form["x2"])
    y2 = int(request.form["y2"])
    sig_field_name = "Signature"
    spec = SigFieldSpec(
        sig_field_name=sig_field_name,
        on_page=page - 1,
        box=(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)),
    )
    doc_name = file.filename[:-4] if file.filename[-4:] == ".pdf" else file.filename
    append_signature_field(w, spec)
    w.write_in_place()
    db_entry = DBSignatureTemplate(
        community_id=community_id,
        name=doc_name,
        data=file.getvalue(),
        signature_field_name=sig_field_name,
    )
    g.db_session.add(db_entry)
    g.db_session.commit()
    return redirect(url_for(".index"))


@bp.route("/manage/<name>/")
@login_required
def manage_template(name: str):
    community_id = session.get("community_id")
    stmt = select(DBSignatureTemplate).where(
        DBSignatureTemplate.community_id == community_id,
        DBSignatureTemplate.name == name,
    )
    try:
        doc = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    b64url = f"data:application/pdf;base64," + base64.b64encode(doc.data).decode(
        encoding="utf-8"
    )
    main_menu_links = get_admin_menu()
    return render_template(
        "manage-sig-template.html",
        doc=doc,
        b64url=b64url,
        main_menu_links=main_menu_links,
    )


@bp.post("/manage/<name>/")
@login_required
def manage_template_post(name: str):
    community_id = session.get("community_id")
    action = request.form.get("action")
    if action == "rename":
        g.db_session.execute(
            update(DBSignatureTemplate),
            [{"id": request.form["doc-id"], "name": request.form["new-name"]}],
        )
        redirect_url = url_for(".manage_template_post", name=request.form["new-name"])
    elif action == "delete":
        g.db_session.execute(
            delete(DBSignatureTemplate).where(
                DBSignatureTemplate.id == request.form["doc-id"],
                DBSignatureTemplate.community_id == community_id,
            )
        )
        redirect_url = url_for(".index")
    else:
        abort(400)
    g.db_session.commit()
    return redirect(redirect_url)


@bp.route("/assign-signatures/")
@login_required
def assign_signatures():
    community_id = session.get("community_id")
    docs_stmt = (
        select(DBSignatureTemplate)
        .where(DBSignatureTemplate.community_id == community_id)
        .options(defer(DBSignatureTemplate.data))
    )
    docs = g.db_session.execute(docs_stmt).scalars().all()
    users_stmt = (
        select(DBUser)
        .join(DBResidenceOccupancy, DBResidenceOccupancy.user_id == DBUser.id)
        .where(DBResidenceOccupancy.community_id == community_id)
        .order_by(DBUser.collation_name)
    )
    residents = g.db_session.execute(users_stmt).scalars().all()
    main_menu_links = get_admin_menu()
    return render_template(
        "assign-signatures.html",
        docs=docs,
        residents=residents,
        main_menu_links=main_menu_links,
    )


@bp.post("/assign-signatures/")
@login_required
def assign_signatures_post():
    community_id = session.get("community_id")
    user_ids = request.form.getlist("user-id")
    doc_id = request.form.get("document-id")
    g.db_session.execute(
        insert(DBSignatureAssignment).values(
            template_id=int(doc_id), community_id=community_id
        ),
        [{"user_id": int(user_id)} for user_id in user_ids],
    )
    g.db_session.commit()
    return redirect(url_for(".index"))


@bp.route("/view-signed/")
@login_required
def view_all_signed():
    community_id = session.get("community_id")
    stmt = (
        select(DBSignatureRecord)
        .where(
            DBSignatureRecord.community_id == community_id,
        )
        .options(joinedload(DBSignatureRecord.user))
    )
    signed_docs = g.db_session.execute(stmt).scalars().all()
    main_menu_links = get_admin_menu()
    return render_template(
        "all-signatures.html",
        docs=signed_docs,
        main_menu_links=main_menu_links,
    )


@bp.route("/view-signed/<doc_name>/")
@login_required
def view_signed(doc_name: str):
    community_id = session.get("community_id")
    stmt = select(DBSignatureRecord).where(
        DBSignatureRecord.community_id == community_id,
        DBSignatureRecord.name == doc_name,
    )
    try:
        doc = g.db_session.execute(stmt).scalars().one()
    except:
        return abort(404)
    b64url = f"data:application/pdf;base64," + base64.b64encode(doc.data).decode(
        encoding="utf-8"
    )
    main_menu_links = get_admin_menu()
    return render_template(
        "view-signed-doc.html",
        doc=doc,
        b64url=b64url,
        main_menu_links=main_menu_links,
    )
