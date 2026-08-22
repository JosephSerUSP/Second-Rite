/*
 * Shared executable semantic authority for sprite FILE resolution.
 *
 * `sprite-timing.ts` owns what a resolved sprite's tokens mean. This leaf owns
 * the step before it: given a sprite key, which file on disk is that key?
 *
 * That question used to be answerable only by LÖVE, so Thestra Studio asked the
 * runtime — one cold subprocess per sprite, ~3.5-4.8 s each, to parse a
 * filename (#794). The reason it had to ask was never the filesystem: it was
 * that the ORDERING rules lived exclusively in `presentation/sprite_sheet.lua`.
 *
 * So the rules move here and the I/O does not. A host supplies its own
 * directory inventory and its own existence check; this module owns:
 *
 *   - the fixed candidate path list built from a file key, and its order;
 *   - the lookup index built from an inventory, including first-match-wins;
 *   - how an indexed hit contributes its filename tokens.
 *
 * Both hosts therefore agree on which file a key means, by construction rather
 * than by one of them asking the other.
 */
namespace ThestraSpriteResolutionSemantics {
    export interface InventoryEntry {
        /** Directory this file was listed under, e.g. "assets/smallBattlers". */
        dir: string;
        /** File name including extension, e.g. "pixie[fps=15].png". */
        name: string;
    }

    export interface IndexedFile {
        path: string;
        /** Stem tokens, already parsed by the caller's sprite-timing leaf. */
        stem: string;
    }

    export interface FileIndex {
        [lowerFileKey: string]: IndexedFile;
    }

    /**
     * Directories are searched in this order and the list is part of the
     * contract: the first matching stripped basename wins, so reordering these
     * silently changes which file an ambiguous key resolves to.
     */
    export const ASSET_DIRS: string[] = [
        'assets/smallBattlers',
        'assets/sprites',
        'assets/system',
    ];

    function isPng(name: string): boolean {
        const lower = name.toLowerCase();
        return lower.length > 4 && lower.substring(lower.length - 4) === '.png';
    }

    function stripPng(name: string): string {
        return name.substring(0, name.length - 4);
    }

    /** Lua's `s:sub(1,1):upper() .. s:sub(2):lower()`, without a locale. */
    function capitalizedAscii(value: string): string {
        if (value.length === 0) return value;
        return value.substring(0, 1).toUpperCase() + value.substring(1).toLowerCase();
    }

    /**
     * The fixed candidate list for a file key, in probe order. A host tries
     * each in turn and takes the first that exists.
     *
     * The order encodes history: smallBattlers is probed with three case
     * spellings before sprites and system are consulted at all, so a battler
     * named in any casing keeps resolving to the battler rather than to a
     * same-named system sprite.
     */
    export function candidatePaths(fileKey: string): string[] {
        return [
            'assets/smallBattlers/' + capitalizedAscii(fileKey) + '.png',
            'assets/smallBattlers/' + fileKey + '.png',
            'assets/smallBattlers/' + fileKey.toLowerCase() + '.png',
            'assets/sprites/' + fileKey + '.png',
            'assets/system/' + fileKey + '.png',
            'assets/system/' + capitalizedAscii(fileKey) + '.png',
        ];
    }

    /**
     * Build the stripped-basename lookup index from a host-supplied inventory.
     *
     * `entries` must already be in the host's directory order, and within a
     * directory in the host's own listing order, because first-match-wins is
     * the historical contract. Non-PNG entries are ignored.
     *
     * The caller passes `fileKeyOf`, which strips `[k=v]` tokens from a stem —
     * that is the sprite-timing leaf's `parseKey().fileKey`. Keeping it a
     * parameter is what stops this leaf from duplicating the token grammar.
     */
    export function buildFileIndex(
        entries: InventoryEntry[],
        fileKeyOf: (stem: string) => string
    ): FileIndex {
        const index: FileIndex = {};
        for (let i = 0; i < entries.length; i++) {
            const entry = entries[i];
            if (!entry || !isPng(entry.name)) continue;
            const stem = stripPng(entry.name);
            const base = fileKeyOf(stem).toLowerCase();
            // First match wins: a later directory never displaces an earlier one.
            //
            // Deliberately `!== undefined` rather than a hasOwnProperty guard:
            // this source compiles to Lua as well as JavaScript, and `Object`
            // does not exist in the Lua target. A JS-only idiom here generates
            // Lua that throws `attempt to index global 'Object'` the first time
            // a sprite is resolved.
            if (index[base] !== undefined) continue;
            index[base] = { path: entry.dir + '/' + entry.name, stem: stem };
        }
        return index;
    }

    /**
     * The full ordered probe list for a key: the fixed candidates, then the
     * indexed hit if there is one. An indexed path goes LAST so an exact
     * conventional filename always beats a token-carrying variant.
     */
    export function probeOrder(fileKey: string, index: FileIndex): string[] {
        const paths = candidatePaths(fileKey);
        const indexed = index ? index[fileKey.toLowerCase()] : undefined;
        if (indexed) paths[paths.length] = indexed.path;
        return paths;
    }

    /** The indexed entry for a key, or null. Hosts read `stem` for filename tokens. */
    export function indexedFor(fileKey: string, index: FileIndex): IndexedFile | null {
        if (!index) return null;
        const hit = index[fileKey.toLowerCase()];
        return hit === undefined ? null : hit;
    }
}
