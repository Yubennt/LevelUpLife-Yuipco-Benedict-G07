from .models import Level


def level_progress(user):
    """Everything the UI needs to draw a user's level and XP bar."""
    current = user.current_level
    nxt = Level.objects.filter(level_number=current.level_number + 1).first()
    if nxt is None:  # highest seeded level
        return {"level": current, "next": None, "xp_into": user.total_xp - current.xp_required,
                "xp_span": 0, "xp_remaining": 0, "percent": 100}
    span = nxt.xp_required - current.xp_required
    into = user.total_xp - current.xp_required
    return {"level": current, "next": nxt, "xp_into": into, "xp_span": span,
            "xp_remaining": nxt.xp_required - user.total_xp, "percent": into * 100 // span}
