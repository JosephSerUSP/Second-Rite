"""Solve the town camera when it is ROTATED, and compensate for the rotation.

THE CONTRACT IS TWO INVARIANTS, NOT A LENS.

  1. **1:1 pixel scale at the action plane.** One texel of the actor sprite
     renders as one native pixel. Today walker.png is 48px tall so the actor is
     48px; if the sprite is ever redrawn at a different size the RULE is
     unchanged and the number follows the art.
  2. **Base y = 128.** Where the actor's feet land before slopes or props move
     them.

Everything else - focal length, pitch, camera distance, eye height, principal
point - is free, and is chosen for how the picture looks. The older rule "do not
change the lens" fixed an implementation detail rather than the invariant, and
it forbids solutions that satisfy both constraints perfectly well.

That freedom is why there is a FAMILY of answers rather than one. Rotating the
camera is what makes vertical edges stop being parallel - no lens or principal
shift on a level camera can do it - but rotation alone breaks both invariants.
With four knobs (distance, height, shift, focal length) against two constraints,
two degrees of freedom remain, and the modes below are different choices within
that family:

  * TRANSLATE   - move the camera. Keeps the lens, holds at any angle, and picks
                  a genuinely new viewpoint.
  * SHIFT       - principal point only. UNDERDETERMINED: a shift changes framing,
                  not magnification, so scale drifts. Kept to show the drift.
  * SHIFT+FOV   - camera never moves; the lens absorbs the scale. Holds the
                  viewpoint exactly.
  * SHIFT+DOLLY - slide along the view axis, keeping the lens. Its eye descends
                  as the angle grows and goes below the floor past ~25 degrees.

Screen convention: native pixels, top-left origin, +y down.
"""

import math

WALKER_UNITS = 1.75                             # the actor's world height
# INVARIANT 1: the sprite renders 1:1, so its native pixel height IS the target.
# Read from the sheet rather than hard-coded, because the rule outlives the art.
def _actor_native_px(default=48):
    try:
        from PIL import Image
        import os
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "..", "projects", "hichaukitoden-game",
                         "assets", "character", "walker.png")
        with Image.open(p) as im:
            return im.size[1]           # 144x48 sheet = six 24x48 cells
    except Exception:
        return default


WALKER_PX = _actor_native_px()
PX_PER_UNIT = WALKER_PX / WALKER_UNITS          # scale at the action plane
DISTANCE = 18.666666666666668                   # the level-camera solution
FEET_Y = 128.0                                  # INVARIANT 2: base y
HEAD_Y = FEET_Y - WALKER_PX
# screen_offset_px = K * (camera_axis_ratio). K is the lens, in pixels, and is
# independent of render width because the horizontal FOV widens with it.
K = PX_PER_UNIT * DISTANCE                      # 512.0


def basis(theta):
    """forward / right / up for a camera pitched `theta` radians downward."""
    f = (math.cos(theta), 0.0, -math.sin(theta))
    r = (0.0, -1.0, 0.0)
    u = (math.sin(theta), 0.0, math.cos(theta))
    return f, r, u


def project_y(point_z, dist, height, theta, principal_y):
    """Native screen y of a point on the action plane at world height point_z."""
    f, _r, u = basis(theta)
    v = (dist, 0.0, point_z - height)
    z_c = v[0] * f[0] + v[2] * f[2]
    y_c = v[0] * u[0] + v[2] * u[2]
    return principal_y - K * (y_c / z_c)


def solve_translate(theta, principal_y):
    """Move the camera so feet land at 128 AND the Walker measures 48px.

    Damped Newton on (distance, height). Both residuals are screen pixels, so
    the solve is in the units the contract actually cares about.
    """
    d, h = DISTANCE * math.cos(theta), WALKER_UNITS / 2.0 + DISTANCE * math.sin(theta)
    for _ in range(200):
        r0 = project_y(0.0, d, h, theta, principal_y) - FEET_Y
        r1 = project_y(WALKER_UNITS, d, h, theta, principal_y) - HEAD_Y
        if abs(r0) < 1e-9 and abs(r1) < 1e-9:
            break
        e = 1e-5
        a = (project_y(0.0, d + e, h, theta, principal_y) - project_y(0.0, d, h, theta, principal_y)) / e
        b = (project_y(0.0, d, h + e, theta, principal_y) - project_y(0.0, d, h, theta, principal_y)) / e
        c = (project_y(WALKER_UNITS, d + e, h, theta, principal_y) - project_y(WALKER_UNITS, d, h, theta, principal_y)) / e
        dd = (project_y(WALKER_UNITS, d, h + e, theta, principal_y) - project_y(WALKER_UNITS, d, h, theta, principal_y)) / e
        det = a * dd - b * c
        if abs(det) < 1e-12:
            break
        d -= 0.6 * (dd * r0 - b * r1) / det
        h -= 0.6 * (-c * r0 + a * r1) / det
    return d, h


def solve_shift(theta, height=None, dist=None):
    """Leave the camera put, slide the principal point until the feet land.

    Returns (dist, height, principal_y, walker_px). `walker_px` will NOT be 48:
    a shift cannot restore scale, and how far it drifts is the whole difference
    between this mode and TRANSLATE.
    """
    d = DISTANCE if dist is None else dist
    h = 2.2604166666666665 if height is None else height
    # principal_y such that the feet land on FEET_Y
    f, _r, u = basis(theta)
    v = (d, 0.0, -h)
    z_c = v[0] * f[0] + v[2] * f[2]
    y_c = v[0] * u[0] + v[2] * u[2]
    p = FEET_Y + K * (y_c / z_c)
    px = project_y(0.0, d, h, theta, p) - project_y(WALKER_UNITS, d, h, theta, p)
    return d, h, p, px


def vertical_convergence(theta, dist, height, half_width_units=6.0):
    """How far from parallel a vertical edge becomes, in pixels.

    A vertical world line is sampled at the ground and one Walker up, off to the
    side of frame. Under a level camera the two samples share a screen x exactly;
    under a rotated one they do not, and the gap IS the effect being chased.
    """
    f, r, u = basis(theta)

    def sx(point_z):
        v = (dist, -half_width_units, point_z - height)
        z_c = v[0] * f[0] + v[2] * f[2]
        x_c = v[0] * r[0] + v[1] * r[1] + v[2] * r[2]
        return K * (x_c / z_c)

    return abs(sx(WALKER_UNITS * 3.0) - sx(0.0))



def _ratios(theta, dist, height):
    f, _r, u = basis(theta)
    out = []
    for pz in (0.0, WALKER_UNITS):
        v = (dist, 0.0, pz - height)
        z_c = v[0] * f[0] + v[2] * f[2]
        y_c = v[0] * u[0] + v[2] * u[2]
        out.append(y_c / z_c)
    return out


def solve_shift_fov(theta, dist=None, height=None):
    """Rotate in place; fix SCALE with the lens and POSITION with the shift.

    The camera never moves. Solving is closed form: the Walker's pixel height is
    K * (feet_ratio - head_ratio), so the lens constant K that makes it 48 falls
    straight out, and the principal point follows.

    This is the "zoom" answer as against TRANSLATE's "dolly". It holds the
    viewpoint exactly - the same rooflines, the same amount of ground - and pays
    for it by changing the strength of the perspective.
    """
    d = DISTANCE if dist is None else dist
    h = 2.2604166666666665 if height is None else height
    r0, r1 = _ratios(theta, d, h)
    k = WALKER_PX / (r1 - r0)   # screen_y = principal - K*ratio
    p = FEET_Y + k * r0
    return d, h, p, k


def solve_shift_dolly(theta, height=None):
    """Rotate in place; fix SCALE by dollying ALONG the view axis, position by shift.

    Unlike TRANSLATE this does not choose a new viewpoint freely - it slides the
    camera down its own line of sight, which is the one move that changes
    magnification without changing what the lens is pointed at.
    """
    h0 = 2.2604166666666665 if height is None else height
    f, _r, _u = basis(theta)
    t = 0.0
    for _ in range(200):
        d, h = DISTANCE - t * f[0], h0 - t * f[2]
        r0, r1 = _ratios(theta, d, h)
        px = K * (r1 - r0)
        if abs(px - WALKER_PX) < 1e-9:
            break
        e = 1e-5
        d2, h2 = DISTANCE - (t + e) * f[0], h0 - (t + e) * f[2]
        s0, s1 = _ratios(theta, d2, h2)
        deriv = (K * (s1 - s0) - px) / e
        if abs(deriv) < 1e-12:
            break
        t -= 0.6 * (px - WALKER_PX) / deriv
    d, h = DISTANCE - t * f[0], h0 - t * f[2]
    r0, _r1 = _ratios(theta, d, h)
    return d, h, FEET_Y + K * r0, t



def horizon_screen_y(theta, principal_y):
    """Where the horizon lands. A point at infinite horizontal distance."""
    return principal_y - K * math.tan(theta)


def solve_for_horizon(theta, want_horizon_y):
    """Pitch sets the LEAN; the principal point sets where the HORIZON sits;
    translating then restores both invariants.

    Three knobs against three targets, so it is determined. This is the member
    of the family that keeps the converging verticals AND puts sky and sea in
    frame - with the principal point centred, a 17.5 degree pitch throws the
    horizon 41 pixels above the top of the frame and no amount of lighting will
    bring it back.
    """
    principal = want_horizon_y + K * math.tan(theta)
    d, h = solve_translate(theta, principal)
    return d, h, principal



def solve_billboard(theta, want_horizon_y=66.0):
    """THE solve, for an actor drawn as a screen-space billboard.

    The world keystones - that is the whole point of pitching the camera - but
    the actor must NOT. A character is an axis-aligned rectangle that only
    scales with depth, never shears, leans or foreshortens. So it is not a plane
    in the scene: a plane would keystone with everything else. It is a sprite
    blitted at the projected position of its GROUND POINT.

    That changes the constraint. The earlier solve projected a head and a pair of
    feet and asked for 48 pixels between them, which silently compensated for a
    keystoning the actor is not allowed to have. The real constraints are:

      1:1 pixel scale  ->  the slant distance from the eye to the ground point
                           must be exactly DISTANCE, because pixels-per-world-
                           unit is K / slant, and 1.75 units must come to
                           WALKER_PX pixels.
      base y = 128     ->  that ground point projects to FEET_Y.
      horizon          ->  fixed by the principal point, independent of both.

    Three equations, three unknowns, and it solves in closed form.
    """
    principal = want_horizon_y + K * math.tan(theta)
    # y_c/z_c is fixed by where the feet must land; z_c is fixed by scale.
    z_c = WALKER_UNITS * K / WALKER_PX          # == DISTANCE
    y_c = z_c * (principal - FEET_Y) / K
    dist = z_c * math.cos(theta) + y_c * math.sin(theta)
    height = z_c * math.sin(theta) - y_c * math.cos(theta)
    return dist, height, principal


def billboard_check(theta, dist, height, principal):
    """Confirm the two invariants for a screen-space actor."""
    f, _r, u = basis(theta)
    v = (dist, 0.0, -height)
    z_c = v[0] * f[0] + v[2] * f[2]
    y_c = v[0] * u[0] + v[2] * u[2]
    return {
        "feetY": principal - K * (y_c / z_c),
        "spritePx": WALKER_UNITS * (K / z_c),
        "slant": z_c,
        "horizonY": horizon_screen_y(theta, principal),
    }


def project_ground(theta, dist, height, principal_y, lane_y, principal_x):
    """Screen position and sprite size for an actor standing at `lane_y`.

    This is what the ENGINE must do, and what a Blender preview must do in post.
    The sprite is never geometry in the pitched scene - it is blitted here, as
    an axis-aligned rectangle, so it can only scale.
    """
    f, r, u = basis(theta)
    v = (dist, lane_y, -height)
    z_c = v[0] * f[0] + v[2] * f[2]
    x_c = v[0] * r[0] + v[1] * r[1] + v[2] * r[2]
    y_c = v[0] * u[0] + v[2] * u[2]
    return (principal_x + K * (x_c / z_c),
            principal_y - K * (y_c / z_c),
            WALKER_UNITS * (K / z_c))


def describe(theta_deg, principal_y=120.0):
    t = math.radians(theta_deg)
    d, h = solve_translate(t, principal_y)
    sd, sh, sp, spx = solve_shift(t)
    fd, fh, fp, fk = solve_shift_fov(t)
    dd, dh, dp, dolly = solve_shift_dolly(t)
    import math as _m

    def px_at(dist, height, principal, k=K):
        r0, r1 = _ratios(t, dist, height)
        return k * (r1 - r0), principal - k * r0 + 0.0

    return {
        "pitchDeg": theta_deg,
        "translate": {"dist": d, "height": h, "principalY": principal_y,
                      "walkerPx": px_at(d, h, principal_y)[0],
                      "convergencePx": vertical_convergence(t, d, h),
                      "hFovDeg": 2 * _m.degrees(_m.atan((256 / 2.0) / K))},
        "shift": {"dist": sd, "height": sh, "principalY": sp, "walkerPx": spx,
                  "convergencePx": vertical_convergence(t, sd, sh),
                  "hFovDeg": 2 * _m.degrees(_m.atan((256 / 2.0) / K))},
        "shift_fov": {"dist": fd, "height": fh, "principalY": fp,
                      "walkerPx": px_at(fd, fh, fp, fk)[0], "K": fk,
                      "convergencePx": vertical_convergence(t, fd, fh),
                      "hFovDeg": 2 * _m.degrees(_m.atan((256 / 2.0) / fk))},
        "shift_dolly": {"dist": dd, "height": dh, "principalY": dp, "dolly": dolly,
                        "walkerPx": px_at(dd, dh, dp)[0],
                        "convergencePx": vertical_convergence(t, dd, dh),
                        "hFovDeg": 2 * _m.degrees(_m.atan((256 / 2.0) / K))},
    }


if __name__ == "__main__":
    hdr = ("pitch", "mode", "dist", "eye", "hFOV", "WalkerPx", "converge")
    print("%-6s %-13s %7s %7s %7s %9s %9s" % hdr)
    for deg in (0.0, 10.0, 17.5, 25.0):
        r = describe(deg)
        for m in ("translate", "shift", "shift_fov", "shift_dolly"):
            v = r[m]
            print("%-6.1f %-13s %7.2f %7.3f %7.2f %9.2f %9.2f"
                  % (deg, m, v["dist"], v["height"], v["hFovDeg"],
                     v["walkerPx"], v["convergencePx"]))
        print()
