(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory(require('./generated/world-view.js'));
    } else root.ThestraCompositionAuthoring = factory(root.ThestraWorldViewSemantics);
}(typeof globalThis !== 'undefined' ? globalThis : this, function (semantics) {
    'use strict';
    if (!semantics) throw new Error('Plate composition requires generated shared world-view semantics.');
    return semantics;
}));
