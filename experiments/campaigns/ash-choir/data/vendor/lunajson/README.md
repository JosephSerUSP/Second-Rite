# Lunajson vendor note

Thestra vendors source derived from **Lunajson 1.2.3** by Shunsuke Shimizu (`grafi-tt/lunajson`), pinned to upstream tag `1.2.3` / commit `250afac121df831f449d6370ddf406673f6f9c2b`.

Upstream: `https://github.com/grafi-tt/lunajson`

License: MIT; see `LICENSE` in this directory.

`decoder.lua` follows the upstream 1.2.3 decoder contract without an intended semantic patch. It remains vendored locally so exported games have no package-manager or native-library dependency.

`encoder.lua` is derived from the upstream 1.2.3 encoder with one Thestra contract adaptation: object keys are iterated in lexical order so the existing `data.json` deterministic-byte behavior survives the codec replacement. JSON string escaping, number encoding, value/type validation, cycle detection, and array encoding remain codec mechanics rather than Thestra domain semantics.

Thestra policy stays in `data/json.lua`: the legacy `json.decode()` null-as-absence contract, opt-in lossless `json.decodeExact()` / `json.null`, empty object/array identity, and projection of Lua tables (including sparse numeric maps) into JSON object/array shapes. Consumers continue to depend only on `data.json`, never on this vendor directory.
