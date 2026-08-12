1. Dangling References
The following asset reference points to a file that does not exist on disk:
- `data/commonEvents.json:47` references `assets/sprites/OBJ_Statue_001.png`

2. Orphaned Assets
The following files exist under `assets/` but are not referenced anywhere in `data/`, `engine/`, `presentation/`, or `tools/`:
- assets/models/gothic/
- assets/models/town/
