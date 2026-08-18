from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8', newline='\n')

def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {text.count(old)}")
    return text.replace(old, new, 1)

def replace_between(text, start, end, replacement, label):
    a = text.find(start)
    b = text.find(end, a + len(start)) if a >= 0 else -1
    if a < 0 or b < 0:
        raise RuntimeError(f"{label}: boundary not found")
    return text[:a] + replacement + text[b:]

# Shared exact direct-definition -> Three consumer. Spatial attributes are one
# runtime-authored definition; placement geometry objects are lightweight views
# that share those BufferAttributes and own only RGB.
write('tools/editor/js/three-definition-consumer.js', r'''(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./thestra-viewport-contract.js'));
    } else {
        root.ThestraThreeDefinitionConsumer = factory(root.ThestraViewportContract);
    }
}(typeof self !== 'undefined' ? self : this, function (Contract) {
    'use strict';

    if (!Contract) throw new Error('ThestraThreeDefinitionConsumer requires ThestraViewportContract.');

    const INSTANCE_TRANSPORT_KIND = 'mesh-definitions-v1';

    function isDirectBundle(bundle) {
        return !!(bundle && bundle.encoding && bundle.encoding.kind === INSTANCE_TRANSPORT_KIND);
    }

    function checkedStream(definition, key, width) {
        const stream = definition && definition[key];
        if (!Array.isArray(stream) || stream.length % width !== 0) {
            throw new Error(`Renderable definition '${definition && definition.id}' has invalid ${key}.`);
        }
        return stream;
    }

    function definitionGeometry(THREE, definition) {
        const positions = checkedStream(definition, 'positions', 3);
        const uvs = checkedStream(definition, 'uvs', 2);
        const normals = checkedStream(definition, 'normals', 3);
        const colors = checkedStream(definition, 'colors', 4);
        const indices = definition && definition.indices;
        if (!Array.isArray(indices) || indices.length % 3 !== 0) {
            throw new Error(`Renderable definition '${definition && definition.id}' has invalid indices.`);
        }
        const vertexCount = positions.length / 3;
        if (uvs.length !== vertexCount * 2 || normals.length !== vertexCount * 3
                || colors.length !== vertexCount * 4) {
            throw new Error(`Renderable definition '${definition && definition.id}' attribute counts disagree.`);
        }

        const outPositions = new Float32Array(vertexCount * 3);
        const outNormals = new Float32Array(vertexCount * 3);
        const outUvs = new Float32Array(uvs.length);
        for (let index = 0; index < vertexCount; index++) {
            const p = index * 3, uv = index * 2;
            const mappedPosition = Contract.runtimeLocalPositionToThestra([
                positions[p], positions[p + 1], positions[p + 2]
            ]);
            const mappedNormal = Contract.runtimeNormalToThestra([
                normals[p], normals[p + 1], normals[p + 2]
            ]);
            outPositions[p] = mappedPosition[0];
            outPositions[p + 1] = mappedPosition[1];
            outPositions[p + 2] = mappedPosition[2];
            outNormals[p] = mappedNormal[0];
            outNormals[p + 1] = mappedNormal[1];
            outNormals[p + 2] = mappedNormal[2];
            outUvs[uv] = Number(uvs[uv]);
            outUvs[uv + 1] = Number(uvs[uv + 1]);
        }

        // Runtime Z-up -> Studio Y-up reverses orientation. The expanded path
        // swaps vertices 2/3; indexed direct consumption performs the exact
        // equivalent by reversing each triangle's final two indices.
        const IndexArray = vertexCount > 65535 ? Uint32Array : Uint16Array;
        const outIndices = new IndexArray(indices.length);
        for (let index = 0; index < indices.length; index += 3) {
            const a = Number(indices[index]);
            const b = Number(indices[index + 1]);
            const c = Number(indices[index + 2]);
            if (![a, b, c].every(value => Number.isInteger(value) && value >= 0 && value < vertexCount)) {
                throw new Error(`Renderable definition '${definition.id}' has an out-of-range triangle index.`);
            }
            outIndices[index] = a;
            outIndices[index + 1] = c;
            outIndices[index + 2] = b;
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(outPositions, 3));
        geometry.setAttribute('normal', new THREE.BufferAttribute(outNormals, 3));
        geometry.setAttribute('uv', new THREE.BufferAttribute(outUvs, 2));
        geometry.setIndex(new THREE.BufferAttribute(outIndices, 1));
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();
        geometry.userData.thestraDefinitionId = definition.id;
        return geometry;
    }

    function placementMatrix(THREE, placement, coordinateSystem) {
        const rows = Contract.runtimePlacementTransformToThestra(placement, coordinateSystem);
        const matrix = new THREE.Matrix4();
        matrix.set(...rows);
        return matrix;
    }

    function placementGeometry(THREE, spatialGeometry, colorState) {
        if (!spatialGeometry || !colorState || !(colorState.authoritative instanceof Float32Array)
                || !(colorState.unlit instanceof Float32Array)
                || colorState.authoritative.length !== colorState.unlit.length) {
            throw new Error('Direct placement geometry requires exact placement-owned RGB state.');
        }
        const position = spatialGeometry.getAttribute('position');
        if (!position || colorState.authoritative.length !== position.count * 3) {
            throw new Error('Direct placement RGB count does not match its runtime definition.');
        }

        // The BufferGeometry object is placement-owned so Three can bind an
        // ordinary per-Mesh colour attribute. The spatial BufferAttributes and
        // index are the SAME objects from the runtime definition: no positions,
        // normals, UVs or topology are cloned per placement.
        const geometry = new THREE.BufferGeometry();
        for (const key of ['position', 'normal', 'uv']) {
            const attribute = spatialGeometry.getAttribute(key);
            if (attribute) geometry.setAttribute(key, attribute);
        }
        geometry.setIndex(spatialGeometry.index);
        geometry.setAttribute('color', new THREE.BufferAttribute(colorState.authoritative.slice(), 3));
        geometry.boundingBox = spatialGeometry.boundingBox && spatialGeometry.boundingBox.clone();
        geometry.boundingSphere = spatialGeometry.boundingSphere && spatialGeometry.boundingSphere.clone();
        geometry.userData.thestraDirectPlacement = true;
        geometry.userData.thestraAuthoritativeColors = colorState.authoritative;
        geometry.userData.thestraUnlitColors = colorState.unlit;
        return geometry;
    }

    function orderedRenderables(bundle) {
        if (!isDirectBundle(bundle) || !Array.isArray(bundle.definitions)
                || !Array.isArray(bundle.placements) || !Array.isArray(bundle.surfaces)) {
            throw new Error(`Direct Three consumer requires ${INSTANCE_TRANSPORT_KIND}.`);
        }
        const count = bundle.placements.length + bundle.surfaces.length;
        const ordered = new Array(count);
        function put(order, entry) {
            if (!Number.isInteger(order) || order < 1 || order > count || ordered[order - 1]) {
                throw new Error(`Renderable instance transport has invalid surface order ${order}.`);
            }
            ordered[order - 1] = entry;
        }
        for (const placement of bundle.placements) {
            put(placement && placement.order, { kind: 'placement', value: placement });
        }
        for (const surface of bundle.surfaces) {
            put(surface && surface.transportOrder, { kind: 'literal', value: surface });
        }
        if (ordered.some(entry => !entry)) {
            throw new Error('Renderable instance transport did not provide every render order.');
        }
        return ordered;
    }

    function updatePlacementLighting(THREE, geometry, placementMatrixValue, lightGrid) {
        const attribute = geometry && geometry.getAttribute('color');
        const positions = geometry && geometry.getAttribute('position');
        const authoritative = geometry && geometry.userData.thestraAuthoritativeColors;
        const unlit = geometry && geometry.userData.thestraUnlitColors;
        if (!attribute || !positions || !authoritative || !unlit) return 0;
        const colors = attribute.array;
        if (!lightGrid) {
            colors.set(authoritative);
            attribute.needsUpdate = true;
            return positions.count;
        }

        const world = new THREE.Vector3();
        for (let index = 0; index < positions.count; index++) {
            world.fromBufferAttribute(positions, index).applyMatrix4(placementMatrixValue);
            const lit = Contract.sampleAuthoringLighting(lightGrid, world.x, world.z);
            const colorIndex = index * 3;
            colors[colorIndex] = unlit[colorIndex] * lit[0];
            colors[colorIndex + 1] = unlit[colorIndex + 1] * lit[1];
            colors[colorIndex + 2] = unlit[colorIndex + 2] * lit[2];
        }
        attribute.needsUpdate = true;
        return positions.count;
    }

    function uniqueAttributeBytes(geometries) {
        const arrays = new Set();
        let bytes = 0;
        for (const geometry of geometries || []) {
            for (const attribute of Object.values(geometry && geometry.attributes || {})) {
                if (!attribute || !attribute.array || arrays.has(attribute.array)) continue;
                arrays.add(attribute.array);
                bytes += attribute.array.byteLength || 0;
            }
            const index = geometry && geometry.index;
            if (index && index.array && !arrays.has(index.array)) {
                arrays.add(index.array);
                bytes += index.array.byteLength || 0;
            }
        }
        return bytes;
    }

    function raycastFirstTriangle(THREE, mesh) {
        const geometry = mesh && mesh.geometry;
        const positions = geometry && geometry.getAttribute('position');
        if (!positions || positions.count < 3) return null;
        const index = geometry.index;
        const ia = index ? index.getX(0) : 0;
        const ib = index ? index.getX(1) : 1;
        const ic = index ? index.getX(2) : 2;
        const a = new THREE.Vector3().fromBufferAttribute(positions, ia).applyMatrix4(mesh.matrixWorld);
        const b = new THREE.Vector3().fromBufferAttribute(positions, ib).applyMatrix4(mesh.matrixWorld);
        const c = new THREE.Vector3().fromBufferAttribute(positions, ic).applyMatrix4(mesh.matrixWorld);
        const center = a.clone().add(b).add(c).multiplyScalar(1 / 3);
        const normal = b.clone().sub(a).cross(c.clone().sub(a)).normalize();
        if (!Number.isFinite(normal.x) || normal.lengthSq() < 1e-10) return null;
        const raycaster = new THREE.Raycaster(center.clone().addScaledVector(normal, 0.1), normal.clone().negate(), 0, 1);
        return raycaster.intersectObject(mesh, false)[0] || null;
    }

    return {
        INSTANCE_TRANSPORT_KIND,
        isDirectBundle,
        definitionGeometry,
        placementMatrix,
        placementGeometry,
        orderedRenderables,
        updatePlacementLighting,
        uniqueAttributeBytes,
        raycastFirstTriangle
    };
}));
''')

# Central coordinate contract: direct definitions are local Z-up, placements
# carry the runtime-authored world transform. Both production and benchmarks use
# these helpers; no second coordinate formula lives in the experiment.
rel = 'tools/editor/js/thestra-viewport-contract.js'
s = read(rel)
s = replace_once(s,
"    function runtimePositionToThestra(value, coordinateSystem) {\n        const origin = coordinateSystem && coordinateSystem.runtimeGridOrigin || { x: 1, y: 1 };\n        return [\n            Number(value[0]) - Number(origin.x || 1),\n            Number(value[2]),\n            Number(value[1]) - Number(origin.y || 1)\n        ];\n    }\n\n    function runtimeNormalToThestra(value) {",
"    function runtimePositionToThestra(value, coordinateSystem) {\n        const origin = coordinateSystem && coordinateSystem.runtimeGridOrigin || { x: 1, y: 1 };\n        return [\n            Number(value[0]) - Number(origin.x || 1),\n            Number(value[2]),\n            Number(value[1]) - Number(origin.y || 1)\n        ];\n    }\n\n    function runtimeLocalPositionToThestra(value) {\n        return [Number(value[0]), Number(value[2]), Number(value[1])];\n    }\n\n    function runtimePlacementTransformToThestra(placement, coordinateSystem) {\n        const transform = placement && placement.transform || {};\n        const m = transform.matrix2d;\n        const t = transform.translation;\n        if (!Array.isArray(m) || m.length !== 4 || !m.every(Number.isFinite)\n                || !Array.isArray(t) || t.length !== 3 || !t.every(Number.isFinite)) {\n            throw new Error(`Renderable placement '${placement && placement.id}' has an invalid transform.`);\n        }\n        const origin = coordinateSystem && coordinateSystem.runtimeGridOrigin || { x: 1, y: 1 };\n        return [\n            Number(m[0]), 0, Number(m[1]), Number(t[0]) - Number(origin.x || 1),\n            0, 1, 0, Number(t[2]),\n            Number(m[2]), 0, Number(m[3]), Number(t[1]) - Number(origin.y || 1),\n            0, 0, 0, 1\n        ];\n    }\n\n    function runtimeNormalToThestra(value) {",
'contract helpers')
s = replace_once(s,
"        transformTriangleStream, runtimePositionToThestra, runtimeNormalToThestra,\n",
"        transformTriangleStream, runtimePositionToThestra, runtimeLocalPositionToThestra,\n        runtimePlacementTransformToThestra, runtimeNormalToThestra,\n",
'contract exports')
write(rel, s)

# Adapter: keep existing expanded modulation as the only colour semantic
# implementation. Direct preparation presents each placement's UNIQUE indexed
# vertices as transient samples to that authority once, then retains only RGB.
rel = 'tools/editor/js/second-rite-editor-adapter.js'
s = read(rel)
s = replace_once(s,
"    const INSTANCE_TRANSPORT_KIND = 'mesh-definitions-v1';\n",
"    const INSTANCE_TRANSPORT_KIND = 'mesh-definitions-v1';\n    const RENDERABLE_CONSUMER_EXPANDED = 'expanded';\n    const RENDERABLE_CONSUMER_DIRECT = 'direct-definitions';\n    const DIRECT_COLOR_STATE = Symbol('thestraDirectPlacementColorState');\n",
'adapter constants')
insert = r'''
    function isDirectTransport(bundle) {
        return !!(bundle && bundle.encoding && bundle.encoding.kind === INSTANCE_TRANSPORT_KIND);
    }

    function directPlacementSample(definition, placement) {
        const positions = checkedStream(definition, 'positions', 3);
        const colors = checkedStream(definition, 'colors', 4);
        const indices = definition && definition.indices;
        const vertexCount = positions.length / 3;
        if (colors.length !== vertexCount * 4 || !Array.isArray(indices) || indices.length % 3 !== 0) {
            throw new Error(`Renderable definition '${definition && definition.id}' has invalid direct-consumer attributes.`);
        }
        for (const sourceIndex of indices) {
            if (!Number.isInteger(sourceIndex) || sourceIndex < 0 || sourceIndex >= vertexCount) {
                throw new Error(`Renderable definition '${definition.id}' has out-of-range index ${sourceIndex}.`);
            }
        }
        const transform = placement && placement.transform || {};
        const matrix = transform.matrix2d;
        const translation = transform.translation;
        if (!Array.isArray(matrix) || matrix.length !== 4 || !matrix.every(Number.isFinite)
                || !Array.isArray(translation) || translation.length !== 3 || !translation.every(Number.isFinite)) {
            throw new Error(`Renderable placement '${placement && placement.id}' has an invalid transform.`);
        }
        const world = new Array(positions.length);
        for (let index = 0; index < vertexCount; index++) {
            const p = index * 3;
            const x = Number(positions[p]), y = Number(positions[p + 1]);
            world[p] = Number(translation[0]) + Number(matrix[0]) * x + Number(matrix[1]) * y;
            world[p + 1] = Number(translation[1]) + Number(matrix[2]) * x + Number(matrix[3]) * y;
            world[p + 2] = Number(translation[2]) + Number(positions[p + 2]);
        }
        return {
            id: placement.id,
            name: placement.name,
            source: placement.source,
            material: placement.material,
            positions: world,
            colors: colors.slice()
        };
    }

    function rgbFromRgba(values, vertexCount) {
        if (!Array.isArray(values) || values.length !== vertexCount * 4) {
            throw new Error('Direct placement modulation returned an invalid RGBA stream.');
        }
        const rgb = new Float32Array(vertexCount * 3);
        for (let src = 0, dst = 0; src < values.length; src += 4, dst += 3) {
            rgb[dst] = Number(values[src]);
            rgb[dst + 1] = Number(values[src + 1]);
            rgb[dst + 2] = Number(values[src + 2]);
        }
        return rgb;
    }

    function prepareDirectTransport(bundle, layersOverride) {
        if (!isDirectTransport(bundle) || !Array.isArray(bundle.definitions)
                || !Array.isArray(bundle.placements) || !Array.isArray(bundle.surfaces)) {
            throw new Error(`Direct renderable consumer requires ${INSTANCE_TRANSPORT_KIND}.`);
        }
        const definitions = new Map();
        for (const definition of bundle.definitions) {
            if (!definition || typeof definition.id !== 'string' || definitions.has(definition.id)) {
                throw new Error('Renderable instance transport has an invalid or duplicate definition id.');
            }
            definitions.set(definition.id, definition);
        }

        // Crucially this is NOT compatibility expansion: each placement exposes
        // one sample per UNIQUE definition vertex, with no indices expanded and
        // no normals/UV/topology copied. Existing Studio shading + static-light
        // code runs once over these transient world-position samples, after
        // which only placement-owned RGB survives.
        const samples = [];
        for (const placement of bundle.placements) {
            const definition = definitions.get(placement && placement.definition);
            if (!definition) {
                throw new Error(`Renderable placement '${placement && placement.id}' references unknown definition '${placement && placement.definition}'.`);
            }
            samples.push(directPlacementSample(definition, placement));
        }
        const layers = layersOverride === undefined ? (bundle.vertexShadingLayers || []) : (layersOverride || []);
        const modulation = {
            surfaces: samples.concat(bundle.surfaces),
            light: bundle.light,
            vertexShadingLayers: bundle.vertexShadingLayers || []
        };
        applyVertexModulation(modulation, layers);
        for (let index = 0; index < samples.length; index++) {
            const sample = samples[index];
            const vertexCount = sample.positions.length / 3;
            Object.defineProperty(bundle.placements[index], DIRECT_COLOR_STATE, {
                value: {
                    unlit: rgbFromRgba(sample.unlitColors, vertexCount),
                    authoritative: rgbFromRgba(sample.colors, vertexCount)
                },
                configurable: true,
                writable: true
            });
        }
        bundle.vertexShadingLayers = layers;
        return bundle;
    }

    function directPlacementColorState(placement) {
        return placement && placement[DIRECT_COLOR_STATE] || null;
    }

    function applyRenderableModulation(bundle, layersOverride) {
        return isDirectTransport(bundle)
            ? prepareDirectTransport(bundle, layersOverride)
            : applyVertexModulation(bundle, layersOverride);
    }

'''
s = replace_once(s,
"    // #757 compatibility boundary: reconstruct today's ordinary surface arrays\n",
insert + "    // #757 compatibility boundary: reconstruct today's ordinary surface arrays\n",
'adapter direct insert')
s = replace_once(s,
"        let response;\n        try {\n            response = await fetcher(renderableUrl, {",
"        const consumer = requestOptions.consumer || RENDERABLE_CONSUMER_EXPANDED;\n        if (consumer !== RENDERABLE_CONSUMER_EXPANDED && consumer !== RENDERABLE_CONSUMER_DIRECT) {\n            throw new Error(`Unknown renderable consumer '${consumer}'.`);\n        }\n        const requestBody = Object.assign(\n            { map },\n            Number.isFinite(requestOptions.seed) ? { seed: requestOptions.seed } : {},\n            consumer === RENDERABLE_CONSUMER_DIRECT ? { renderableEncoding: 'instances' } : {}\n        );\n\n        let response;\n        try {\n            response = await fetcher(renderableUrl, {",
'adapter request consumer')
s = replace_once(s,
"                body: JSON.stringify(Object.assign({ map }, Number.isFinite(requestOptions.seed) ? { seed: requestOptions.seed } : {}))\n",
"                body: JSON.stringify(requestBody)\n",
'adapter request body')
s = replace_once(s,
"        decodeTransport(payload);\n        if (!payload || !Array.isArray(payload.surfaces) || !Array.isArray(payload.materials)) {\n            throw new Error('Runtime renderable bridge returned an invalid bundle.');\n        }\n        return applyVertexModulation(payload, map.vertexShadingLayers || payload.vertexShadingLayers || []);",
"        if (consumer === RENDERABLE_CONSUMER_DIRECT) {\n            if (!isDirectTransport(payload) || !Array.isArray(payload.materials)) {\n                throw new Error(`Runtime renderable bridge did not return ${INSTANCE_TRANSPORT_KIND}.`);\n            }\n            return applyRenderableModulation(payload, map.vertexShadingLayers || payload.vertexShadingLayers || []);\n        }\n        decodeTransport(payload);\n        if (!payload || !Array.isArray(payload.surfaces) || !Array.isArray(payload.materials)) {\n            throw new Error('Runtime renderable bridge returned an invalid bundle.');\n        }\n        return applyVertexModulation(payload, map.vertexShadingLayers || payload.vertexShadingLayers || []);",
'adapter load result')
s = replace_once(s,
"        INSTANCE_TRANSPORT_KIND,\n        buildScene,",
"        INSTANCE_TRANSPORT_KIND,\n        RENDERABLE_CONSUMER_EXPANDED,\n        RENDERABLE_CONSUMER_DIRECT,\n        buildScene,",
'adapter export constants')
s = replace_once(s,
"        applyVertexLighting,\n        applyVertexModulation\n",
"        applyVertexLighting,\n        applyVertexModulation,\n        applyRenderableModulation,\n        prepareDirectTransport,\n        directPlacementColorState,\n        isDirectTransport\n",
'adapter export functions')
write(rel, s)

# Bridge: compact encoding is an explicit request-owned host capability. Remove
# stale shell state for the control path; only direct Studio requests opt in.
rel = 'tools/editor/runtime-bridge-server.js'
s = read(rel)
s = replace_once(s,
"    if (value.seed !== undefined && !Number.isFinite(Number(value.seed))) {\n        throw new Error('seed must be numeric');\n    }\n    return {\n        map: value.map,\n        seed: value.seed === undefined ? 1735689600 : Number(value.seed),\n    };",
"    if (value.seed !== undefined && !Number.isFinite(Number(value.seed))) {\n        throw new Error('seed must be numeric');\n    }\n    if (value.renderableEncoding !== undefined && value.renderableEncoding !== 'instances') {\n        throw new Error(`unsupported renderable encoding '${value.renderableEncoding}'`);\n    }\n    return {\n        map: value.map,\n        seed: value.seed === undefined ? 1735689600 : Number(value.seed),\n        ...(value.renderableEncoding ? { renderableEncoding: value.renderableEncoding } : {}),\n    };",
'bridge validation')
s = replace_once(s,
"    const { command, requestEnvironmentKey, envelope, parseOutput, maxBuffer } = spec;",
"    const { command, requestEnvironmentKey, encodingEnvironmentKey, envelope, parseOutput, maxBuffer } = spec;",
'bridge spec destructure')
s = replace_once(s,
"    const env = projectPlay.launchEnvironment(null, dataSnapshot);\n    env[requestEnvironmentKey] = file.relative;\n",
"    const env = projectPlay.launchEnvironment(null, dataSnapshot);\n    env[requestEnvironmentKey] = file.relative;\n    if (encodingEnvironmentKey) {\n        delete env[encodingEnvironmentKey];\n        if (request.renderableEncoding) env[encodingEnvironmentKey] = request.renderableEncoding;\n    }\n",
'bridge encoding env')
s = replace_once(s,
"        requestEnvironmentKey: 'SECOND_RITE_RENDERABLE_REQUEST',\n        envelope:",
"        requestEnvironmentKey: 'SECOND_RITE_RENDERABLE_REQUEST',\n        encodingEnvironmentKey: 'SECOND_RITE_RENDERABLE_ENCODING',\n        envelope:",
'bridge renderable spec')
write(rel, s)

# Viewport: consume exact compact output. Definition spatial BufferAttributes are
# shared; each ordinary Mesh gets a tiny geometry view and unique RGB only.
rel = 'tools/editor/js/three-editor-viewport-base.js'
s = read(rel)
s = replace_once(s,
"import '/js/three-world-fidelity-core.js';\n",
"import '/js/three-world-fidelity-core.js';\nimport '/js/three-definition-consumer.js';\n",
'viewport import')
s = replace_once(s,
"const WorldFidelity = globalThis.ThestraThreeWorldFidelityCore;\nif (!WorldFidelity) throw new Error('Thestra world fidelity core failed to load.');\n",
"const WorldFidelity = globalThis.ThestraThreeWorldFidelityCore;\nif (!WorldFidelity) throw new Error('Thestra world fidelity core failed to load.');\nconst DirectDefinitions = globalThis.ThestraThreeDefinitionConsumer;\nif (!DirectDefinitions) throw new Error('Thestra direct definition consumer failed to load.');\nconst EditorAdapter = globalThis.SecondRiteEditorAdapter;\nif (!EditorAdapter) throw new Error('Second Rite editor adapter failed to load.');\n",
'viewport globals')
old_loop = r'''        for (const geometry of renderableGeometries) {
            const attribute = geometry.getAttribute('color');
            const authoritative = geometry.userData.thestraAuthoritativeColors;
            const unlit = geometry.userData.thestraUnlitColors;
            const positions = geometry.getAttribute('position');
            if (!attribute || !authoritative || !unlit || !positions) continue;

            const colors = attribute.array;
            if (!lightGrid) {
                colors.set(authoritative);
                attribute.needsUpdate = true;
                continue;
            }

            const xyz = positions.array;
            for (let index = 0; index < positions.count; index++) {
                const positionIndex = index * 3;
                const lit = Contract.sampleAuthoringLighting(
                    lightGrid, xyz[positionIndex], xyz[positionIndex + 2]
                );
                colors[positionIndex] = unlit[positionIndex] * lit[0];
                colors[positionIndex + 1] = unlit[positionIndex + 1] * lit[1];
                colors[positionIndex + 2] = unlit[positionIndex + 2] * lit[2];
            }
            attribute.needsUpdate = true;
        }
'''
new_loop = r'''        for (const geometry of renderableGeometries) {
            if (geometry.userData.thestraDirectPlacement) {
                DirectDefinitions.updatePlacementLighting(
                    THREE, geometry, geometry.userData.thestraPlacementMatrix, lightGrid
                );
                continue;
            }
            const attribute = geometry.getAttribute('color');
            const authoritative = geometry.userData.thestraAuthoritativeColors;
            const unlit = geometry.userData.thestraUnlitColors;
            const positions = geometry.getAttribute('position');
            if (!attribute || !authoritative || !unlit || !positions) continue;

            const colors = attribute.array;
            if (!lightGrid) {
                colors.set(authoritative);
                attribute.needsUpdate = true;
                continue;
            }

            const xyz = positions.array;
            for (let index = 0; index < positions.count; index++) {
                const positionIndex = index * 3;
                const lit = Contract.sampleAuthoringLighting(
                    lightGrid, xyz[positionIndex], xyz[positionIndex + 2]
                );
                colors[positionIndex] = unlit[positionIndex] * lit[0];
                colors[positionIndex + 1] = unlit[positionIndex + 1] * lit[1];
                colors[positionIndex + 2] = unlit[positionIndex + 2] * lit[2];
            }
            attribute.needsUpdate = true;
        }
'''
s = replace_once(s, old_loop, new_loop, 'viewport live lighting')
new_set = r'''    function setRenderableBundle(bundle) {
        clearGroup(renderableContent);
        renderableSelectable.length = 0;
        renderableGeometries.length = 0;
        const directBundle = DirectDefinitions.isDirectBundle(bundle);
        hasAuthoritativeBundle = !!(bundle && Array.isArray(bundle.surfaces)
            && (!bundle.encoding || directBundle));
        syncProxyVisibility();
        syncLayerVisuals();
        markLiveLightingDirty();
        if (!hasAuthoritativeBundle) {
            setSelection(selection);
            return;
        }

        const materialById = new Map();
        (bundle.materials || []).forEach(spec => materialById.set(spec.id, createBundleMaterial(spec)));
        function materialFor(id) {
            return materialById.get(id)
                || WorldFidelity.decorateResolvedWorldMaterial(new THREE.MeshStandardMaterial({
                    color: 0x777777, roughness: 0.9, side: THREE.DoubleSide, vertexColors: true
                }));
        }
        function addMesh(mesh, source, materialId, order) {
            mesh.userData.thestraSource = source || null;
            mesh.userData.thestraMaterialId = materialId || null;
            mesh.userData.thestraTransportOrder = order;
            renderableContent.add(mesh);
            renderableGeometries.push(mesh.geometry);
            const semantic = semanticFromSource(source);
            if (semantic) addRenderableSelectable(mesh, semantic);
        }

        if (directBundle) {
            const definitions = new Map();
            for (const definition of bundle.definitions || []) {
                if (!definition || typeof definition.id !== 'string' || definitions.has(definition.id)) {
                    throw new Error('Direct renderable bundle has an invalid or duplicate definition id.');
                }
                definitions.set(definition.id, DirectDefinitions.definitionGeometry(THREE, definition));
            }
            for (const entry of DirectDefinitions.orderedRenderables(bundle)) {
                if (entry.kind === 'literal') {
                    const surface = entry.value;
                    if (!surface || !Array.isArray(surface.positions) || surface.positions.length < 9) continue;
                    const geometry = createBundleGeometry(surface, bundle.coordinateSystem || {});
                    const mesh = new THREE.Mesh(geometry, materialFor(surface.material));
                    mesh.name = surface.name || surface.id || 'runtime-literal-surface';
                    addMesh(mesh, surface.source, surface.material, surface.transportOrder);
                    continue;
                }
                const placement = entry.value;
                const spatial = definitions.get(placement && placement.definition);
                if (!spatial) {
                    throw new Error(`Renderable placement '${placement && placement.id}' references unknown definition '${placement && placement.definition}'.`);
                }
                const colorState = EditorAdapter.directPlacementColorState(placement);
                if (!colorState) {
                    throw new Error(`Renderable placement '${placement && placement.id}' has no prepared placement colour state.`);
                }
                const geometry = DirectDefinitions.placementGeometry(THREE, spatial, colorState);
                const mesh = new THREE.Mesh(geometry, materialFor(placement.material));
                mesh.name = placement.name || placement.id || 'runtime-placement';
                mesh.matrixAutoUpdate = false;
                mesh.matrix.copy(DirectDefinitions.placementMatrix(
                    THREE, placement, bundle.coordinateSystem || {}
                ));
                geometry.userData.thestraPlacementMatrix = mesh.matrix;
                addMesh(mesh, placement.source, placement.material, placement.order);
            }
            renderableContent.updateMatrixWorld(true);
            setSelection(selection);
            return;
        }

        (bundle.surfaces || []).forEach(surface => {
            if (!surface || !Array.isArray(surface.positions) || surface.positions.length < 9) return;
            const geometry = createBundleGeometry(surface, bundle.coordinateSystem || {});
            const mesh = new THREE.Mesh(geometry, materialFor(surface.material));
            mesh.name = surface.name || surface.id || 'runtime-surface';
            addMesh(mesh, surface.source, surface.material, null);
        });
        setSelection(selection);
    }

'''
s = replace_between(s, "    function setRenderableBundle(bundle) {", "    function setSelection(next) {", new_set, 'viewport bundle setter')
write(rel, s)

# Workspace production hot path defaults to direct definitions. Expanded remains
# a deliberate control/fallback via THESTRA_MAP_RENDERABLE_CONSUMER='expanded'.
rel = 'tools/editor/js/thestra-editor-workspace.js'
s = read(rel)
s = replace_once(s,
"            Adapter.applyVertexModulation(currentBundle, map.vertexShadingLayers || []);\n",
"            Adapter.applyRenderableModulation(currentBundle, map.vertexShadingLayers || []);\n",
'workspace local modulation')
s = replace_once(s,
"            const bundle = await Adapter.loadRenderable(map, {\n                seed: inspection && inspection.request && inspection.request.seed\n            });",
"            const requestedConsumer = window.THESTRA_MAP_RENDERABLE_CONSUMER === Adapter.RENDERABLE_CONSUMER_EXPANDED\n                ? Adapter.RENDERABLE_CONSUMER_EXPANDED\n                : Adapter.RENDERABLE_CONSUMER_DIRECT;\n            const bundle = await Adapter.loadRenderable(map, {\n                seed: inspection && inspection.request && inspection.request.seed,\n                consumer: requestedConsumer\n            });",
'workspace direct request')
write(rel, s)

# Bench helper now delegates all spatial/transform rules to the production core.
rel = 'tools/editor/three-definition-transport.js'
s = read(rel)
s = replace_once(s,
"const Contract = require('./js/thestra-viewport-contract.js');\n",
"const Contract = require('./js/thestra-viewport-contract.js');\nconst Core = require('./js/three-definition-consumer.js');\n",
'bench helper core require')
# Replace the duplicated definition and placement functions wholesale.
s = replace_between(s, "function definitionGeometry(definition) {", "function expandedLiteralGeometry(surface, coordinateSystem) {",
r'''function definitionGeometry(definition) {
    return Core.definitionGeometry(THREE, definition);
}

function placementMatrix(placement, coordinateSystem) {
    return Core.placementMatrix(THREE, placement, coordinateSystem);
}

''', 'bench helper spatial core')
s = replace_once(s,
"    INSTANCE_TRANSPORT_KIND,\n",
"    INSTANCE_TRANSPORT_KIND,\n",
'bench helper noop constant')
write(rel, s)

# Focused contract tests: compact structure survives, spatial attributes are
# actually shared, RGB is placement-owned, and ordinary raycast still works.
rel = 'tools/editor/test-instance-transport.js'
s = read(rel)
s = replace_once(s,
"const adapter = require('./js/second-rite-editor-adapter.js');\n",
"const adapter = require('./js/second-rite-editor-adapter.js');\nconst Direct = require('./js/three-definition-consumer.js');\nconst THREE = require('three');\n",
'test direct imports')
s += r'''

test('direct consumer keeps compact topology and owns colour per placement only', () => {
    const bundle = compactFixture();
    adapter.applyRenderableModulation(bundle, []);

    assert.equal(bundle.encoding.kind, adapter.INSTANCE_TRANSPORT_KIND);
    assert.equal(bundle.definitions.length, 1);
    assert.equal(bundle.placements.length, 2);
    assert.equal(bundle.surfaces.length, 1, 'literal surfaces remain literal; placements were not compatibility-expanded');
    assert.equal('positions' in bundle.placements[0], false, 'placement never grows an expanded spatial stream');

    const first = adapter.directPlacementColorState(bundle.placements[0]);
    const second = adapter.directPlacementColorState(bundle.placements[1]);
    assert.ok(first && second);
    assert.notStrictEqual(first.authoritative, second.authoritative);
    assert.notStrictEqual(first.unlit, second.unlit);
    assert.ok(second.authoritative[0] < first.authoritative[0],
        'placement-dependent orientation tint remains placement-owned');

    const spatial = Direct.definitionGeometry(THREE, bundle.definitions[0]);
    const firstGeometry = Direct.placementGeometry(THREE, spatial, first);
    const secondGeometry = Direct.placementGeometry(THREE, spatial, second);
    assert.strictEqual(firstGeometry.getAttribute('position'), secondGeometry.getAttribute('position'));
    assert.strictEqual(firstGeometry.getAttribute('normal'), secondGeometry.getAttribute('normal'));
    assert.strictEqual(firstGeometry.getAttribute('uv'), secondGeometry.getAttribute('uv'));
    assert.strictEqual(firstGeometry.index, secondGeometry.index);
    assert.notStrictEqual(firstGeometry.getAttribute('color'), secondGeometry.getAttribute('color'));
    assert.notStrictEqual(firstGeometry.getAttribute('color').array, secondGeometry.getAttribute('color').array);

    const peerBefore = secondGeometry.getAttribute('color').array.slice();
    firstGeometry.getAttribute('color').array[0] = 0.123;
    assert.deepEqual(Array.from(secondGeometry.getAttribute('color').array), Array.from(peerBefore),
        'mutating one placement RGB buffer must not leak into a peer sharing spatial attributes');

    const mesh = new THREE.Mesh(firstGeometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide }));
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(Direct.placementMatrix(THREE, bundle.placements[0], {}));
    mesh.matrixWorld.copy(mesh.matrix);
    const hit = Direct.raycastFirstTriangle(THREE, mesh);
    assert.ok(hit, 'ordinary THREE.Mesh remains raycastable');
    assert.ok(Math.abs(hit.distance - 0.1) < 1e-6);
});

test('direct geometry matches the compatibility path triangle-for-triangle', () => {
    const directBundle = compactFixture();
    adapter.applyRenderableModulation(directBundle, []);
    const control = compactFixture();
    adapter.decodeTransport(control);
    adapter.applyVertexModulation(control, []);

    const definition = directBundle.definitions[0];
    const placement = directBundle.placements[0];
    const spatial = Direct.definitionGeometry(THREE, definition);
    const geometry = Direct.placementGeometry(
        THREE, spatial, adapter.directPlacementColorState(placement)
    );
    const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true }));
    mesh.matrixAutoUpdate = false;
    mesh.matrix.copy(Direct.placementMatrix(THREE, placement, {}));
    mesh.matrixWorld.copy(mesh.matrix);

    const expectedSurface = control.surfaces[0];
    const Contract = require('./js/thestra-viewport-contract.js');
    const expectedPositions = Contract.transformTriangleStream(
        expectedSurface.positions, 3, value => Contract.runtimePositionToThestra(value, {})
    );
    const expectedUvs = Contract.transformTriangleStream(expectedSurface.uvs, 2);
    const expectedColors = Contract.transformTriangleStream(expectedSurface.colors, 4);
    const index = geometry.index;
    const position = geometry.getAttribute('position');
    const uv = geometry.getAttribute('uv');
    const color = geometry.getAttribute('color');
    const world = new THREE.Vector3();
    for (let out = 0; out < index.count; out++) {
        const source = index.getX(out);
        world.fromBufferAttribute(position, source).applyMatrix4(mesh.matrixWorld);
        const p = out * 3, u = out * 2, c = out * 4;
        assert.ok(Math.abs(world.x - expectedPositions[p]) < 1e-6);
        assert.ok(Math.abs(world.y - expectedPositions[p + 1]) < 1e-6);
        assert.ok(Math.abs(world.z - expectedPositions[p + 2]) < 1e-6);
        assert.ok(Math.abs(uv.getX(source) - expectedUvs[u]) < 1e-6);
        assert.ok(Math.abs(uv.getY(source) - expectedUvs[u + 1]) < 1e-6);
        assert.ok(Math.abs(color.getX(source) - expectedColors[c]) < 1e-6);
        assert.ok(Math.abs(color.getY(source) - expectedColors[c + 1]) < 1e-6);
        assert.ok(Math.abs(color.getZ(source) - expectedColors[c + 2]) < 1e-6);
    }
    assert.equal(placement.material, expectedSurface.material);
    assert.deepEqual(placement.source, expectedSurface.source);
});
'''
write(rel, s)

# Bridge tests pin explicit opt-in and stale-environment deletion.
rel = 'tools/editor/test-runtime-bridge.js'
s = read(rel)
s = replace_once(s,
"    const source = { map: { id: 7, layout: ['#.#'] }, seed: '42' };\n",
"    const source = { map: { id: 7, layout: ['#.#'] }, seed: '42', renderableEncoding: 'instances' };\n",
'bridge validation fixture')
s = replace_once(s,
"    assert.equal(value.seed, 42);\n});",
"    assert.equal(value.seed, 42);\n    assert.equal(value.renderableEncoding, 'instances');\n    assert.throws(() => bridge.validateRequest({ map: { id: 7 }, renderableEncoding: 'packed' }),\n        /unsupported renderable encoding/);\n});",
'bridge validation assertions')
s = replace_once(s,
"        const value = await bridge.compileRenderable({ map: { id: 1 }, seed: 1 }, {",
"        const value = await bridge.compileRenderable({ map: { id: 1 }, seed: 1, renderableEncoding: 'instances' }, {",
'bridge external direct request')
s = replace_once(s,
"                    assert.equal(options.env.THESTRA_RUNTIME_DATA_ROOT, undefined,\n                        'external compiled stage must not need same-root data override');\n                    requestPath = path.join(stagedRoot, options.env.SECOND_RITE_RENDERABLE_REQUEST);\n                    assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')), { map: { id: 1 }, seed: 1 });",
"                    assert.equal(options.env.THESTRA_RUNTIME_DATA_ROOT, undefined,\n                        'external compiled stage must not need same-root data override');\n                    assert.equal(options.env.SECOND_RITE_RENDERABLE_ENCODING, 'instances');\n                    requestPath = path.join(stagedRoot, options.env.SECOND_RITE_RENDERABLE_REQUEST);\n                    assert.deepEqual(JSON.parse(fs.readFileSync(requestPath, 'utf8')),\n                        { map: { id: 1 }, seed: 1, renderableEncoding: 'instances' });",
'bridge external env assertions')
s = replace_once(s,
"                assert.equal(options.env.THESTRA_RUNTIME_DATA_ROOT,\n                    'tmp/editor-runtime-data/snapshot-fixture/data');\n                requestPath = path.join(root, options.env.SECOND_RITE_RENDERABLE_REQUEST);",
"                assert.equal(options.env.THESTRA_RUNTIME_DATA_ROOT,\n                    'tmp/editor-runtime-data/snapshot-fixture/data');\n                assert.equal(options.env.SECOND_RITE_RENDERABLE_ENCODING, undefined,\n                    'expanded control must not inherit compact encoding');\n                requestPath = path.join(root, options.env.SECOND_RITE_RENDERABLE_REQUEST);",
'bridge expanded control env')
write(rel, s)

# Lighting/source tests pin production direct wiring and explicit fallback.
rel = 'tools/editor/tests/test-map-3d-lighting.js'
s = read(rel)
s += r'''

test('direct definition viewport keeps placement RGB isolated while sharing only spatial attributes', () => {
    const viewportSource = fs.readFileSync(
        path.join(ROOT, 'tools', 'editor', 'js', 'three-editor-viewport-base.js'), 'utf8'
    );
    const workspaceSource = fs.readFileSync(
        path.join(ROOT, 'tools', 'editor', 'js', 'thestra-editor-workspace.js'), 'utf8'
    );
    assert.match(viewportSource, /three-definition-consumer\.js/);
    assert.match(viewportSource, /DirectDefinitions\.placementGeometry/);
    assert.match(viewportSource, /DirectDefinitions\.updatePlacementLighting/,
        'live light edits must update the exact placement-owned direct RGB path');
    assert.match(viewportSource, /geometry\.userData\.thestraPlacementMatrix = mesh\.matrix/,
        'live lighting must sample direct local vertices through the runtime-authored placement transform');
    assert.match(workspaceSource, /THESTRA_MAP_RENDERABLE_CONSUMER/,
        'production direct path retains an explicit expanded parity/fallback control');
    assert.match(workspaceSource, /Adapter\.RENDERABLE_CONSUMER_DIRECT/);
    assert.match(workspaceSource, /Adapter\.applyRenderableModulation/,
        'live vertex-shading edits must refresh compact placement colour state without compatibility decode');
});
'''
write(rel, s)

# Final benchmark uses the exact production colour prep + Three spatial core.
write('tools/editor/bench-three-placement-colors.js', r'''\
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');
const THREE = require('three');
const adapter = require('./js/second-rite-editor-adapter.js');
const Contract = require('./js/thestra-viewport-contract.js');
const Direct = require('./js/three-definition-consumer.js');
const projectPlay = require('./project-play');
const authoredStorage = require('./authored-storage');

const SEED = 1735689600;
const MAX_BUFFER = 16 * 1024 * 1024;
function argument(name, fallback) {
    const index = process.argv.indexOf(name);
    return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}
function round(value) { return Number(value.toFixed(3)); }
function mib(bytes) { return Number((bytes / (1024 * 1024)).toFixed(3)); }
function heap() { if (global.gc) global.gc(); return process.memoryUsage().heapUsed; }
function close(a, b, epsilon = 1e-6) { return Math.abs(Number(a) - Number(b)) <= epsilon; }

const installRoot = path.resolve(argument('--install-root', path.join(__dirname, '..', '..')));
const projectRoot = path.resolve(argument('--project-root', path.join(installRoot, 'projects', 'hichaukitoden-game')));
const loveExe = path.resolve(argument('--love', process.env.LOVE_PATH || 'C:\\Program Files\\LOVE\\love.exe'));
const lovec = /love\.exe$/i.test(loveExe) ? loveExe.replace(/love\.exe$/i, 'lovec.exe') : loveExe;
if (!fs.existsSync(lovec)) throw new Error(`LÖVE console executable not found: ${lovec}`);

const authoredMaps = authoredStorage.loadOrderedCollection(path.join(projectRoot, 'data'), 'maps').entries;
function mapSnapshot(id) {
    const map = authoredMaps.find(candidate => String(candidate.id) === String(id));
    if (!map) throw new Error(`Map ${id} not found in opened Project.`);
    return map;
}

function runtimeCompact(runtimeRoot, id, map) {
    const requestDir = path.join(runtimeRoot, 'tmp', 'issue-765-final-benchmark');
    fs.mkdirSync(requestDir, { recursive: true });
    const requestPath = path.join(requestDir, `map-${id}-${process.pid}.json`);
    fs.writeFileSync(requestPath, JSON.stringify({ map, seed: SEED }));
    const env = projectPlay.launchEnvironment({
        SECOND_RITE_RENDERABLE_REQUEST: path.relative(runtimeRoot, requestPath).split(path.sep).join('/'),
        SECOND_RITE_RENDERABLE_ENCODING: 'instances',
    });
    const child = spawnSync(lovec, ['.', 'preview-map', String(id)], {
        cwd: runtimeRoot, env, encoding: 'utf8', windowsHide: true,
        maxBuffer: MAX_BUFFER, timeout: 120000,
    });
    try { fs.unlinkSync(requestPath); } catch (_) {}
    if (child.error) throw child.error;
    if (child.status !== 0) throw new Error(`LÖVE Map ${id} failed: ${child.stderr || child.stdout}`);
    const match = String(child.stdout).match(/RENDERABLE BEGIN\s*([\s\S]*?)\s*RENDERABLE END/);
    if (!match) throw new Error(`Map ${id}: no complete renderable envelope.`);
    return match[1];
}

function expandedLiteralGeometry(surface, coordinateSystem) {
    const source = surface && surface.positions || [];
    if (!Array.isArray(source) || source.length < 9 || source.length % 9 !== 0) return null;
    const positions = new Float32Array(Contract.transformTriangleStream(
        source, 3, value => Contract.runtimePositionToThestra(value, coordinateSystem)
    ));
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const normals = surface.normals || [];
    if (normals.length === positions.length) {
        geometry.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(
            Contract.transformTriangleStream(normals, 3, Contract.runtimeNormalToThestra)
        ), 3));
    } else geometry.computeVertexNormals();
    const uvs = surface.uvs || [];
    if (uvs.length === positions.length / 3 * 2) {
        geometry.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(
            Contract.transformTriangleStream(uvs, 2)
        ), 2));
    }
    const rgba = surface.colors || [];
    const reordered = Contract.transformTriangleStream(rgba, 4);
    const rgb = new Float32Array(positions.length);
    for (let src = 0, dst = 0; src < reordered.length; src += 4, dst += 3) {
        rgb[dst] = reordered[src]; rgb[dst + 1] = reordered[src + 1]; rgb[dst + 2] = reordered[src + 2];
    }
    geometry.setAttribute('color', new THREE.BufferAttribute(rgb, 3));
    geometry.computeBoundingBox(); geometry.computeBoundingSphere();
    return geometry;
}

function buildProductionDirect(bundle) {
    const scene = new THREE.Scene();
    const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide });
    const definitions = new Map();
    const spatialGeometries = [];
    for (const definition of bundle.definitions) {
        const geometry = Direct.definitionGeometry(THREE, definition);
        definitions.set(definition.id, geometry);
        spatialGeometries.push(geometry);
    }
    const placementMeshes = [];
    const literalMeshes = [];
    for (const entry of Direct.orderedRenderables(bundle)) {
        if (entry.kind === 'literal') {
            const surface = entry.value;
            const geometry = expandedLiteralGeometry(surface, bundle.coordinateSystem || {});
            if (!geometry) continue;
            const mesh = new THREE.Mesh(geometry, material);
            mesh.userData.thestraSource = surface.source || null;
            mesh.userData.thestraMaterialId = surface.material || null;
            mesh.userData.thestraTransportOrder = surface.transportOrder;
            scene.add(mesh); literalMeshes.push(mesh);
            continue;
        }
        const placement = entry.value;
        const geometry = Direct.placementGeometry(
            THREE, definitions.get(placement.definition), adapter.directPlacementColorState(placement)
        );
        const mesh = new THREE.Mesh(geometry, material);
        mesh.matrixAutoUpdate = false;
        mesh.matrix.copy(Direct.placementMatrix(THREE, placement, bundle.coordinateSystem || {}));
        mesh.userData.thestraSource = placement.source || null;
        mesh.userData.thestraMaterialId = placement.material || null;
        mesh.userData.thestraTransportOrder = placement.order;
        geometry.userData.thestraPlacementMatrix = mesh.matrix;
        scene.add(mesh); placementMeshes.push(mesh);
    }
    scene.updateMatrixWorld(true);
    return { scene, material, spatialGeometries, placementMeshes, literalMeshes };
}

function placementStateBytes(bundle) {
    let bytes = 0;
    for (const placement of bundle.placements) {
        const state = adapter.directPlacementColorState(placement);
        bytes += state.unlit.byteLength + state.authoritative.byteLength;
    }
    return bytes;
}
function placementAttributeBytes(built) {
    return built.placementMeshes.reduce((sum, mesh) => sum + mesh.geometry.getAttribute('color').array.byteLength, 0);
}
function literalAttributeBytes(built) {
    return Direct.uniqueAttributeBytes(built.literalMeshes.map(mesh => mesh.geometry));
}

function parityAgainstExpanded(jsonText, map, directBundle) {
    const expanded = JSON.parse(jsonText);
    adapter.decodeTransport(expanded);
    adapter.applyVertexModulation(expanded, map.vertexShadingLayers || expanded.vertexShadingLayers || []);
    const definitions = new Map(directBundle.definitions.map(definition => [definition.id, definition]));
    let tuples = 0, colorComponents = 0, mismatchCount = 0, maxAbsError = 0;
    for (const placement of directBundle.placements) {
        const definition = definitions.get(placement.definition);
        const expected = expanded.surfaces[Number(placement.order) - 1];
        const state = adapter.directPlacementColorState(placement);
        if (!expected || !definition || !state) throw new Error(`Missing parity data for ${placement.id}`);
        if (expected.material !== placement.material || JSON.stringify(expected.source) !== JSON.stringify(placement.source)) {
            throw new Error(`Provenance/material mismatch for ${placement.id}`);
        }
        const matrix = placement.transform.matrix2d, translation = placement.transform.translation;
        for (let out = 0; out < definition.indices.length; out++) {
            const sourceIndex = Number(definition.indices[out]);
            const p = sourceIndex * 3, uv = sourceIndex * 2, c = sourceIndex * 4;
            const ep = out * 3, euv = out * 2, ec = out * 4;
            const x = Number(definition.positions[p]), y = Number(definition.positions[p + 1]);
            const expectedValues = [
                Number(translation[0]) + Number(matrix[0]) * x + Number(matrix[1]) * y,
                Number(translation[1]) + Number(matrix[2]) * x + Number(matrix[3]) * y,
                Number(translation[2]) + Number(definition.positions[p + 2]),
                Number(definition.uvs[uv]), Number(definition.uvs[uv + 1])
            ];
            const controlValues = [
                expected.positions[ep], expected.positions[ep + 1], expected.positions[ep + 2],
                expected.uvs[euv], expected.uvs[euv + 1]
            ];
            for (let i = 0; i < expectedValues.length; i++) {
                if (!close(expectedValues[i], controlValues[i])) mismatchCount++;
                maxAbsError = Math.max(maxAbsError, Math.abs(expectedValues[i] - controlValues[i]));
            }
            for (let channel = 0; channel < 3; channel++) {
                const error = Math.abs(Number(expected.colors[ec + channel]) - Number(state.authoritative[sourceIndex * 3 + channel]));
                if (error > 1e-6) mismatchCount++;
                maxAbsError = Math.max(maxAbsError, error);
                colorComponents++;
            }
            tuples++;
        }
    }
    return { tuples, colorComponents, mismatchCount, maxAbsError };
}

function liveLightingProof(bundle, built) {
    if (!Array.isArray(bundle.light)) return { updateMs: 0, compared: 0, mismatchCount: 0, maxAbsError: 0, noLeak: true };
    const started = performance.now();
    let compared = 0, mismatchCount = 0, maxAbsError = 0;
    for (const mesh of built.placementMeshes) {
        Direct.updatePlacementLighting(THREE, mesh.geometry, mesh.matrix, bundle.light);
        const current = mesh.geometry.getAttribute('color').array;
        const baseline = mesh.geometry.userData.thestraAuthoritativeColors;
        for (let index = 0; index < current.length; index++) {
            const error = Math.abs(Number(current[index]) - Number(baseline[index]));
            if (error > 1e-6) mismatchCount++;
            maxAbsError = Math.max(maxAbsError, error); compared++;
        }
    }
    const updateMs = performance.now() - started;

    let noLeak = true;
    const byDefinition = new Map();
    for (let index = 0; index < bundle.placements.length; index++) {
        const placement = bundle.placements[index];
        const list = byDefinition.get(placement.definition) || [];
        list.push(built.placementMeshes[index]);
        byDefinition.set(placement.definition, list);
    }
    const peers = [...byDefinition.values()].find(list => list.length >= 2);
    if (peers) {
        const before = peers[1].geometry.getAttribute('color').array.slice();
        const zero = bundle.light.map(row => row.map(() => [0, 0, 0]));
        Direct.updatePlacementLighting(THREE, peers[0].geometry, peers[0].matrix, zero);
        const after = peers[1].geometry.getAttribute('color').array;
        noLeak = before.length === after.length && before.every((value, index) => value === after[index]);
    }
    return { updateMs: round(updateMs), compared, mismatchCount, maxAbsError, noLeak };
}

function pickProof(built) {
    for (const mesh of built.placementMeshes.concat(built.literalMeshes)) {
        if (!mesh.userData.thestraSource) continue;
        const hit = Direct.raycastFirstTriangle(THREE, mesh);
        if (hit) return {
            hit: true,
            source: mesh.userData.thestraSource,
            material: mesh.userData.thestraMaterialId,
            order: mesh.userData.thestraTransportOrder,
            distance: round(hit.distance)
        };
    }
    return { hit: false };
}

function runMap(runtimeRoot, id) {
    const map = mapSnapshot(id);
    const jsonText = runtimeCompact(runtimeRoot, id, map);
    const bundle = JSON.parse(jsonText);
    const literalCount = bundle.surfaces.length;
    const before = heap();
    const prepStarted = performance.now();
    adapter.applyRenderableModulation(bundle, map.vertexShadingLayers || bundle.vertexShadingLayers || []);
    const prepMs = performance.now() - prepStarted;
    const ready = heap();
    if (!Direct.isDirectBundle(bundle) || bundle.surfaces.length !== literalCount
            || bundle.placements.some(placement => Object.prototype.hasOwnProperty.call(placement, 'positions'))) {
        throw new Error('Compatibility expansion was reintroduced into the direct path.');
    }

    const sceneStarted = performance.now();
    const built = buildProductionDirect(bundle);
    const sceneMs = performance.now() - sceneStarted;
    const afterScene = heap();
    const parity = parityAgainstExpanded(jsonText, map, bundle);
    const live = liveLightingProof(bundle, built);
    const sharedSpatialBytes = Direct.uniqueAttributeBytes(built.spatialGeometries);
    const colorStateBytes = placementStateBytes(bundle);
    const colorAttributeBytes = placementAttributeBytes(built);
    const literalBytes = literalAttributeBytes(built);
    const result = {
        map: id,
        compactMiB: mib(Buffer.byteLength(jsonText, 'utf8')),
        definitions: bundle.definitions.length,
        placements: bundle.placements.length,
        literals: bundle.surfaces.length,
        prepMs: round(prepMs),
        consumerReadyHeapDeltaMiB: mib(ready - before),
        sceneCreationMs: round(sceneMs),
        sceneHeapDeltaMiB: mib(afterScene - ready),
        totalHeapDeltaMiB: mib(afterScene - before),
        sharedSpatialMiB: mib(sharedSpatialBytes),
        placementColorStateMiB: mib(colorStateBytes),
        placementColorAttributeMiB: mib(colorAttributeBytes),
        placementOwnedColorTotalMiB: mib(colorStateBytes + colorAttributeBytes),
        literalAttributeMiB: mib(literalBytes),
        totalUniqueAttributeMiB: mib(sharedSpatialBytes + colorAttributeBytes + literalBytes),
        objectCount: built.placementMeshes.length + built.literalMeshes.length,
        geometryViewCount: built.placementMeshes.length,
        spatialDefinitionGeometryCount: built.spatialGeometries.length,
        parity,
        live,
        pick: pickProof(built),
        noCompatibilityExpansion: true,
        productionReady: parity.mismatchCount === 0 && parity.maxAbsError <= 1e-6
            && live.mismatchCount === 0 && live.maxAbsError <= 1e-6 && live.noLeak
    };
    console.log(`ISSUE765 FINAL ${JSON.stringify(result)}`);
    if (!result.productionReady || !result.pick.hit) throw new Error(`Map ${id}: final direct proof failed.`);
    return result;
}

let stageDir = null;
try {
    stageDir = projectPlay.stageProject({ installRoot, projectRoot });
    const results = [runMap(stageDir, 2), runMap(stageDir, 3)];
    console.log('ISSUE765 FINAL SUMMARY');
    console.log(JSON.stringify(results, null, 2));
} finally {
    projectPlay.cleanupLaunch(stageDir, null);
}
'''.lstrip('\\'))

print('issue #765 production patch applied')
