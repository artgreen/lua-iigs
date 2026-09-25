"""Remove disposable development outputs; preserve builds, reports, and releases."""
from .common import BUILD, DEV, TEST_RUNS, DirLock, rel, remove_tree, say


def clean(args):
    with DirLock(BUILD, "clean"):
        for path in (DEV, TEST_RUNS):
            if path.exists():
                say(("would remove " if args.dry_run else "removing ") + rel(path))
                if not args.dry_run:
                    remove_tree(path)
    return 0
