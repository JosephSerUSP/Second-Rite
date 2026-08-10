-- Shared retro mesh shader core for 3D world and item rendering.
-- Provides GLSL source composition for vertex snapping, affine UV mapping,
-- ordered dithering, color quantization, and surface lighting.

local retro_mesh_shader = {}

-- Second Rite's canonical 3D clip/NDC convention is Y-up: +1 is the top edge
-- and -1 is the bottom edge. UI/layout and pixel coordinates stay ordinary
-- Y-down. These helpers are prepended to both generated shaders because the
-- conversions belong to vertex projection, not to the pixel/dither core.
local function runtimeClipYSignLiteral()
    if love and love.getVersion then
        local major = select(1, love.getVersion())
        if major and major >= 12 then return "1.0" end
    end
    return "-1.0"
end

local clipSpaceShaderSource = [[
    float screenYToCanonicalClipY(float screenY, float targetHeight)
    {
        return 1.0 - (2.0 * screenY / targetHeight);
    }

    float canonicalClipYToScreenY(float clipY, float targetHeight)
    {
        return (1.0 - clipY) * targetHeight * 0.5;
    }

    // Shadow-lab runtime boundary. Production LÖVE 11.5 still needs the
    // historical final Y inversion; the pinned LÖVE 12 candidate consumes
    // canonical Y-up clip output directly. Canonical renderer math stays the
    // same on both sides; only this final runtime handoff changes.
    float love11ClipY(float canonicalClipY)
    {
        return canonicalClipY * ]] .. runtimeClipYSignLiteral() .. [[;
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
        if (vertexSnapPixels > 0.0) {
            float pixelX = (ndcX + 1.0) * targetWidth * 0.5;
            float pixelY = canonicalClipYToScreenY(ndcY, targetHeight);
            pixelX = floor((pixelX - compositionOrigin.x) / vertexSnapPixels + 0.5)
                * vertexSnapPixels + compositionOrigin.x;
            pixelY = floor((pixelY - compositionOrigin.y) / vertexSnapPixels + 0.5)
                * vertexSnapPixels + compositionOrigin.y;
            ndcX = pixelX * 2.0 / targetWidth - 1.0;
            ndcY = screenYToCanonicalClipY(pixelY, targetHeight);
        }
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
        if (ditherLevels > 1.0) {
            float threshold = orderedDither(screen_coords - compositionOrigin) - 0.5;
            fogged = floor(clamp(fogged + threshold / ditherLevels, 0.0, 1.0) * ditherLevels + 0.5) / ditherLevels;
        }
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

        float NdotL = max(0.0, dot(N, lightDir));
        float ambient = 0.35;
        float lightIntensity = ambient + (1.0 - ambient) * NdotL;

        worldColor = vec4(VertexColor.rgb * materialColor * lightIntensity, VertexColor.a);

        float ndcX = rotX / halfWidth;
        float ndcY = rotZ / halfHeight;

        if (vertexSnapPixels > 0.0) {
            float pixelX = (ndcX + 1.0) * targetWidth * 0.5;
            float pixelY = canonicalClipYToScreenY(ndcY, targetHeight);
            pixelX = floor(pixelX / vertexSnapPixels + 0.5) * vertexSnapPixels;
            pixelY = floor(pixelY / vertexSnapPixels + 0.5) * vertexSnapPixels;
            ndcX = pixelX * 2.0 / targetWidth - 1.0;
            ndcY = screenYToCanonicalClipY(pixelY, targetHeight);
        }

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

    uniform float ditherLevels;
    uniform float hasTexture;

]] .. sharedShaderSource .. [[

    vec4 effect(vec4 color, Image texture, vec2 texture_coords, vec2 screen_coords)
    {
        vec4 texel = vec4(1.0);
        if (hasTexture > 0.5) {
            texel = Texel(texture, worldUV / affineScale);
        }
        if (texel.a < 0.01) discard;

        vec3 lit = texel.rgb * color.rgb * worldColor.rgb;
        if (ditherLevels > 1.0) {
            float threshold = orderedDither(screen_coords) - 0.5;
            lit = floor(clamp(lit + threshold / ditherLevels, 0.0, 1.0) * ditherLevels + 0.5) / ditherLevels;
        }
        return vec4(lit, texel.a * color.a * worldColor.a);
    }
    #endif
]]
end

return retro_mesh_shader
