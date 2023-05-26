actor User {}

resource Group {
    permissions = ["query", "create", "update", "delete"];
    roles = ["member", "manager"];

    "query" if "member";

    "query" if "manager";
    "update" if "manager";
    "delete" if "manager";
}

has_permission(user: User, "create", _group: Group) if
    group in user.groups and
    group.right != nil and
    group.right.permits(Permissions.CREATE_GROUPS);

has_role(user: User, "member", group: Group) if
    member in group.custom_members and
    member matches {id: user.id};

has_role(user: User, "manager", group: Group) if
    member in group.managed_by.custom_members and
    member matches {id: user.id};

resource Right {
    permissions = ["delegate"];
    roles = ["possessor", "delegator"];

    "delegate" if "delegator";

}

has_role(user: User, "possessor", right: Right) if
    group in user.groups and
    group matches {right_id: right.id};

has_role(user: User, "delegator", right: Right) if
    group in user.groups and
    group matches {right_id: right.parent_right_id} and
    right.parent_right.permits(Permissions.CAN_DELEGATE) and
    right.parent_right.permits(right.permissions);


resource ContactMethod {
    permissions = ["query", "delete"];
    relations = { owner: User };

    "query" if "owner";
    "delete" if "owner";
}

has_relation(user: User, "owner", contact_method: ContactMethod) if
    contact_method.user.id = user.id;

allow(actor, action, resource) if
    has_permission(actor, action, resource);
