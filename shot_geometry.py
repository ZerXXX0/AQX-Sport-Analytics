"""Simulator geometry in feet, matching the Shot Explorer court."""
import math


def shot_value_at(x, y):
    """The line counts as two points; inputs represent the shooter's location."""
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError('Shot coordinates must be finite.')
    if not (-25 < x < 25 and -5.25 < y < 41.75):
        raise ValueError('Choose a location inside the displayed half court.')
    corner_end = math.sqrt(23.75**2 - 22**2)
    boundary = 22 if y <= corner_end else 23.75
    position = abs(x) if y <= corner_end else math.hypot(x, y)
    return 3 if position > boundary and not math.isclose(position, boundary, abs_tol=1e-9) else 2
