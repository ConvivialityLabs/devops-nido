#  Nido main_menu.py
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

from flask import url_for


@dataclasses.dataclass
class MenuLink:
    name: str
    href: str


def get_main_menu():
    menu_list = []
    menu_list.append(MenuLink("My Household", url_for("household.index")))
    menu_list.append(MenuLink("Billing", url_for("billing.index")))
    menu_list.append(MenuLink("Resident Directory", url_for("resident_dir.index")))
    menu_list.append(MenuLink("Documents", url_for("documents.index")))
    menu_list.append(MenuLink("Logout", url_for("authentication.logout")))
    return menu_list
