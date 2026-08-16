from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_exact(path, old, new, expected=1):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old[:140]!r}")
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"updated {path}: {count} replacement(s)")


# Pure stale-completion guard used by the workspace. A late completion from an
# older map/inspection request cannot make a newer request look ready.
replace_exact(
    "tools/editor/js/thestra-workspace-state.js",
    '''    // The workspace can continue authoring semantically whether the optional\n    // runtime bridge is absent, rejects this origin, or reports a compile\n    // failure. Keep that rendered state deterministic; the detailed cause is\n    // preserved as the toolbar status tooltip by the workspace host.\n    function fallbackStatusLabel() { return 'runtime unavailable · fallback'; }\n\n    return { transitionPlan, mutationPlan, fallbackStatusLabel };\n''',
    '''    // Full map/inspection refreshes have two independently useful moments:\n    // semantic geometry is available early, while runtime-authoritative geometry\n    // catches up later. Capture/tests need to know when the LATEST full refresh\n    // has reached that second moment. A token prevents an older async completion\n    // from certifying a newer request as settled.\n    function createReadiness() {\n        let requested = 0;\n        let settled = 0;\n        return Object.freeze({\n            begin() { requested += 1; return requested; },\n            settle(token) {\n                if (token === requested) settled = token;\n                return requested > 0 && settled === requested;\n            },\n            isSettled() { return requested > 0 && settled === requested; },\n            snapshot() { return { requested, settled }; }\n        });\n    }\n\n    // The workspace can continue authoring semantically whether the optional\n    // runtime bridge is absent, rejects this origin, or reports a compile\n    // failure. Keep that rendered state deterministic; the detailed cause is\n    // preserved as the toolbar status tooltip by the workspace host.\n    function fallbackStatusLabel() { return 'runtime unavailable · fallback'; }\n\n    return { transitionPlan, mutationPlan, fallbackStatusLabel, createReadiness };\n'''
)

replace_exact(
    "tools/editor/tests/test-thestra-workspace-state.js",
    '''(function testFallbackStatusDoesNotDependOnBridgeAvailability() {\n    assert.strictEqual(WorkspaceState.fallbackStatusLabel(), 'runtime unavailable · fallback');\n})();\n\nconsole.log('Thestra workspace transition/invalidation tests OK');\n''',
    '''(function testLatestFullRefreshOwnsReadiness() {\n    const readiness = WorkspaceState.createReadiness();\n    assert.strictEqual(readiness.isSettled(), false, 'no request is never a ready workspace');\n\n    const first = readiness.begin();\n    assert.deepStrictEqual(readiness.snapshot(), { requested: first, settled: 0 });\n    const second = readiness.begin();\n    assert.strictEqual(readiness.isSettled(), false, 'newer work invalidates prior readiness immediately');\n\n    assert.strictEqual(readiness.settle(first), false,\n        'a stale async completion cannot certify the newer refresh');\n    assert.deepStrictEqual(readiness.snapshot(), { requested: second, settled: 0 });\n\n    assert.strictEqual(readiness.settle(second), true, 'the latest completion settles the workspace');\n    assert.strictEqual(readiness.isSettled(), true);\n\n    readiness.begin();\n    assert.strictEqual(readiness.isSettled(), false,\n        'starting another map/inspection refresh makes readiness false synchronously');\n})();\n\n(function testFallbackStatusDoesNotDependOnBridgeAvailability() {\n    assert.strictEqual(WorkspaceState.fallbackStatusLabel(), 'runtime unavailable · fallback');\n})();\n\nconsole.log('Thestra workspace transition/invalidation tests OK');\n'''
)

# Invisible DOM readiness state: G6 can observe production lifecycle without
# inventing its own timing guesses. Preserve refreshAll's early semantic return;
# only the sidecar readiness flag waits for authoritative geometry/fallback.
replace_exact(
    "tools/editor/js/thestra-editor-workspace.js",
    '''    let bundleTimer = null;\n    let loadedMapIndex = null;\n    let bundleStatus = 'runtime geometry';\n''',
    '''    let bundleTimer = null;\n    let loadedMapIndex = null;\n    let bundleStatus = 'runtime geometry';\n    const workspaceReadiness = WorkspaceState.createReadiness();\n'''
)

replace_exact(
    "tools/editor/js/thestra-editor-workspace.js",
    '''    async function refreshAll(options) {\n        options = options || {};\n        await refreshSemanticScene({ clearBundle: !!options.clearBundle });\n        // Runtime authority catches up independently. The semantic viewport is\n        // already usable when this function resolves.\n        refreshAuthoritativeBundle({ clearFirst: false }).catch(console.error);\n    }\n''',
    '''    async function refreshAll(options) {\n        options = options || {};\n        const readinessToken = workspaceReadiness.begin();\n        // Nonvisual lifecycle evidence. `0` is written before the first await,\n        // so a stale runtime-geometry label from the previous Map can never be\n        // mistaken for completion of this refresh.\n        status.dataset.workspaceReady = '0';\n        status.dataset.workspaceRevision = String(readinessToken);\n\n        await refreshSemanticScene({ clearBundle: !!options.clearBundle });\n        // Runtime authority still catches up independently: callers retain the\n        // existing early semantic return. The readiness sidecar settles only\n        // after the latest authoritative bundle (or explicit fallback) has been\n        // installed. Older async completions are ignored by the token guard.\n        refreshAuthoritativeBundle({ clearFirst: false }).then(() => {\n            if (workspaceReadiness.settle(readinessToken)) {\n                status.dataset.workspaceReady = '1';\n                status.dataset.workspaceRevision = String(readinessToken);\n            }\n        }).catch(console.error);\n    }\n'''
)

# G6 waits on lifecycle state before every independent action, before a
# user-facing post-ready action, and immediately before settling pixels. That
# catches both reset loadActiveMap() and step-triggered map/inspection refreshes.
replace_exact(
    "tools/golden/editor-screens-core.py",
    '''PENDING_IMAGES_JS = """\n(function () {\n    var pending = Array.prototype.slice.call(document.images)\n        .filter(function (i) { return !i.complete; }).length;\n    if (document.fonts && document.fonts.status !== 'loaded') pending += 1;\n    return pending;\n})()\n"""\n\n\n# ---------------------------------------------------------------------------\n''',
    '''PENDING_IMAGES_JS = """\n(function () {\n    var pending = Array.prototype.slice.call(document.images)\n        .filter(function (i) { return !i.complete; }).length;\n    if (document.fonts && document.fonts.status !== 'loaded') pending += 1;\n    return pending;\n})()\n"""\n\n# A stable screenshot is not necessarily a ready screenshot: the 3D Map\n# workspace intentionally exposes semantic fallback before the runtime bundle\n# finishes compiling. #683 caught docs-only candidates photographing that\n# previous/staging state. The workspace publishes an invisible revision guard;\n# wait for the latest full map/inspection refresh rather than a clock or text.\nWORKSPACE_READY_JS = """\n(function () {\n    var status = document.getElementById('thestra-map-view-status');\n    return !!status && status.dataset.workspaceReady === '1';\n})()\n"""\n\n\n# ---------------------------------------------------------------------------\n'''
)

replace_exact(
    "tools/golden/editor-screens-core.py",
    '''            chrome.evaluate(RESET_JS, await_promise=True)\n            chrome.evaluate("(function(){%s})()" % step["js"], await_promise=False)\n            if step.get("wait"):\n                chrome.wait_for(step["wait"], step["path"])\n            if step.get("after_wait"):\n                chrome.evaluate("(function(){%s})()" % step["after_wait"],\n                                await_promise=False)\n''',
    '''            chrome.evaluate(RESET_JS, await_promise=True)\n            chrome.wait_for(WORKSPACE_READY_JS, step["path"] + " reset workspace")\n            chrome.evaluate("(function(){%s})()" % step["js"], await_promise=False)\n            if step.get("wait"):\n                chrome.wait_for(step["wait"], step["path"])\n            if step.get("after_wait"):\n                # A step may have called loadActiveMap()/resolveMapInspection().\n                # Do not perform its user-facing follow-up against stale scene\n                # geometry just because the step-specific DOM text is ready.\n                chrome.wait_for(WORKSPACE_READY_JS, step["path"] + " before post-ready action")\n                chrome.evaluate("(function(){%s})()" % step["after_wait"],\n                                await_promise=False)\n'''
)

replace_exact(
    "tools/golden/editor-screens-core.py",
    '''                if post_wait:\n                    chrome.wait_for(post_wait, step["path"] + " after post-ready action")\n            chrome.evaluate(SETTLE_JS, await_promise=True)\n            captures.append({"path": step["path"],\n''',
    '''                if post_wait:\n                    chrome.wait_for(post_wait, step["path"] + " after post-ready action")\n            # Follow-up actions may themselves trigger a full inspection/map\n            # refresh. Require the latest revision immediately before pixel\n            # settling, so two identical premature frames cannot certify it.\n            chrome.wait_for(WORKSPACE_READY_JS, step["path"] + " workspace refresh")\n            chrome.evaluate(SETTLE_JS, await_promise=True)\n            captures.append({"path": step["path"],\n'''
)

replace_exact(
    "tools/golden/test-g6-harness-boundaries.py",
    '''assert "class HarnessStall" in g6\nassert "raise HarnessStall(what, expression, last)" in g6\nassert 'print("G6 HARNESS STALL"' in g6\nassert "raise SystemExit(2)" in g6\n''',
    '''assert "class HarnessStall" in g6\nassert "raise HarnessStall(what, expression, last)" in g6\nassert 'print("G6 HARNESS STALL"' in g6\nassert "raise SystemExit(2)" in g6\n\n# #683: the Map workspace can be pixel-stable while an async authoritative\n# bundle still belongs to the previous Map. Capture must use the production\n# revision guard both around reset and after step-triggered refreshes.\nassert "workspaceReadiness = WorkspaceState.createReadiness()" in workspace\nassert "status.dataset.workspaceReady = '0'" in workspace\nassert "status.dataset.workspaceReady = '1'" in workspace\nassert "WORKSPACE_READY_JS" in g6\nassert g6.count("chrome.wait_for(WORKSPACE_READY_JS") >= 3\n'''
)

print("#683 workspace readiness patch prepared")
