def xp_needed_for_level(level: int) -> int:
    """
    XP required to go from level L -> L+1.
    Tuned for steady early game with ~quadratic growth.
    Feel free to tweak coefficients to taste.
    """
    level = max(1, int(level))
    base = 100           # floor so level 1 isn't trivial
    linear = 30 * level  # keeps early levels snappy
    quad = 10 * level * level  # ramps mid/late game
    return base + linear + quad

def cumulative_xp_to_level(level: int) -> int:
    """Total XP required to reach the *start* of level L (sum over previous levels)."""
    return sum(xp_needed_for_level(l) for l in range(1, max(1, level)))

def xp_progress(level: int, xp_value: int, *, xp_is_total: bool) -> dict:
    """
    Returns: dict(xp_in_level, xp_to_next, pct, text)
    - If xp_is_total=True, xp_value is lifetime XP.
    - If xp_is_total=False, xp_value is XP within the current level.
    """
    level = max(1, int(level))
    need = xp_needed_for_level(level)

    if xp_is_total:
        spent = int(xp_value) - cumulative_xp_to_level(level)
    else:
        spent = int(xp_value)

    # Clamp to [0, need]
    spent = max(0, min(need, spent))
    pct = int(round((spent * 100.0) / need)) if need else 0
    return {
        "xp_in_level": spent,
        "xp_to_next": need,
        "pct": pct,
        "text": f"XP {spent} / {need}",
    }
