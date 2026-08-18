(function (root, factory) {
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
