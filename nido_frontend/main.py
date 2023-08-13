#  Nido main.py
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

import dataclasses
import os
import secrets
from typing import Any

from flask import Flask, Request, Response, current_app, g, render_template, session
from pyhanko.sign import signers, timestamps
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from strawberry import Schema
from strawberry.flask.views import GraphQLView

from nido_backend.gql_query import Issue
from nido_backend.gql_schema import SchemaContext, create_schema

from .admin_blueprint import bp as admin_bp
from .authentication import bp as auth_bp
from .authentication import login_required
from .billing import bp as billing_bp
from .documents import bp as documents_bp
from .household import bp as household_bp
from .household import index as household_index
from .report_issues import bp as issues_bp
from .resident_directory import bp as rd_bp
from .signatures import bp as signing_bp

dev_issue_list = [
    Issue(
        is_open=True,
        description="Construction in the parking lot is scheduled for next month.",
    ),
    Issue(
        is_open=True,
        description="The light is out in the first floor hallway.",
        status_msg="An electrician is scheduled to come out on Monday.",
    ),
    Issue(
        is_open=False,
        description="The front gate does not always latch.",
        status_msg="Eric has repaired it on 3/28.",
    ),
]


class GraphQLWithDB(GraphQLView):
    def get_context(self, request: Request, response: Response) -> Any:
        user_id = session.get("user_id")
        community_id = session.get("community_id")
        db_session = g.db_session

        return SchemaContext(dev_issue_list, db_session, user_id, community_id)


class GraphQLDataDict(dict):
    def __getattr__(self, attr):
        words = [
            word.title() if i > 0 else word for i, word in enumerate(attr.split("_"))
        ]
        camel_case_attr = "".join(words)
        result = self.get(camel_case_attr)
        if isinstance(result, dict):
            return GraphQLDataDict(result)
        elif isinstance(result, list):
            return [GraphQLDataDict(i) for i in result]
        else:
            return result


@dataclasses.dataclass
class IntegratedGraphQLClient:
    gql_schema: Schema

    def execute_query(self, query, variable_values=None):
        user_id = session.get("user_id")
        community_id = session.get("community_id")
        db_session = g.db_session

        context = SchemaContext(dev_issue_list, db_session, user_id, community_id)
        result = self.gql_schema.execute_sync(query, variable_values, context)
        result.data = GraphQLDataDict(result.data)
        return result


def create_app(testing_config=None):
    app = Flask(
        "nido_frontend",
        instance_path=os.environ.get("NIDO_VARDIR"),
        instance_relative_config=True,
        template_folder="resources/html_templates",
        static_folder="resources/static",
    )
    if app.debug:
        os.makedirs(app.instance_path, exist_ok=True)

    if testing_config:
        app.config.from_mapping(testing_config)
    else:
        conf_file = os.environ.get("NIDO_CONFIG_FILE") or "nido.cfg"
        try:
            app.config.from_pyfile(conf_file)
        except:
            if not app.debug:
                raise
            key = secrets.token_hex()
            app.config["SECRET_KEY"] = key
            with app.open_instance_resource(conf_file, mode="a") as fp:
                fp.write(f'SECRET_KEY="{key}"\n')

    try:
        from sassutils.wsgi import SassMiddleware  # type: ignore
    except:
        pass
    else:
        app.wsgi_app = SassMiddleware(
            app.wsgi_app,
            {
                "nido_frontend": {
                    "sass_path": "resources/static/sass",
                    "css_path": "resources/static/css",
                    "wsgi_path": "/static/css",
                    "strip_extension": True,
                }
            },
        )

    db_engine = create_engine(
        app.config.get(
            "DATABASE_URL",
            "sqlite:///" + os.path.join(app.instance_path, "nido_db.sqlite3"),
        ),
        echo=app.config.get("LOG_SQL", app.debug),
    )
    # XXX: Is a scoped session really necessary?
    # See https://docs.sqlalchemy.org/en/20/orm/contextual.html
    app.Session = scoped_session(sessionmaker(bind=db_engine))

    @app.before_request
    def create_db_session():
        g.db_session = current_app.Session()

    @app.teardown_appcontext
    def end_db_session(_response):
        current_app.Session.remove()

    gql_schema = create_schema()
    gql_client = IntegratedGraphQLClient(gql_schema)

    @app.before_request
    def create_gql_client():
        g.gql_client = gql_client

    doc_signing_key = app.config.get("DOC_SIGNING_KEY", None)
    doc_signing_key_pass = app.config.get("DOC_SIGNING_KEY_PASS", None)
    doc_signing_cert = app.config.get("DOC_SIGNING_CERT", None)

    if doc_signing_key is None or doc_signing_cert is None:
        pass
    else:
        try:
            cms_signer = signers.SimpleSigner.load(
                doc_signing_key, doc_signing_cert, key_passphrase=doc_signing_key_pass
            )
        except:
            pass
        else:

            @app.before_request
            def create_cms_signer():
                g.cms_signer = cms_signer

    doc_signing_tsa_url = app.config.get("DOC_SIGNING_TSA_URL", None)

    if doc_signing_tsa_url:
        tsa_client = timestamps.HTTPTimeStamper(doc_signing_tsa_url)

        @app.before_request
        def create_tsa_client():
            g.tsa_client = tsa_client

    app.register_blueprint(admin_bp, url_prefix="/admin")

    app.register_blueprint(auth_bp)
    app.register_blueprint(billing_bp, url_prefix="/billing")
    app.register_blueprint(documents_bp, url_prefix="/documents")
    app.register_blueprint(household_bp, url_prefix="/my-household")
    app.register_blueprint(issues_bp, url_prefix="/report-issues")
    app.register_blueprint(rd_bp, url_prefix="/resident-directory")
    app.register_blueprint(signing_bp, url_prefix="/signatures")
    app.add_url_rule("/", endpoint="index", view_func=household_index)

    if app.debug:
        app.add_url_rule(
            "/api/graphql",
            view_func=GraphQLWithDB.as_view("graphql_view", schema=gql_schema),
        )

    return app
