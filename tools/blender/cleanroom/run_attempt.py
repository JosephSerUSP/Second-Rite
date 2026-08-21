"""Blender entrypoint: python -m style runner for one attempt."""
import importlib
import sys


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    attempt_id, out_dir = argv[0], argv[1]
    mod = importlib.import_module("cleanroom.attempts.a%s" % attempt_id)
    mod.build(out_dir, attempt_id=attempt_id)


if __name__ == "__main__":
    main()
