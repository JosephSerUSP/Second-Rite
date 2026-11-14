#!/usr/bin/env bash
# park_worktrees.sh: put Hichaukitoden into its dormant state without losing work.
#
# Written 2026-11-13 when the project went dormant (see DORMANT.md at the repo root).
#
# For every git worktree except the primary checkout:
#   1. If HEAD is on a branch, push that branch to origin (creates it if missing).
#      If HEAD is detached and no origin branch contains it, push it as
#      parking/<worktree-name> so the commit stays reachable.
#   2. If the worktree has uncommitted work, copy it aside to
#      $PARK_DIR/<worktree-name>/ : `tracked.patch` (git diff HEAD, binary-safe),
#      every modified and untracked file at its repo path under files/, and
#      MANIFEST.txt (branch, HEAD, origin URL, file list). Large generated art is
#      kept on disk here rather than pushed to GitHub.
#      Worktrees whose only changes are deletions (sparse scratch copies) need no copy.
#   3. Remove the worktree (`git worktree remove --force`) only after steps 1-2
#      succeeded; on any failure the worktree is left in place and reported.
#
# Usage (from the repo root):
#   bash tools/dormancy/park_worktrees.sh            # dry run: prints the plan
#   bash tools/dormancy/park_worktrees.sh --apply    # does it
# Env: PARK_DIR (default D:/Antigravity/Hichaukitoden-parked)
# With --main, also parks the primary checkout's uncommitted work the same way and
# then restores it to a clean HEAD (only after the copy is verified).
set -u
APPLY=0; DO_MAIN=0
for a in "$@"; do case "$a" in --apply) APPLY=1;; --main) DO_MAIN=1;; esac; done
PARK_DIR="${PARK_DIR:-D:/Antigravity/Hichaukitoden-parked}"
ROOT="$(git rev-parse --show-toplevel)"
LOG="$PARK_DIR/park-log.txt"
[ "$APPLY" = 1 ] && mkdir -p "$PARK_DIR"
say() { echo "$*"; [ "$APPLY" = 1 ] && echo "$*" >> "$LOG"; }

save_dirty() { # $1 worktree path, $2 name -> 0 ok
  local w="$1" name="$2" dest="$PARK_DIR/$2"
  local files; files="$(git -C "$w" status --porcelain -z --untracked-files=all | tr '\0' '\n' | grep -v '^ D \|^D  ' | cut -c4- | grep -v '^$')"
  if [ -z "$files" ]; then say "  only deletions; nothing to copy"; return 0; fi
  local n; n=$(printf '%s\n' "$files" | wc -l)
  say "  copy $n changed/untracked files -> $dest"
  [ "$APPLY" = 1 ] || return 0
  mkdir -p "$dest/files" || return 1
  git -C "$w" diff --binary HEAD > "$dest/tracked.patch" || return 1
  { echo "worktree: $w"; echo "branch: $(git -C "$w" branch --show-current)"; echo "head: $(git -C "$w" rev-parse HEAD)";
    echo "origin: $(git -C "$w" remote get-url origin)"; echo "parked: $(date -Iseconds)"; echo "files:"; printf '%s\n' "$files"; } > "$dest/MANIFEST.txt"
  local bad=0
  while IFS= read -r f; do
    [ -e "$w/$f" ] || continue
    mkdir -p "$dest/files/$(dirname "$f")" && cp -p "$w/$f" "$dest/files/$f" || bad=1
    cmp -s "$w/$f" "$dest/files/$f" || bad=1
  done <<< "$files"
  [ "$bad" = 0 ] || say "  COPY VERIFY FAILED"
  return $bad
}

push_head() { # $1 worktree path, $2 name -> 0 ok
  local w="$1" name="$2" b; b="$(git -C "$w" branch --show-current)"
  if [ -n "$b" ]; then
    if git -C "$w" rev-parse -q --verify "origin/$b" >/dev/null && [ "$(git -C "$w" rev-list --count "origin/$b..$b")" = 0 ]; then
      say "  branch $b already on origin"; return 0; fi
    say "  push branch $b"
    [ "$APPLY" = 1 ] || return 0
    git -C "$w" push -q origin "$b:refs/heads/$b" >> "$LOG" 2>&1
  else
    if [ -n "$(git -C "$w" branch -r --contains HEAD 2>/dev/null | head -1)" ]; then say "  detached HEAD already on origin"; return 0; fi
    say "  push detached HEAD as parking/$name"
    [ "$APPLY" = 1 ] || return 0
    git -C "$w" push -q origin "HEAD:refs/heads/parking/$name" >> "$LOG" 2>&1
  fi
}

git -C "$ROOT" worktree list --porcelain | grep '^worktree ' | cut -d' ' -f2- | while IFS= read -r w; do
  [ "$w" = "$ROOT" ] && continue
  name="$(basename "$w")"; [ "$name" = prev ] || [ "$name" = g5prev ] && name="$(basename "$(dirname "$(dirname "$w")")")-$name"
  say "== $name ($w)"
  if [ ! -d "$w" ]; then say "  missing on disk; prune"; [ "$APPLY" = 1 ] && git -C "$ROOT" worktree prune; continue; fi
  if push_head "$w" "$name" && save_dirty "$w" "$name"; then
    say "  remove worktree"
    [ "$APPLY" = 1 ] && { git -C "$ROOT" worktree remove --force "$w" >> "$LOG" 2>&1 || say "  REMOVE FAILED"; }
  else
    say "  KEPT: push or copy failed"
  fi
done

if [ "$DO_MAIN" = 1 ]; then
  say "== primary checkout ($ROOT)"
  if save_dirty "$ROOT" "main-checkout"; then
    say "  restore clean HEAD"
    [ "$APPLY" = 1 ] && { git -C "$ROOT" checkout -- . && git -C "$ROOT" clean -fdq; }
  else say "  KEPT: copy failed"; fi
fi
[ "$APPLY" = 1 ] && git -C "$ROOT" worktree prune
