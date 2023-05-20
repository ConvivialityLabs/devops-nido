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
    {id: user.id} in group.custom_members;

has_relation(parent: Group, "managing_group", child: Group) if
    child.managed_by.id = parent.id;

resource ContactMethod {
    permissions = ["read", "delete"];
    relations = { owner: User };

    "read" if "owner";
    "delete" if "owner";
}

has_relation(user: User, "owner", contact_method: ContactMethod) if
    contact_method.user.id = user.id;

allow(actor, action, resource) if
    has_permission(actor, action, resource);
