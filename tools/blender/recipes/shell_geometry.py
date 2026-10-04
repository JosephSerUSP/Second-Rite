"""Shared dimensions for a closed three-sided interior ceiling junction."""
def ceiling_members(front, back, half_width, wall_thick, ceiling_z, ceiling_thick):
    depth = back - front
    if min(depth, half_width, wall_thick, ceiling_thick) <= 0:
        raise ValueError('Interior shell dimensions must be positive')
    return [
        ('ceiling', (depth + wall_thick, 2 * (half_width + wall_thick), ceiling_thick),
         ((front + back + wall_thick) / 2, 0, ceiling_z + ceiling_thick / 2)),
        ('ceiling_wall_plate_rear', (.12, 2 * half_width, .12),
         (back - .04, 0, ceiling_z - .06)),
        *[(f'ceiling_wall_plate_side_{i}', (depth, .12, .12),
           ((front + back) / 2, sign * (half_width - .04), ceiling_z - .06))
          for i, sign in enumerate((-1, 1))],
    ]
