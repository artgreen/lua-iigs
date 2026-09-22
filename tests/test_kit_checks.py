"""Negative tests for checks that previously accepted misleading success."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_support import validate


class CompletionTests(unittest.TestCase):
    def test_incidental_ok_is_not_completion(self):
        for text in ("NOT OK\n", "prefix OK suffix\n", "OK but unfinished\n"):
            with self.assertRaises(ValueError):
                validate("cstack", text)

    def test_corruption_overrides_success(self):
        for problem in ("MemCheck: memory altered", "BRK", "FAIL", "[mm] selftest state=-1",
                        "Lua IIgs: mm=degraded"):
            with self.assertRaises(ValueError):
                validate("cstack", "OK\n" + problem)

    def test_mm_workload_requires_activation(self):
        output = "MMALLOC PASSED\n[M7] state closed\n"
        with self.assertRaises(ValueError):
            validate("mmalloc", output, traced=True)
        self.assertEqual(validate("mmalloc", "[mm] selftest state=1 attr=C018\n" + output,
                                  traced=True)["status"], "passed")

    def test_small_workload_need_not_activate_mm(self):
        validate("sieve", "chain=40 primes=6 caught: C stack overflow\n[M7] state closed\n", traced=True)

    def test_trace_requires_shutdown(self):
        with self.assertRaises(ValueError):
            validate("cstack", "OK\n", traced=True)

    def test_skips_remain_visible(self):
        result = validate("hwtest", "SKIP Lua hook cannot yield\nHWTEST PASSED WITH SKIPS\n")
        self.assertEqual(result["status"], "passed with skips")
        self.assertEqual(len(result["skips"]), 1)

    def test_generated_beacons_are_synchronized(self):
        spec = importlib.util.spec_from_file_location("beacons", ROOT / "tools/generate-cobeacon.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.generate((ROOT / "tests/coroutine.lua").read_text()),
                         (ROOT / "tests/cobeacon.lua").read_text())


if __name__ == "__main__":
    unittest.main()
