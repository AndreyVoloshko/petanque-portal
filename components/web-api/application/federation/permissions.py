CREATE_TOURNAMENT_ALLOWLIST = {
    (1, "andreyvoloshko"),
    (65, "andriikamenev"),
    (84, "olenakolodiy"),
    (1084, "vsevolodprahnіtskij"),
    (1839, "admin"),
}


def can_create_tournament(user):
    if not getattr(user, "is_authenticated", False):
        return False

    if not getattr(user, "is_active", False):
        return False

    if not getattr(user, "is_superuser", False):
        return False

    return (getattr(user, "id", None), getattr(user, "username", None)) in CREATE_TOURNAMENT_ALLOWLIST
