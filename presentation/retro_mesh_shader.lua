-- Shared retro mesh shader core for 3D world and item rendering.
-- Provides GLSL source composition for vertex snapping, affine UV mapping,
-- ordered dithering, color quantization, and surface lighting.

local retro_mesh_shader = {}

-- Material overlay passes.
--
-- The retro shader cannot compute specular, reflection or refraction (SPEC
-- 1.25), so material identity beyond a flat colour comes from layering sampled
-- images with fixed blend operations -- the way PS1-era hardware did it, where
-- semi-transparency was four fixed modes rather than a lighting model.
--
-- Passes are evaluated in the fragment shader rather than as extra draw calls.
-- That is not an approximation of multi-pass rendering, it is exact: both
-- operands are present in the same fragment, so subtract/multiply/screen
-- compute without a framebuffer read, and no sorting or depth-write change is
-- needed. A pass blending against *other* geometry would need real draws, and
-- that is the transparency work SPEC 1.25 scopes out.
--
-- The numeric ids are the shader's enum. `obj_model` validates authored names
-- against this table, so a typo fails at load instead of rendering nothing.
retro_mesh_shader.BLEND_OPS = {
    add = 0,       -- base + layer. PS1 mode B+F: sheen, glow, gem sparkle.
    subtract = 1,  -- base - layer. PS1 mode B-F: soot, tarnish, shadowing.
    multiply = 2,  -- base * layer: grime, staining, printed detail.
    screen = 3,    -- 1-(1-base)(1-layer): frost, bloom, dusting.
    mix = 4,       -- lerp toward layer: a plain overlay decal.
}

-- Where a pass takes its texture coordinates.
retro_mesh_shader.UV_SOURCES = {
    uv = 0,      -- the model's authored UVs, like the albedo
    sphere = 1,  -- sphere-mapped from the screen-space normal (matcap)
}

-- Two overlay passes on top of the base. This is a deliberate, stated bound:
-- each slot costs a sampler and a uniform set per group, and every material
-- proposed so far (sheen, sheen + grime) fits. Authoring more fails loudly
-- rather than silently dropping the extras.
retro_mesh_shader.MAX_PASSES = 2

-- Second Rite's canonical 3D clip/NDC convention is Y-up: +1 is the top edge
-- and -1 is the bottom edge. UI/layout and pixel coordinates stay ordinary
-- Y-down. These helpers are prepended to both generated shaders because the
-- conversions belong to vertex projection, not to the pixel/dither core.
local clipSpaceShaderSource = [[
    float screenYToCanonicalClipY(float screenY, float targetHeight)
    {
        return 1.0 - (2.0 * screenY / targetHeight);
    }

    float canonicalClipYToScreenY(float clipY, float targetHeight)
    {
        return (1.0 - clipY) * targetHeight * 0.5;
    }

    // Temporary production-runtime boundary. LÖVE 11.5 expects the custom
    // vertex-shader clip Y that Second Rite historically supplied, while LÖVE
    // 12 standardizes custom shader output on canonical Y-up clip space. The
    // renderer itself stays Y-up; the eventual LÖVE 12 migration deletes this
    // handoff rather than teaching engine math about a second convention.
    float love11ClipY(float canonicalClipY)
    {
        return -canonicalClipY;
    }

    // Vertex snapping: the PS1-era wobble. Positions are quantized to a pixel
    // grid in screen space, then converted back to clip space.
    //
    // `origin` is the composition origin the grid is anchored to. The world
    // renderer composites into a sub-rect and must anchor there or the grid
    // crawls as the viewport moves; the item turntable owns its whole canvas
    // and passes zero. That is the *only* difference between the two call
    // sites, which is why this is one function and not two.
    vec2 snapToPixelGrid(vec2 ndc, vec2 targetSize, float snapPixels, vec2 origin)
    {
        if (snapPixels <= 0.0) {
            return ndc;
        }
        float pixelX = (ndc.x + 1.0) * targetSize.x * 0.5;
        float pixelY = canonicalClipYToScreenY(ndc.y, targetSize.y);
        pixelX = floor((pixelX - origin.x) / snapPixels + 0.5) * snapPixels + origin.x;
        pixelY = floor((pixelY - origin.y) / snapPixels + 0.5) * snapPixels + origin.y;
        return vec2(
            pixelX * 2.0 / targetSize.x - 1.0,
            screenYToCanonicalClipY(pixelY, targetSize.y)
        );
    }
]]

local sharedShaderSource = [[
    float orderedDither(vec2 position)
    {
        vec2 cell = mod(floor(position), 4.0);
        float x = cell.x;
        float y = cell.y;
        float row0 = (x < 1.0) ? 0.0 : ((x < 2.0) ? 8.0 : ((x < 3.0) ? 2.0 : 10.0));
        float row1 = (x < 1.0) ? 12.0 : ((x < 2.0) ? 4.0 : ((x < 3.0) ? 14.0 : 6.0));
        float row2 = (x < 1.0) ? 3.0 : ((x < 2.0) ? 11.0 : ((x < 3.0) ? 1.0 : 9.0));
        float row3 = (x < 1.0) ? 15.0 : ((x < 2.0) ? 7.0 : ((x < 3.0) ? 13.0 : 5.0));
        return ((y < 1.0) ? row0 : ((y < 2.0) ? row1 : ((y < 3.0) ? row2 : row3))) / 16.0;
    }

    // Colour quantization with an ordered-dither threshold: the other half of
    // the PS1-era look. `screenPosition` is already relative to the caller's
    // composition origin, for the same reason the vertex grid is anchored --
    // an unanchored dither pattern crawls under a moving viewport.
    vec3 quantizeWithDither(vec3 rgb, vec2 screenPosition, float levels)
    {
        if (levels <= 1.0) {
            return rgb;
        }
        float threshold = orderedDither(screenPosition) - 0.5;
        return floor(clamp(rgb + threshold / levels, 0.0, 1.0) * levels + 0.5) / levels;
    }
]]

function retro_mesh_shader.sharedSource()
    return sharedShaderSource
end

function retro_mesh_shader.clipSpaceSource()
    return clipSpaceShaderSource
end

function retro_mesh_shader.buildWorldShader()
    return clipSpaceShaderSource .. [[
    #ifdef VERTEX
    varying vec2 worldUV;
    varying float affineScale;
    varying vec4 worldColor;
    varying float fogVisibility;
    varying float cameraDepth;
    attribute float WorldHeight;
    attribute float FogVisibility;
    attribute vec3 SurfaceLight;
    uniform vec3 cameraPosition;
    uniform vec2 cameraForward;
    uniform vec2 cameraRight;
    uniform float cameraPitch;
    uniform float fovHalfX;
    uniform float fovHalfY;
    uniform float nearPlane;
    uniform float farPlane;
    uniform float baseViewportWidth;
    uniform float baseViewportHeight;
    uniform float targetWidth;
    uniform float targetHeight;
    uniform vec2 compositionOrigin;
    uniform float viewportCenterX;
    uniform float viewportCenterY;
    uniform float affineTextures;
    uniform float vertexSnapPixels;
    uniform float fogStart;
    uniform float fogDistance;
    uniform float fogSharpness;
    uniform float fogMinFactor;
    uniform float fogBands;
    uniform vec3 playerLightColor;
    uniform float playerLightRadius;
    uniform float playerLightFalloff;

    vec4 position(mat4 transform_projection, vec4 vertex_position)
    {
        vec3 relative = vec3(VertexPosition.xy, WorldHeight) - cameraPosition;
        float depth = dot(relative.xy, cameraForward);
        float horizontal = dot(relative.xy, cameraRight);
        float vertical = relative.z;

        if (cameraPitch != 0.0) {
            float cosP = cos(cameraPitch);
            float sinP = sin(cameraPitch);
            float pitchedDepth = depth * cosP - vertical * sinP;
            float pitchedVertical = vertical * cosP + depth * sinP;
            depth = pitchedDepth;
            vertical = pitchedVertical;
        }
        cameraDepth = depth;

        float safeDepth = depth;
        worldUV = mix(VertexTexCoord.xy, VertexTexCoord.xy * safeDepth, affineTextures);
        affineScale = mix(1.0, safeDepth, affineTextures);
        vec3 dynamicLight = SurfaceLight;
        if (playerLightRadius > 0.0) {
            float playerDistance = length(relative.xy);
            if (playerDistance < playerLightRadius) {
                float strength = pow(1.0 - playerDistance / playerLightRadius, playerLightFalloff);
                dynamicLight = min(vec3(1.0), dynamicLight + playerLightColor * strength);
            }
        }
        worldColor = vec4(dynamicLight, 1.0);
        float safeFogDistance = max(fogDistance, 0.001);
        float normalizedFog = clamp((max(0.05, depth) - fogStart) / safeFogDistance, 0.0, 1.0);
        if (fogSharpness != 1.0) normalizedFog = pow(normalizedFog, fogSharpness);
        fogVisibility = 1.0 - normalizedFog * (1.0 - fogMinFactor);
        if (fogBands > 1.0) {
            fogVisibility = floor(fogVisibility * fogBands + 0.5) / fogBands;
        }
        float ndcDepth = (farPlane + nearPlane) / (farPlane - nearPlane)
            - (2.0 * farPlane * nearPlane)
                / ((farPlane - nearPlane) * safeDepth);
        float viewportCenter = (2.0 * viewportCenterX / targetWidth) - 1.0;
        float viewportCenterClipY = screenYToCanonicalClipY(viewportCenterY, targetHeight);
        float ndcX = viewportCenter
            + horizontal / (fovHalfX * safeDepth) * (baseViewportWidth / targetWidth);
        float ndcY = viewportCenterClipY
            + vertical / (fovHalfY * safeDepth) * (baseViewportHeight / targetHeight);
        vec2 snapped = snapToPixelGrid(
            vec2(ndcX, ndcY), vec2(targetWidth, targetHeight),
            vertexSnapPixels, compositionOrigin
        );
        ndcX = snapped.x;
        ndcY = snapped.y;
        return vec4(ndcX * safeDepth, love11ClipY(ndcY) * safeDepth, ndcDepth * safeDepth, safeDepth);
    }
    #endif

    #ifdef PIXEL
    varying vec2 worldUV;
    varying float affineScale;
    varying vec4 worldColor;
    varying float fogVisibility;
    varying float cameraDepth;
    uniform vec3 fogColor;
    uniform float ditherLevels;
    uniform vec2 compositionOrigin;
    uniform float roomBakePass;
    uniform float roomBakeFar;
    // Emission. `glowMap` is sampled at the SAME uv as the albedo, so it must
    // be the albedo's exact parallel -- the atlas for atlas-mapped faces, the
    // matching composite bake for composited walls. `glowStrength` is 0 when
    // no map is bound, which is what keeps the 1x1 fallback free.
    uniform Image glowMap;
    uniform float glowStrength;

]] .. sharedShaderSource .. [[

    vec4 effect(vec4 color, Image texture, vec2 texture_coords, vec2 screen_coords)
    {
        vec2 uv = worldUV / affineScale;
        vec4 texel = Texel(texture, uv);
        if (texel.a < 0.01) discard;
        // Asset-generation guides use the real world geometry and camera but
        // bypass presentation lighting. Normal gameplay always sends zero.
        if (roomBakePass > 1.5) return texel;
        if (roomBakePass > 0.5) {
            float depth01 = clamp(cameraDepth / max(roomBakeFar, 0.001), 0.0, 1.0);
            return vec4(depth01, depth01, depth01, 1.0);
        }
        vec3 lit = texel.rgb * color.rgb * worldColor.rgb;
        // A glowing texel ignores the light reaching it and resists fog. It
        // still honours `color` (the per-draw tint) -- glow opts out of being
        // lit, not out of being tinted -- and it never exceeds its own albedo,
        // so a glow mask can only ever restore a texel to full brightness.
        float glow = 0.0;
        if (glowStrength > 0.0) {
            glow = clamp(Texel(glowMap, uv).r * glowStrength, 0.0, 1.0);
            lit = mix(lit, texel.rgb * color.rgb, glow);
        }
        vec3 fogged = mix(fogColor, lit, max(fogVisibility, glow));
        fogged = quantizeWithDither(fogged, screen_coords - compositionOrigin, ditherLevels);
        return vec4(fogged, texel.a * color.a);
    }
    #endif
]]
end

function retro_mesh_shader.buildItemShader()
    return clipSpaceShaderSource .. [[
    #ifdef VERTEX
    attribute vec3 VertexNormal;

    varying vec2 worldUV;
    varying float affineScale;
    varying vec4 worldColor;
    varying vec2 sheenUV;

    uniform vec3 modelCenter;
    uniform float modelTilt;
    uniform float modelAngle;
    uniform float halfWidth;
    uniform float halfHeight;
    uniform float vertexSnapPixels;
    uniform float targetWidth;
    uniform float targetHeight;
    uniform vec3 lightDir;
    uniform vec3 materialColor;

    vec4 position(mat4 transform_projection, vec4 vertex_position)
    {
        vec3 pos = VertexPosition.xyz - modelCenter;
        vec3 norm = VertexNormal.xyz;

        float cosT = cos(modelTilt);
        float sinT = sin(modelTilt);

        // 1. local-Y tilt
        float tiltX = pos.x * cosT + pos.z * sinT;
        float tiltY = pos.y;
        float tiltZ = -pos.x * sinT + pos.z * cosT;

        float tiltNormX = norm.x * cosT + norm.z * sinT;
        float tiltNormY = norm.y;
        float tiltNormZ = -norm.x * sinT + norm.z * cosT;

        // 2. Z-axis turntable yaw
        float cosA = cos(modelAngle);
        float sinA = sin(modelAngle);

        float rotX = tiltX * cosA - tiltY * sinA;
        float rotY = tiltX * sinA + tiltY * cosA;
        float rotZ = tiltZ;

        float normX = tiltNormX * cosA - tiltNormY * sinA;
        float normY = tiltNormX * sinA + tiltNormY * cosA;
        float normZ = tiltNormZ;

        vec3 N = vec3(normX, normY, normZ);
        float nLen = length(N);
        if (nLen > 0.0) {
            N = N / nLen;
        }

        // Sphere-map ("matcap") coordinates from the rotated normal. This
        // projection sends rotX to screen X and rotZ to screen Y, with rotY
        // as depth -- so the screen-facing pair is (N.x, N.z), NOT the usual
        // (N.x, N.y). The v term is flipped because texture space is Y-down
        // while clip space here is canonical Y-up, matching the `1 - v` the
        // OBJ loader applies to authored UVs.
        sheenUV = vec2(N.x * 0.5 + 0.5, 0.5 - N.z * 0.5);

        float NdotL = max(0.0, dot(N, lightDir));
        float ambient = 0.35;
        float lightIntensity = ambient + (1.0 - ambient) * NdotL;

        worldColor = vec4(VertexColor.rgb * materialColor * lightIntensity, VertexColor.a);

        float ndcX = rotX / halfWidth;
        float ndcY = rotZ / halfHeight;

        // The turntable owns its whole canvas, so its grid anchors at zero.
        vec2 snapped = snapToPixelGrid(
            vec2(ndcX, ndcY), vec2(targetWidth, targetHeight),
            vertexSnapPixels, vec2(0.0)
        );
        ndcX = snapped.x;
        ndcY = snapped.y;

        float depthScale = max(halfWidth, halfHeight) * 4.0;
        float ndcZ = clamp(rotY / depthScale, -0.99, 0.99);

        worldUV = VertexTexCoord.xy;
        affineScale = 1.0;

        return vec4(ndcX, love11ClipY(ndcY), ndcZ, 1.0);
    }
    #endif

    #ifdef PIXEL
    varying vec2 worldUV;
    varying float affineScale;
    varying vec4 worldColor;
    varying vec2 sheenUV;

    uniform float ditherLevels;
    uniform float hasTexture;

    // Overlay passes. Slots are fixed rather than an array because sampler
    // arrays are not reliably indexable across the GLSL versions LOVE targets.
    // `passCount` is 0 when a material declares none, which keeps the 1x1
    // fallback samplers free.
    uniform float passCount;
    uniform Image passMap0;
    uniform float passBlend0;
    uniform float passStrength0;
    uniform float passUvSource0;
    uniform Image passMap1;
    uniform float passBlend1;
    uniform float passStrength1;
    uniform float passUvSource1;

    // Blend ids must match retro_mesh_shader.BLEND_OPS. Compared as floats
    // rather than ints: integer uniforms are the flakier path across drivers,
    // and these are a handful of exact small values.
    vec3 applyPass(vec3 base, vec4 layer, float op, float strength)
    {
        vec3 c = layer.rgb;
        float a = clamp(layer.a * strength, 0.0, 1.0);
        if (op < 0.5) {
            return min(vec3(1.0), base + c * a);
        } else if (op < 1.5) {
            return max(vec3(0.0), base - c * a);
        } else if (op < 2.5) {
            return mix(base, base * c, a);
        } else if (op < 3.5) {
            return mix(base, vec3(1.0) - (vec3(1.0) - base) * (vec3(1.0) - c), a);
        }
        return mix(base, c, a);
    }

]] .. sharedShaderSource .. [[

    vec4 effect(vec4 color, Image texture, vec2 texture_coords, vec2 screen_coords)
    {
        vec4 texel = vec4(1.0);
        if (hasTexture > 0.5) {
            texel = Texel(texture, worldUV / affineScale);
        }
        if (texel.a < 0.01) discard;

        vec3 lit = texel.rgb * color.rgb * worldColor.rgb;
        if (passCount > 0.5) {
            lit = applyPass(lit,
                Texel(passMap0, passUvSource0 > 0.5 ? sheenUV : worldUV),
                passBlend0, passStrength0);
        }
        if (passCount > 1.5) {
            lit = applyPass(lit,
                Texel(passMap1, passUvSource1 > 0.5 ? sheenUV : worldUV),
                passBlend1, passStrength1);
        }
        // Quantize after the passes, so an overlay lands in the same palette
        // as everything else instead of floating above it in full precision.
        lit = quantizeWithDither(lit, screen_coords, ditherLevels);
        return vec4(lit, texel.a * color.a * worldColor.a);
    }
    #endif
]]
end

return retro_mesh_shader
