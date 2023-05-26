actor User {}

resource Group {
    permissions = ["query", "update", "delete"];
    roles = ["member", "manager"];
    relations = { managing_group: Group };

    "query" if "member";

    "query" if "manager";
    "update" if "manager";
    "delete" if "manager";

    "manager" if "member" on "managing_group";
}

has_role(user: User, "member", group: Group) if
    member in group.custom_members and
    member matches {id: user.id};

has_relation(parent: Group, "managing_group", child: Group) if
    child.managed_by.id = parent.id;

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
