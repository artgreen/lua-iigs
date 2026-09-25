"""Regression checks for build ownership, cleanup, and public command behavior."""
from contextlib import contextmanager
import json
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from iigsbuild import identified, kits  # noqa: E402
from iigsbuild.common import BuildError  # noqa: E402


class BuildOwnership(unittest.TestCase):
    def test_directory_created_while_waiting_is_never_reused_or_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            destination = parent / "abc-fixed"

            @contextmanager
            def contended_lock(*args):
                # Another invocation finishes while this invocation waits.
                destination.mkdir()
                (destination / "BUILD-MANIFEST.json").write_text("completed evidence")
                yield

            args = types.SimpleNamespace(sdk=None, label=None, configs=["luac"], no_hosts=True)
            with patch.object(identified, "IDENTIFIED", parent), \
                    patch.object(identified, "utc_stamp", return_value="fixed"), \
                    patch.object(identified, "DirLock", contended_lock), \
                    patch.object(identified.Toolchain, "discover"), \
                    patch.object(identified, "Orca"), \
                    patch("iigsbuild.cli.jobs_for", return_value=1), \
                    patch.object(identified, "runtime_inputs", return_value={}), \
                    patch.object(identified, "host_inputs", return_value={}), \
                    patch.object(identified, "build_digest", return_value="abc"), \
                    patch.object(identified, "ConfigBuild", side_effect=BuildError("compile failed")) as build:
                with self.assertRaises(BuildError):
                    identified.identify(args)
            self.assertEqual((destination / "BUILD-MANIFEST.json").read_text(), "completed evidence")
            build.assert_not_called()


class CleanupCoordination(unittest.TestCase):
    def spawn(self, code):
        proc = subprocess.Popen([sys.executable, "-u", "-c", code], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        def stop():
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=10)
        self.addCleanup(stop)
        return proc

    def line(self, proc):
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(timeout=10), "child did not reach synchronization point")
        return proc.stdout.readline().strip()

    def setup_code(self, root):
        return f"""
import sys, types
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'tools')!r})
from iigsbuild import cli, commands, clean
root = Path({str(root)!r})
cli.BUILD = clean.BUILD = root / 'build'
clean.ROOT = root
clean.DEV = root / 'build/dev'
clean.TEST_RUNS = root / 'build/test-runs'
clean.tracked = lambda: set()
"""

    def test_cleanup_waits_for_builds_and_test_sessions(self):
        for command in ("build", "test", "suite", "identify"):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                setup = self.setup_code(root)
                worker = self.spawn(setup + f"""
def active(args):
    for directory in (clean.DEV, clean.TEST_RUNS):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'sentinel').write_text('in use')
    print('ACTIVE', flush=True)
    sys.stdin.readline()
    assert (clean.DEV / 'sentinel').exists()
    assert (clean.TEST_RUNS / 'sentinel').exists()
    return 0
cli.cmd_build = active
commands.HANDLERS[{command!r}] = active
sys.exit(cli.main([{command!r}]))
""")
                self.assertEqual(self.line(worker), "ACTIVE")
                lock = root / "build/.lock"
                inode = lock.stat().st_ino
                cleaner = self.spawn(setup + "sys.exit(cli.main(['clean']))\n")
                self.assertIn("Waiting for another build", self.line(cleaner))
                self.assertTrue((root / "build/dev/sentinel").exists())
                self.assertTrue((root / "build/test-runs/sentinel").exists())
                out, err = worker.communicate(input="\n", timeout=10)
                self.assertEqual(worker.returncode, 0, out + err)
                out, err = cleaner.communicate(timeout=10)
                self.assertEqual(cleaner.returncode, 0, out + err)
                self.assertFalse((root / "build/dev").exists())
                self.assertFalse((root / "build/test-runs").exists())
                self.assertEqual(lock.stat().st_ino, inode)

    def test_new_commands_wait_until_cleanup_finishes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "build/dev").mkdir(parents=True)
            setup = self.setup_code(root)
            cleaner = self.spawn(setup + """
remove = clean.remove_tree
def paused_remove(path):
    print('CLEANING', flush=True)
    sys.stdin.readline()
    remove(path)
clean.remove_tree = paused_remove
sys.exit(cli.main(['clean']))
""")
            self.assertIn("removing", self.line(cleaner))
            # Synchronize via the lock's waiting message, without timed sleeps.
            worker = self.spawn(setup + """
def active(args):
    clean.DEV.mkdir(parents=True)
    (clean.DEV / 'sentinel').write_text('new build')
    return 0
cli.cmd_build = active
sys.exit(cli.main(['build']))
""")
            self.assertIn("Waiting for another build", self.line(worker))
            out, err = cleaner.communicate(input="\n", timeout=10)
            self.assertEqual(cleaner.returncode, 0, out + err)
            out, err = worker.communicate(timeout=10)
            self.assertEqual(worker.returncode, 0, out + err)
            self.assertEqual((root / "build/dev/sentinel").read_text(), "new build")


class KitPreflight(unittest.TestCase):
    def test_none_skips_every_kit_and_records_the_skip(self):
        for kind in kits.NEEDS:
            with self.subTest(kit=kind), tempfile.TemporaryDirectory() as temp:
                args = types.SimpleNamespace(sdk=None, prefix="20:", kit=kind, group="full", preflight="none")
                inputs = {"source": {"kind": "explicit executables"},
                          "bytes": {name: b"executable" for name in kits.NEEDS[kind]}}

                def container(tc, directory, *a, **kw):
                    directory.mkdir()
                    (directory / "TEST.po").write_bytes(b"image")
                    (directory / "TEST.SHK").write_bytes(b"archive")
                    return {}

                # Compact kit driver compilation is preparation, not preflight.
                small = {"title": "Compact kit", "volume": "COMPACT", "exes": {}, "text": {},
                         "binary": {}, "steps": [], "preflight_steps": [kits.Step("run", "luatest", [])],
                         "groups": {}, "readme": [], "expect": "done"}
                with patch.object(kits, "KITS", Path(temp)), \
                        patch("iigsbuild.toolchain.Toolchain.discover"), \
                        patch.object(kits, "executables", return_value=inputs), \
                        patch.object(kits, "small_kit", return_value=small), \
                        patch.object(kits, "build_container", side_effect=container), \
                        patch.object(kits, "preflight", side_effect=AssertionError("preflight ran")) as preflight:
                    self.assertEqual(kits.hardware_suite(args), 0)
                preflight.assert_not_called()
                manifest = next(Path(temp).glob("*/package/KIT-MANIFEST.json"))
                self.assertEqual(json.loads(manifest.read_text())["preflight"], "skipped")


class LegacyForwarding(unittest.TestCase):
    def test_existing_legacy_executables_still_forward(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / "src"
            src.mkdir()
            (src / "Makefile").write_bytes((ROOT / "src/Makefile").read_bytes())
            targets = ("lua", "luac", "liblua", "all", "clean")
            (root / "Makefile").write_text(".PHONY: " + " ".join(targets) + "\n" +
                                           "\n".join(f"{n}:\n\t@echo FORWARDED-{n}" for n in targets) + "\n")
            for target in targets:
                (src / target).write_text("legacy output")
                result = subprocess.run(["make", "-C", str(src), target], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("FORWARDED-" + target, result.stdout)


if __name__ == "__main__":
    unittest.main()
