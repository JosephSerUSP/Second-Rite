# Lunajson vendor note

Thestra vendors the decoder and encoder from **Lunajson 1.2.3** by Shunsuke Shimizu (`grafi-tt/lunajson`), pinned to upstream tag `1.2.3` / commit `250afac121df831f449d6370ddf406673f6f9c2b`.

Upstream: `https://github.com/grafi-tt/lunajson`

License: MIT; see `LICENSE` in this directory.

`decoder.lua` is the upstream 1.2.3 source unchanged.

`encoder.lua` carries one intentionally narrow Thestra patch: object keys are iterated in lexical order so the existing `data.json` deterministic-byte behavior survives the codec replacement. JSON grammar, string escaping, number encoding, type validation, cycle detection, and array encoding remain Lunajson-owned.

Thestra policy stays in `data/json.lua`: explicit null identity, empty object/array identity, and projection of Lua tables (including sparse numeric maps) into JSON object/array shapes. Consumers continue to depend only on `data.json`, never on this vendor directory.
