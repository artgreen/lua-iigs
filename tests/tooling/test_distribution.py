"""Distribution contracts: source staging, release evidence, and clean exports."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from iigsbuild.common import BuildError, digest_json
from iigsbuild import identified, release, testfiles, runtests, kits
from iigsbuild.contracts import suite_manifest, compact_manifest
from iigsbuild.distribution import source_files
from iigsbuild.runtests import ALL_CHECKS, EXECUTABLES, NEEDS, expected_checks


class TestSources(unittest.TestCase):
    def test_every_suite_and_compact_script_resolves(self):
        names = set(suite_manifest()["tests"]) | {"tracegc"}
        plan = compact_manifest()
        for group in plan["groups"].values():
            names.update(group)
        names.update(plan["helpers"])
        for name in names:
            self.assertTrue(testfiles.test_source(name + ".lua").is_file(), name)

    def test_staging_preserves_non_ascii_fixture_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            testfiles.stage_sources(Path(temp))
            self.assertEqual((Path(temp) / "files.lua").read_bytes(),
                             (ROOT / "tests/upstream/files.lua").read_bytes())

    def test_source_inventory_excludes_local_and_generated_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("README.md", "src/lua.c", "build/output.c", ".rebuild-backup/a.md",
                         "tools/__pycache__/x.py", ".orca-sdk-2.2.1/private.h", "src/lua.a"):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")
            self.assertEqual(source_files(root), ["README.md", "src/lua.c"])

    def test_archive_provenance_does_not_borrow_parent_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = b"source"
            from iigsbuild.common import sha256
            (root / "SOURCE-MANIFEST.json").write_text(json.dumps({
                "commit": "original", "files_sha256": {"src/lua.c": sha256(data)}}))
            with patch.object(identified, "ROOT", root), patch.object(identified.subprocess, "run",
                    return_value=SimpleNamespace(stdout=str(root.parent))):
                state = identified.git_state({"src/lua.c": data})
                self.assertEqual(state["commit"], "original")
                self.assertTrue(state["inputs_match_commit"])
                self.assertFalse(identified.git_state({"src/lua.c": b"changed"})["inputs_match_commit"])

    def test_source_archive_provenance_without_git_installed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "SOURCE-MANIFEST.json").write_text(json.dumps({
                "commit": "original", "files_sha256": {}}))
            with patch.object(identified, "ROOT", root), patch.object(identified.subprocess, "run",
                    side_effect=FileNotFoundError):
                self.assertEqual(identified.git_state({})["commit"], "original")

    def test_flat_staging_rejects_case_collisions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("upstream/a.lua", "regression/A.lua"):
                p = root / "tests" / name
                p.parent.mkdir(parents=True)
                p.write_text("return true")
            with patch.object(testfiles, "ROOT", root), self.assertRaisesRegex(BuildError, "duplicate"):
                testfiles.sources()


class ReleaseEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "report.json"
        self.inputs = {"tests/regression/test.lua": "source-hash"}
        needed = {n for group in ALL_CHECKS for n in NEEDS[group]}
        artifacts = {EXECUTABLES[n]: {"sha256": n + "-hash"} for n in needed}
        self.build = SimpleNamespace(id="abc", manifest_sha256="manifest", manifest={"artifacts": artifacts})
        self.report = {"schema": "lua-iigs-test-report/1",
                       "subject": {"build_id": "abc", "build_manifest_sha256": "manifest",
                       "executables_sha256": {n: n + "-hash" for n in needed}},
                       "checks": [{"group": g, "name": n, "subject": s, "status": "passed"}
                                  for g, n, s in expected_checks()],
                       "summary": {"failed": 0, "total": len(expected_checks()), "with_skips": 0, "built_only": 0},
                       "test_inputs_sha256": self.inputs, "test_identity": digest_json(self.inputs)[:12]}
        self.report["checks"][0]["tests"] = 55

    def check(self, report):
        self.path.write_text(json.dumps(report))
        with patch.object(release, "test_inputs", return_value=self.inputs):
            return release.approved_report(self.path, self.build)

    def test_accepts_all_groups_with_explicit_skips(self):
        self.report["checks"][1]["status"] = "passed with skips"
        self.report["checks"][1]["skips"] = ["intentional"]
        self.report["summary"]["with_skips"] = 1
        self.assertEqual(self.check(self.report)["summary"]["failed"], 0)

    def test_only_memfree_may_be_built_without_a_run(self):
        self.report["checks"][-1]["status"] = "built, not run"
        self.report["summary"]["built_only"] = 1
        self.check(self.report)
        self.report["checks"][-1]["name"] = "iigshost"
        with self.assertRaises(BuildError):
            self.check(self.report)

    def test_rejects_failed_incomplete_stale_or_different_artifact_evidence(self):
        mutations = [lambda r: r["checks"][0].update(status="FAILED"),
                     lambda r: r["checks"].pop(),
                     lambda r: r["test_inputs_sha256"].update(stale="hash"),
                     lambda r: r["subject"]["executables_sha256"].update(lua="different"),
                     lambda r: r["subject"].update(build_manifest_sha256="different"),
                     lambda r: r["checks"][0].update(tests=0),
                     lambda r: r["checks"][1].update(subject="wrong-runtime"),
                     lambda r: r.update(schema="unknown"),
                     lambda r: r["summary"].update(total=999)]
        for change in mutations:
            report = copy.deepcopy(self.report)
            change(report)
            with self.subTest(change=change), self.assertRaises(BuildError):
                self.check(report)

    def test_rejects_missing_check_even_with_correct_group_set_and_total(self):
        self.report["checks"].pop(1)
        self.report["summary"]["total"] -= 1
        with self.assertRaisesRegex(BuildError, "every check"):
            self.check(self.report)

    def test_rejects_duplicate_in_place_of_required_check(self):
        self.report["checks"][2] = self.report["checks"][1].copy()
        with self.assertRaisesRegex(BuildError, "every check"):
            self.check(self.report)

    def test_missing_hash_in_both_manifest_and_report_is_not_evidence(self):
        del self.report["subject"]["executables_sha256"]["lua"]
        del self.build.manifest["artifacts"][EXECUTABLES["lua"]]
        with self.assertRaisesRegex(BuildError, "executable lua"):
            self.check(self.report)

    def test_zip_refuses_overwrite_and_keeps_binary_bytes(self):
        file = Path(self.temp.name) / "LUA.SHK"
        file.write_bytes(b"\x00\x80\xff\r\n")
        archive = Path(self.temp.name) / "bundle.zip"
        release.zip_files(archive, {"LUA.SHK": file})
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read("LUA.SHK"), file.read_bytes())
        with self.assertRaises(FileExistsError):
            release.zip_files(archive, {"LUA.SHK": file})


class DistributionAssembly(unittest.TestCase):
    def test_standard_includes_every_standalone_example_and_compact_only_hello(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "executable"
            artifact.write_bytes(b"executable")
            build = SimpleNamespace(id="test", path=lambda _: artifact,
                                    manifest={"banners": {"lua": "full", "lua-small": "compact"}})
            expected = {p.name.upper(): p.read_bytes() for p in (ROOT / "examples").glob("*.lua")}
            full = {m.name: m.data for m in release.product_members(build, False, "commit")}
            for name, data in expected.items():
                self.assertEqual(full[name],data)
                self.assertIn("](" + name + ")",full["EXAMPLES.TXT"].decode())
            compact = {m.name for m in release.product_members(build, True, "commit")}
            self.assertEqual(compact & set(expected),{"HELLO.LUA"})

    def test_report_identity_covers_standalone_examples(self):
        inputs = runtests.test_inputs()
        for path in (ROOT / "examples").glob("*.lua"):
            self.assertIn(str(path.relative_to(ROOT)),inputs)

    def test_failed_assembly_never_appears_as_a_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("0.3.0")
            previous = root / "dist/previous/README.txt"
            previous.parent.mkdir(parents=True)
            previous.write_text("existing candidate")
            args = SimpleNamespace(build="build", report="report", sdk=None)
            def assemble(*args):
                (args[-1] / "partial.shk").write_bytes(b"partial")
                raise BuildError("packager failed")
            with patch.object(release, "ROOT", root), patch.object(release, "resolve"), \
                    patch.object(release, "approved_report"), \
                    patch.object(release, "committed_sources", return_value=("commit", [])), \
                    patch.object(release.Toolchain, "discover"), patch.object(release, "assemble", side_effect=assemble):
                with self.assertRaisesRegex(BuildError, "packager failed"):
                    release.release(args)
                self.assertEqual(list((root / "dist").iterdir()), [previous.parent])
                self.assertEqual(previous.read_text(), "existing candidate")
                self.assertFalse(hasattr(args, "release_path"))
                self.assertEqual(len(list((root / "build/release-staging").glob("*/partial.shk"))), 1)

    def test_completed_candidate_moves_to_dist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("0.3.0")
            args = SimpleNamespace(build="build", report="report", sdk=None)
            def assemble(*args):
                (args[-1] / "verified.txt").write_text("completed")
            with patch.object(release, "ROOT", root), patch.object(release, "resolve"), \
                    patch.object(release, "approved_report"), \
                    patch.object(release, "committed_sources", return_value=("commit", [])), \
                    patch.object(release.Toolchain, "discover"), patch.object(release, "assemble", side_effect=assemble):
                self.assertEqual(release.release(args), 0)
                self.assertEqual(args.release_path.parent, root / "dist")
                self.assertEqual((args.release_path / "verified.txt").read_text(), "completed")
                self.assertEqual(list((root / "build/release-staging").iterdir()), [])

    def test_missing_corrupt_and_incomplete_nested_archives_are_clean_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "RELEASE-MANIFEST.json").write_text(json.dumps({
                "executable_containers": {"IIGSHOST": {"zip": "diagnostics.zip", "archive": "IIGSHOST.SHK"}}}))
            args = SimpleNamespace(build=None, release=root, exe=None)
            for contents in (None, b"not a zip", b""):
                if contents is not None:
                    (root / "diagnostics.zip").write_bytes(contents)
                if contents == b"":
                    with zipfile.ZipFile(root / "diagnostics.zip", "w") as archive:
                        archive.writestr("wrong.shk", b"wrong")
                with self.subTest(contents=contents), self.assertRaisesRegex(BuildError, "cannot read IIGSHOST"):
                    kits.executables(args, SimpleNamespace(), ["iigshost"])

    def test_inputs_changed_during_testing_cannot_produce_a_report(self):
        from iigsbuild.toolchain import Toolchain
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            exe = work / "lua"
            exe.write_bytes(b"executable")
            subject = {"kind": "dev", "paths": {"lua": exe}}
            args = SimpleNamespace(sdk=None, checks=["unit"], config=None, timeout=1)
            with patch.object(Toolchain, "discover"), patch.object(runtests, "subject_for", return_value=subject), \
                    patch.object(runtests, "TEST_RUNS", work), patch.object(runtests.Session, "unit"), \
                    patch.object(runtests, "test_inputs", side_effect=[{"test": "before"}, {"test": "after"}]):
                with self.assertRaisesRegex(BuildError, "changed during the run"):
                    runtests.run_tests(args)
                self.assertEqual(list(work.rglob("report.json")), [])

    def test_bundled_markdown_links_resolve_or_pin_to_source_commit(self):
        import re
        with tempfile.TemporaryDirectory() as temp:
            files = release.bundle_guides(Path(temp), "a" * 40)
            for name, path in files.items():
                if path.suffix != ".md":
                    continue
                for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                    with self.subTest(name=name, link=link):
                        if link.startswith("https://github.com/artgreen/lua-iigs/blob/"):
                            self.assertIn("/" + "a" * 40 + "/", link)
                        elif not re.match(r"[a-z]+:", link):
                            self.assertTrue((path.parent / link.split("#")[0]).exists())

    def test_native_guides_reference_shipped_filenames(self):
        local = {"docs/INSTALL.md": "INSTALL.TXT", "docs/COMPATIBILITY.md": "COMPAT.TXT",
                 "docs/USAGE.md": "USAGE.TXT"}
        text = release.render_guide("docs/INSTALL.md", local, "commit")
        self.assertIn("](COMPAT.TXT)", text)
        self.assertIn("](USAGE.TXT)", text)


if __name__ == "__main__":
    unittest.main()
