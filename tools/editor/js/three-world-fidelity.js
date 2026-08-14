import * as THREE from 'three';
import '/js/three-world-fidelity-core.js';

const Fidelity = globalThis.ThestraThreeWorldFidelityCore;
if (!Fidelity) {
    throw new Error('Thestra Three world fidelity core failed to load.');
}

// #475: world renderable vertex RGB already contains the resolved static-light
// modulation. Three's Hemisphere/Directional lights are useful for editor-only
// gizmos and preview objects, but applying them to those world materials lights
// the environment a second time and makes Studio systematically brighter than
// runtime. Patch only the exact resolved-world material signature used by the
// authoritative bundle path; texture sampling, sRGB conversion, alpha and
// emission remain Three's normal MeshStandardMaterial plumbing.
Fidelity.install(THREE);
