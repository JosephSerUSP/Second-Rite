(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else root.ThestraMapHierarchy = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';

    function idKey(id) {
        return id === undefined || id === null || id === '' ? null : String(id);
    }

    function findMapById(maps, id) {
        const key = idKey(id);
        if (key === null) return null;
        return (maps || []).find(map => idKey(map && map.id) === key) || null;
    }

    function wouldCreateCycle(maps, mapId, proposedParentId) {
        const mapKey = idKey(mapId);
        let currentKey = idKey(proposedParentId);
        if (currentKey === null) return false;

        const byId = new Map();
        (maps || []).forEach(map => {
            const key = idKey(map && map.id);
            if (key !== null && !byId.has(key)) byId.set(key, map);
        });

        const visited = new Set();
        while (currentKey !== null) {
            if (currentKey === mapKey || visited.has(currentKey)) return true;
            visited.add(currentKey);
            const current = byId.get(currentKey);
            if (!current) return false;
            currentKey = idKey(current.parentMapId);
        }
        return false;
    }

    function validParentMaps(maps, mapId) {
        const ownKey = idKey(mapId);
        return (maps || []).filter(map => {
            const candidateKey = idKey(map && map.id);
            return candidateKey !== null
                && candidateKey !== ownKey
                && !wouldCreateCycle(maps, mapId, map.id);
        });
    }

    function buildForest(maps, getCategory) {
        const list = Array.isArray(maps) ? maps : [];
        const nodes = list.map((map, index) => ({
            map,
            index,
            children: [],
            problem: null,
            attached: false,
        }));

        const byId = new Map();
        const idCounts = new Map();
        nodes.forEach(node => {
            const key = idKey(node.map && node.map.id);
            if (key === null) return;
            idCounts.set(key, (idCounts.get(key) || 0) + 1);
            if (!byId.has(key)) byId.set(key, node);
        });

        nodes.forEach(node => {
            const map = node.map || {};
            const ownKey = idKey(map.id);
            const parentKey = idKey(map.parentMapId);
            if (ownKey !== null && idCounts.get(ownKey) > 1) {
                node.problem = `Duplicate map id ${map.id}; hierarchy parentage is ambiguous.`;
                return;
            }
            if (parentKey === null) return;
            if ((idCounts.get(parentKey) || 0) > 1) {
                node.problem = `Parent map id ${map.parentMapId} is duplicated.`;
                return;
            }
            const parent = byId.get(parentKey);
            if (!parent) {
                node.problem = `Parent map ${map.parentMapId} does not exist.`;
                return;
            }
            if (wouldCreateCycle(list, map.id, parent.map.id)) {
                node.problem = 'Parent relationship forms a cycle.';
                return;
            }
            parent.children.push(node);
            node.attached = true;
        });

        const rootsByCategory = Object.create(null);
        nodes.forEach(node => {
            if (node.attached) return;
            const category = getCategory
                ? String(getCategory(node.map, node.index))
                : String((node.map && node.map.category) || 'uncategorized');
            if (!rootsByCategory[category]) rootsByCategory[category] = [];
            rootsByCategory[category].push(node);
        });

        return { nodes, rootsByCategory };
    }

    return {
        idKey,
        findMapById,
        wouldCreateCycle,
        validParentMaps,
        buildForest,
    };
});
