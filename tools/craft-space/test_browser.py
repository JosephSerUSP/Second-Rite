#!/usr/bin/env python3
"""Execute the generated Craft-space page in the repository's headless Chrome harness."""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_DRIVER = ROOT / "tools" / "golden" / "editor-screens.py"
PAGE = ROOT / "tools" / "craft-space" / "craft-space.html"


def load_chrome_driver():
    spec = importlib.util.spec_from_file_location("second_rite_g6_driver", GOLDEN_DRIVER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load existing Chrome driver: {GOLDEN_DRIVER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    driver = load_chrome_driver()
    chrome = driver.Chrome(
        driver.free_port(), tempfile.mkdtemp(prefix="craft-space-smoke-")
    )
    try:
        chrome.call("Runtime.enable")
        chrome.call("Page.enable")
        chrome.call(
            "Page.addScriptToEvaluateOnNewDocument",
            source="""
                window.__craftSpaceSmoke = { errors: [], rejections: [] };
                window.addEventListener('error', function (event) {
                  window.__craftSpaceSmoke.errors.push(String(event.error || event.message));
                });
                window.addEventListener('unhandledrejection', function (event) {
                  window.__craftSpaceSmoke.rejections.push(String(event.reason));
                });
            """,
        )
        chrome.call("Page.navigate", url=PAGE.as_uri())
        chrome.wait_for("document.readyState === 'complete'", "generated Craft-space page")
        chrome.evaluate(
            "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))",
            await_promise=True,
        )
        result = chrome.evaluate(
            """
            (() => {
              const smoke = window.__craftSpaceSmoke || {};
              if (smoke.errors.length || smoke.rejections.length) {
                throw new Error('page exceptions: ' + JSON.stringify(smoke));
              }
              if (typeof derive !== 'function') throw new Error('live derive() is missing');
              if (!DATA.provenance || !DATA.provenance.dataFingerprint ||
                  DATA.provenance.itemCount !== DATA.items.length ||
                  DATA.provenance.unitCount !== DATA.units.length ||
                  DATA.provenance.deterministic !== true) {
                throw new Error('canonical payload provenance is missing');
              }
              if (!DATA.disciplines.some(d => d.kind)) throw new Error('no discipline populated');
              if (!CRAFTERS.length || !CRAFTERS[0].id) throw new Error('no current crafter populated');
              if (!ITEMS.length || !ITEMS[0].vec || ITEMS[0].why !== 'engine/craft.lua') {
                throw new Error('no current Item projection reached');
              }
              if (!LAST || !LAST.total || !document.querySelector('#byDisc tbody tr')) {
                throw new Error('main analysis render/update path did not complete');
              }
              const direct = derive(DATA.items[0], { overlap: true });
              if (direct.why !== 'engine/craft.lua' || !direct.disciplines.length) {
                throw new Error('engine-backed derive path was not reached');
              }
              return {
                items: DATA.items.length,
                projectedItems: ITEMS.length,
                units: CRAFTERS.length,
                disciplines: DATA.disciplines.length,
                draws: LAST.total,
                provenance: DATA.provenance.dataFingerprint
              };
            })()
            """
        )
        print("CRAFT SPACE BROWSER SMOKE OK: " + str(result))
        return 0
    finally:
        chrome.close()


if __name__ == "__main__":
    raise SystemExit(main())
