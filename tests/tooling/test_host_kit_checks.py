"""Reject misleading native-host output before reporting a hardware pass."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from iigsbuild.common import BuildError  # noqa: E402
from iigsbuild.kits import host_batch  # noqa: E402


class HostKitChecks(unittest.TestCase):
    def test_batch_preserves_native_exit_status(self):
        script = host_batch()
        self.assertNotIn(";", script)
        self.assertIn("20:iigshost >host.out >&host.err\nset hoststatus {status}\nset exit on\n", script)
        self.assertIn("20:luatest -E test.lua verify {hoststatus}\n20:luatest -E test.lua finish", script)
        self.assertNotIn("20:", host_batch("15:"))
        with self.assertRaises(BuildError):
            host_batch("20:;exit")

    @unittest.skipUnless(os.environ.get("TEST_LUA"), "set TEST_LUA for IIgs verifier checks")
    def test_verifier_requires_status_marker_and_clean_output(self):
        parent = ROOT / "build/test-runs"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            stage = Path(temp)
            (stage / "test.lua").write_bytes((ROOT / "tests/hardware/hostcheck.lua").read_bytes())
            command = [os.environ.get("IIX", "iix"), "--memcheck", str(Path(os.environ["TEST_LUA"]).resolve()), "-E", "test.lua"]
            def invoke(*args):
                return subprocess.run(command + list(args), cwd=stage, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            good = "IIGSHOST PASSED yields=100\r"
            cases = [
                (good, "", "1", "native host returned nonzero status"),
                ("NOT IIGSHOST PASSED yields=100\n", "", "0", "missing/invalid native C-hook completion"),
                (good + good, "", "0", "missing/invalid native C-hook completion"),
                ("IIGSHOST PASSED yields=1\n", "", "0", "missing/invalid native C-hook completion"),
                ("IIGSHOST PASSED yields=10001\n", "", "0", "missing/invalid native C-hook completion"),
                (good, "FAIL C hook\n", "0", "native host reported failure/corruption"),
                (good, "Lua IIgs: mm=degraded\n", "0", "native host reported failure/corruption"),
            ]
            for stdout, stderr, status, reason in cases:
                with self.subTest(stdout=stdout, stderr=stderr, status=status):
                    (stage / "host.state").write_text("prepared")
                    (stage / "host.out").write_text(stdout)
                    (stage / "host.err").write_text(stderr)
                    result = invoke("verify", status)
                    text = result.stdout.decode(errors="replace")
                    self.assertNotEqual(result.returncode, 0, text)
                    self.assertIn(reason, text)
                    self.assertNotIn("HOSTCHECK 1 HOST VERIFIED", text)
            (stage / "host.state").write_text("prepared")
            (stage / "host.out").write_bytes(good.encode())
            (stage / "host.err").write_bytes(b"")
            result = invoke("verify", "0")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(b"HOSTCHECK 1 HOST VERIFIED yields=100", result.stdout)
            (stage / "hwsmoke.lua").write_text('error("injected smoke failure")')
            result = invoke("finish")
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(b"injected smoke failure", result.stdout)
            self.assertNotIn(b"HOSTCHECK 1 PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
