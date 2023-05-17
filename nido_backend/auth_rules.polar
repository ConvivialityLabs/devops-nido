actor User {}

resource Group {
    permissions = ["update", "delete"];
    roles = ["member", "manager"];
    relations = { managing_group: Group };

    "update" if "manager";
    "delete" if "manager";

    "manager" if "member" on "managing_group";
}

has_role(user: User, "member", group: Group) if
    user in group.custom_members;

has_relation(parent: Group, "managing_group", child: Group) if
    child.managed_by = parent;

allow(actor, action, resource) if
    has_permission(actor, action, resource);
