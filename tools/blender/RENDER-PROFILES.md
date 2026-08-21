# Blender render profiles

Second Gate Blender authoring should not invent render cost per script. Use the
shared profiles instead:

```python
import second_gate_render

second_gate_render.apply(scene, "clay")
second_gate_render.apply(scene, "cycles-draft")
second_gate_render.apply(scene, "cycles-lookdev")
second_gate_render.apply(scene, "cycles-candidate")

# Selected scenes only:
second_gate_render.apply(scene, "beauty-selected", allow_expensive=True)
```

`thestra_render.py` owns the generic profile mechanism. `second_gate_render.py`
owns the project-specific native presentation facts.

## Presentation contract

- native review target: **426x240**;
- base projection context: **256x144**;
- Walker sheet: **144x48**, six **24x48** cells;
- reference Walker: **1.75 world units -> 48 native pixels** tall;
- reference pixel density: **27.428571 px/world unit**;
- reference pixel size: **0.0364583 world units/pixel**;
- a 24 px-wide reference billboard at the same scale is **0.875 world units** wide;
- actor filtering stays **nearest** with a hard alpha/chroma boundary;
- environment beauty is **antialiased** and may be rendered above native resolution before downsampling;
- the native 426x240 result is always the composition authority.

These are Second Gate authoring defaults, not universal Thestra runtime policy.

## Cost ladder

| Profile | Engine | Output | Samples | Denoise | Intended use |
| --- | --- | ---: | ---: | --- | --- |
| `clay` | Eevee | 426x240 | - | - | massing/composition |
| `cycles-draft` | Cycles | 426x240 | 4 | OIDN when available | very cheap lighting/material check |
| `cycles-lookdev` | Cycles | 426x240 | 8 | OIDN when available | default textured lookdev |
| `cycles-candidate` | Cycles | 426x240 | 16 | OIDN when available | candidate-quality review |
| `beauty-selected` | Cycles | 852x480 | 16 | OIDN when available | selected-only environment beauty source |

`beauty-selected` refuses to apply unless the caller explicitly passes
`allow_expensive=True`. This is a workflow guard: a gray box should not quietly
turn into a long Cycles job.

High sample counts are not a quality ladder. At this target, low-spp Cycles +
denoising + final downsampling can be both faster and aesthetically useful for
the compressed pre-rendered look. Increase cost only when a visible defect in a
selected scene justifies it.

## Mixed sampling

Do not supersample the Walker together with the environment and then blur it
back down. The intended mixed presentation is:

```text
environment beauty
    -> antialiased / optionally 2x
    -> denoise
    -> high-quality downsample
    -> 426x240

Walker / pixel actors
    -> native 24x48 cells
    -> nearest
    -> hard alpha
    -> composed/rendered at native authority
```

The environment beauty/mask boundary remains a separate renderer concern; this
module only standardizes authoring renders.

## Self-check

Run without Blender:

```text
python tools/blender/check_second_gate_render.py
```

It validates the profile table and the 1:1 Walker reference math without
performing any expensive render.
