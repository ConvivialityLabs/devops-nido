#  Nido billing.py
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

from decimal import Decimal
from functools import reduce

from flask import Blueprint, g, render_template

from .authentication import login_required
from .main_menu import get_main_menu


def format_money(amount: int) -> str:
    return f"${Decimal('.01') * amount}"


bp = Blueprint("billing", __name__)


@bp.route("/")
@login_required
def index():
    gql_query = """
query Billing {
  activeUser {
    isAdmin
    residences {
      billingCharges(filter: {outstandingOnly: true}) {
        remainingBalance
      }
    }
  }
}"""
    gql_result = g.gql_client.execute_query(gql_query)
    residences = gql_result.data.active_user.residences
    total_due = reduce(
        lambda x, y: x + y,
        [
            charge.remaining_balance
            for residence in residences
            for charge in residence.billing_charges
        ],
        0,
    )
    main_menu_links = get_main_menu(gql_result.data.active_user.is_admin)
    return render_template(
        "billing.html",
        main_menu_links=main_menu_links,
        total_due=format_money(total_due),
    )
