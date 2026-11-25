def axes_username(request, credentials):
    """Count failed logins per account regardless of upper/lower case, so case tricks can't dodge the lockout."""
    value = (credentials or {}).get("username") or (credentials or {}).get("email") or ""
    return value.strip().lower()
