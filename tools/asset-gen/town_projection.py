"""The plate camera, read from the authored .blend, so guides are projected not drawn.

The camera that matters for a plate is the one that rendered it. A plate's
perspective is paint: the runtime blits the image and never reprojects it, so the
map's own camera record cannot be the authority -- and taking it as one is what
produced flat guides, because every plate screen declares ``pitchDegrees: 0``.

These numbers come out of ``st_maria_praca_modelled.blend``, whose render
resolution is 906x240, exactly the Praca plate:

    location  (-10.866667, 11.8495, 2.260417)
    rotation  (107.5, 0, -90) degrees -- 17.5 down from level
    lens      20.344372 mm on a 36 mm sensor, horizontal fit
    shift_y   -0.247574

Two of those are checked rather than trusted. Projecting the lane centre gives
column 452.98 against the package's declared centerX of 453, and a 1.75 m actor's
feet land on row 128, which is ``make_town_camera.py``'s authoring default
--feet-y. Both fall out of the camera; neither is fitted to.

The floor is z=0 here, which is a RELABELLING of the blend's old -1.5, not a
move. Everything that was measured against the floor moves with it, the eye
included; the constants below are therefore heights above the floor rather than
absolute world heights. Rebasing the ground while leaving the eye at its old
absolute height lifted every screen by about 41 rows, which is what "the player
is drawn much closer to the upper end of the screen" was.

The plate packages stay as authored, and their screenY of 136 is THE GROUND ROW,
not the top of the sprite: viewport_3d calls it "the authored foot line" and
draws the figure upward from it. Reading it as a sprite top and adding the 48-row
height produced a ground at 184, which is what made this camera look 50 rows out
and prompted a "correction" that lifted every screen. The camera lands the ground
on row 128 against the screens' 136.

Only the vertical framing is fixed. A plate is a horizontally scrolling strip, so
a wider screen is the same camera seeing more world sideways: the vertical half
extent stays 0.234375 (the contract lens over a 240-row target) and the
horizontal extent follows the width. The principal point's shift is likewise a
vertical fact, so it is carried in PIXELS rather than as Blender's width-relative
fraction, which would otherwise drift the horizon as the plate got wider.
"""

from __future__ import annotations

import math

# From the blend. Vertical half-extent, not horizontal: see the note above.
TAN_HALF_Y = 0.234375
PRINCIPAL_SHIFT_PX = -0.247574 * 906.0       # -224.30 rows
PITCH_DEGREES = 17.5                         # down from level
# Height of the eye ABOVE THE FLOOR. The blend's floor is already z=0 -- that is
# the fix that was made in it -- so this is the blend's own eye height unchanged.
EYE_HEIGHT = 2.260417
HORIZONTAL_DISTANCE = 18.666667
PLATE_ROWS = 240
ACTOR_HEIGHT = 1.75                          # metres; the contract's Walker


class PlateCamera:
    """The authored plate camera, for one screen's lane and plate width."""

    def __init__(self, lane_depth_x, lane_centre_y, plate_size,
                 ground_z=0.0, centre_x=None):
        self.plate_w, self.plate_h = plate_size
        self.ground_z = float(ground_z)
        self.centre_x = (self.plate_w * 0.5) if centre_x is None else float(centre_x)

        self.lane_depth_x = float(lane_depth_x)
        self.lane_centre_y = float(lane_centre_y)
        # The eye rides on the floor, not on absolute zero.
        self.eye = (self.lane_depth_x - HORIZONTAL_DISTANCE,
                    self.lane_centre_y, self.ground_z + EYE_HEIGHT)
        self._basis = self._rotation(math.radians(90.0 + PITCH_DEGREES), 0.0,
                                     math.radians(-90.0))

        self.tan_half_y = TAN_HALF_Y
        self.tan_half_x = TAN_HALF_Y * self.plate_w / self.plate_h
        self.shift_rows = PRINCIPAL_SHIFT_PX * (self.plate_h / PLATE_ROWS)

    @staticmethod
    def _rotation(rx, ry, rz):
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)
        rot_x = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
        rot_y = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
        rot_z = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]

        def mul(a, b):
            return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
                    for i in range(3)]

        return mul(rot_z, mul(rot_y, rot_x))

    def project_world(self, point):
        """A world point (x, y, z) to plate pixels, or None if behind the eye."""
        delta = [point[i] - self.eye[i] for i in range(3)]
        cam = [sum(self._basis[k][i] * delta[k] for k in range(3)) for i in range(3)]
        x, y, z = cam
        if -z <= 1e-9:
            return None
        half = self.plate_w * 0.5
        column = self.centre_x + (x / -z) / self.tan_half_x * half
        row = (self.plate_h * 0.5
               - (y / -z) / self.tan_half_x * half
               + self.shift_rows)
        return column, row

    def project(self, lane_y, height_above_ground=0.0, depth_behind=0.0):
        """Along the street, up from the ground, and back from the lane."""
        return self.project_world((self.lane_depth_x + depth_behind, lane_y,
                                   self.ground_z + height_above_ground))

    def horizon_row(self):
        """Where the ground plane vanishes: the limit of the depth divide."""
        far = self.project(self.lane_centre_y, 0.0, 1.0e6)
        return far[1] if far else None


def self_check(camera, projection, tolerance=8.0):
    """Check the camera against the SHIPPED screens, which are the ones that work.

    The screen's ground row is ``playerProjection.screenY`` on its own -- the
    authored foot line. Adding the sprite's 48-row height to it, as if screenY
    were the top of the figure, put the expected ground at 184 and made this
    camera look 50 rows wrong.

    The residual is returned rather than hidden. It runs about 8 rows, which is
    real and is most likely the lens: the packages imply 34.6 pixels per world
    unit along the lane where this camera gives 27.43, and that gap is not
    reconciled here.
    """
    column, ground = camera.project(camera.lane_centre_y, 0.0)
    want_ground = float(projection["screenY"])
    ok = (abs(column - camera.centre_x) < 1.0
          and abs(ground - want_ground) < tolerance)
    return ok, column, ground, ground - want_ground
