# Stratum III — São Paulo Metro

This Project composition uses the engine's generic authored path-mover primitive. Each train is an ordinary Map Event; route, footprint, boarding ports, speed/dwell and visual states live in Project data.

Blue includes Jabaquara, Santa Cruz, Paraíso, Sé and Luz. Green carries the Chácara Klabin gate; Red contains the Brás power/key sequence; Yellow contains the Faria Lima vault and Master Pass; Lilac contains terminal access, the boss and emergency return.

The engine primitive names no metro asset, rail material, route axis, consist offset or platform side. A raft, elevator or moving platform can use the same contract with different authored data.

Metro OBJ/MTL runtime products are reproducible from `tools/generate_metro_train_models.py`. This note describes design only; verification status belongs to CI/PR records.
