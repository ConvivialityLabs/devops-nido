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

import os
from typing import Any

from flask import Flask, Request, Response, g, render_template, session
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from strawberry.flask.views import GraphQLView

from nido_backend.gql_schema import SchemaContext, create_schema

from .authentication import bp as auth_bp
from .authentication import login_required
from .household import bp as household_bp
from .household import index as household_index
from .resident_directory import bp as rd_bp


class GraphQLWithDB(GraphQLView):
    def get_context(self, request: Request, response: Response) -> Any:
        user_id = session.get("user_id")
        community_id = session.get("community_id")
        db_session = g.db_session

        return SchemaContext(db_session, user_id, community_id)


def create_app(testing_config=None):
    app = Flask(
        "nido_frontend",
        instance_path=os.environ.get("NIDO_VARDIR"),
        instance_relative_config=True,
        template_folder="resources/html_templates",
    )

    if testing_config:
        app.config.from_mapping(testing_config)
    else:
        conf_file = os.environ.get("NIDO_CONFIG_FILE") or "nido.cfg"
        app.config.from_pyfile(conf_file)

    db_engine = create_engine(
        app.config["DATABASE_URL"],
        echo=app.config.get("LOG_SQL", app.debug),
    )
    # XXX: Is a scoped session really necessary?
    # See https://docs.sqlalchemy.org/en/20/orm/contextual.html
    Session = scoped_session(sessionmaker(bind=db_engine))

    @app.before_request
    def create_db_session():
        g.db_session = Session()

    @app.teardown_appcontext
    def end_db_session(_response):
        Session.remove()

    app.register_blueprint(auth_bp)
    app.register_blueprint(household_bp, url_prefix="/my-household")
    app.register_blueprint(rd_bp, url_prefix="/resident-directory")
    app.add_url_rule("/", endpoint="index", view_func=household_index)

    if app.debug:
        app.add_url_rule(
            "/api/graphql",
            view_func=GraphQLWithDB.as_view("graphql_view", schema=create_schema()),
        )

    return app
