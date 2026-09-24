"""Subcommands beyond building, registered into the CLI."""
from __future__ import annotations

from pathlib import Path

from .common import say

HANDLERS = {}


def handler(name):
    def wrap(fn):
        HANDLERS[name] = fn
        return fn
    return wrap


def register(sub) -> None:
    p = sub.add_parser("identify", help="identified build of every configuration")
    p.add_argument("--label", help="banner prefix (default 'IIgs <build id>'); variant word is appended")
    p.add_argument("--configs", nargs="*", help="subset of configurations (default: all)")
    p.add_argument("--no-hosts", action="store_true")
    p.add_argument("--compare-release", type=Path, help="release directory to compare executable hashes with")

    p = sub.add_parser("test", help="local regression checks")
    p.add_argument("--build", help="identified build (id prefix or directory); default: dev builds")
    p.add_argument("--config", default="lua", choices=["lua", "lua-small", "luatrace"])
    p.add_argument("--checks", nargs="*", help="unit targeted luac compact hosts trace")
    p.add_argument("--timeout", type=int, default=900, help="per-process local limit (s); not a hardware limit")

    p = sub.add_parser("suite", help="run the reusable Lua suite locally")
    p.add_argument("--build")
    p.add_argument("--config", default="lua", choices=["lua", "luatrace"])
    p.add_argument("--exe", type=Path, help="explicit existing executable (never rebuilt)")
    p.add_argument("--group", default="runtime")
    p.add_argument("--timeout", type=int, default=1800)

    p = sub.add_parser("package", help="verified .po/.SHK packages from an identified build")
    p.add_argument("--build", required=False)
    p.add_argument("--kinds", nargs="*")
    p.add_argument("--report", help="test report.json to reference in the package manifest")

    p = sub.add_parser("hardware-suite", help="TEST.SHK kit for real-hardware testing")
    p.add_argument("--build")
    p.add_argument("--release", type=Path)
    p.add_argument("--exe", nargs="*", help="explicit executables as name=path (lua, luac, luasmall, iigshost)")
    p.add_argument("--kit", default="suite", choices=["suite", "small", "luac", "host"])
    p.add_argument("--group", default="full")
    p.add_argument("--prefix", default="20:")
    p.add_argument("--preflight", default=None,
                   help="suite group to preflight in GoldenGate (default runtime; 'none' to skip)")

    p = sub.add_parser("stage", help="copy verified containers to a transfer directory")
    p.add_argument("--from", dest="source", required=True, type=Path)
    p.add_argument("--dest", required=True, type=Path)
    p.add_argument("--replace", action="store_true")

    p = sub.add_parser("clean", help="remove disposable outputs")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("clean-legacy", help="archive legacy loose outputs")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("sizes", help="measured size of each configuration")
    p.add_argument("--build")

    sub.add_parser("test-build", help="build-system integration tests")
    p = sub.add_parser("kit", help="identify + test + package")
    p.add_argument("--label")


@handler("identify")
def _identify(args) -> int:
    from .identified import IdentifiedBuild, compare_release, identify
    from .common import write_json
    directory = identify(args)
    if args.compare_release:
        build = IdentifiedBuild(directory)
        result = compare_release(build, args.compare_release.resolve())
        out = directory.parent / (directory.name + ".release-comparison.json")
        write_json(out, result)
        for name, row in result["executables"].items():
            say(f"  {name:9} {'IDENTICAL to' if row['identical'] else 'differs from'} release {result['release']}")
    return 0


@handler("test")
def _test(args) -> int:
    from .runtests import run_tests
    return run_tests(args)


@handler("suite")
def _suite(args) -> int:
    from .suite import run_suite
    return run_suite(args)


@handler("package")
def _package(args) -> int:
    from .packages import package
    return package(args)


@handler("hardware-suite")
def _hardware_suite(args) -> int:
    from .kits import hardware_suite
    return hardware_suite(args)


@handler("stage")
def _stage(args) -> int:
    from .stage import stage
    return stage(args)


@handler("clean")
def _clean(args) -> int:
    from .clean import clean
    return clean(args)


@handler("clean-legacy")
def _clean_legacy(args) -> int:
    from .clean import clean_legacy
    return clean_legacy(args)


@handler("sizes")
def _sizes(args) -> int:
    """Measured executable/library sizes and compact-runtime savings."""
    from .common import DEV, rel, sha256_file
    from .configs import CONFIGS, PARSER_SYMBOLS
    from .orca import link_symbols
    if args.build:
        from .identified import resolve
        root = resolve(args.build).dir
    else:
        root = DEV
    sizes = {}
    say(f"Sizes in {rel(root)}:")
    for cfg in CONFIGS.values():
        for product in filter(None, (cfg.exe, cfg.lib)):
            path = root / cfg.name / "out" / product
            if path.is_file():
                sizes[product] = path.stat().st_size
                extra = ""
                if product == cfg.exe and (root / cfg.name / "out" / (product + ".map")).is_file():
                    symbols = link_symbols((root / cfg.name / "out" / (product + ".map")).read_text(errors="replace"))
                    present = [s for s in PARSER_SYMBOLS if s in symbols]
                    extra = f"  parser symbols linked: {len(present)}/{len(PARSER_SYMBOLS)}"
                say(f"  {cfg.name + '/' + product:26} {sizes[product]:>9,} bytes{extra}")
    for full, small in (("lua", "luasmall"), ("lua.lib", "luasmall.lib")):
        if full in sizes and small in sizes:
            saved = sizes[full] - sizes[small]
            say(f"  compact saving {small:13} {saved:>9,} bytes ({100 * saved / sizes[full]:.1f}% of {full})")
    return 0


@handler("kit")
def _kit(args) -> int:
    """identify -> test the identified build -> package it with the report."""
    from .identified import IdentifiedBuild, identify
    ns = type("Args", (), {"sdk": args.sdk, "label": args.label, "configs": None, "no_hosts": False})
    directory = identify(ns)
    build = IdentifiedBuild(directory)
    from .runtests import run_tests
    tests = type("Args", (), {"sdk": args.sdk, "build": str(directory), "config": "lua", "checks": None,
                              "timeout": 900})
    if run_tests(tests):
        say("Tests failed; not packaging. The identified build is kept for investigation.")
        return 1
    report = tests.report_path
    tests.checks = ["trace"]
    if run_tests(tests):
        say("Traced tests failed; not packaging.")
        return 1
    from .packages import package
    return package(type("Args", (), {"sdk": args.sdk, "build": str(build.dir), "kinds": None,
                                     "report": str(report)}))


@handler("test-build")
def _test_build(args) -> int:
    from .selftest import main
    return main(args)
