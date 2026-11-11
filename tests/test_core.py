import copy
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from phiworldforge.core import SCHEMA, read_world, validate_world, pack_world, ingest_exports

DEMO = Path(__file__).resolve().parents[1] / "examples" / "arclight-room"

class GenesisTests(unittest.TestCase):
    def test_demo_valid(self):
        self.assertEqual([], validate_world(DEMO))

    def test_reproducible_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.zip", Path(tmp) / "b.zip"
            self.assertEqual(["world.json"], pack_world(DEMO, a))
            pack_world(DEMO, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with ZipFile(a) as archive:
                self.assertEqual(["world.json"], archive.namelist())

    def _test_document(self, modified):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = copy.deepcopy(read_world(DEMO))
            modified(doc)
            (root / "world.json").write_text(json.dumps(doc), encoding="utf-8")
            return validate_world(root)

    def test_duplicate_entities(self):
        self.assertTrue(any("duplicated" in e for e in self._test_document(
            lambda d: d["entities"].append(copy.deepcopy(d["entities"][0]))
        )))

    def test_traversal(self):
        self.assertTrue(any("traversal" in e for e in self._test_document(
            lambda d: d["entities"].append({
                "id": "bad", "kind": "mesh", "position": [0, 0, 0],
                "asset": "assets/../../private.glb"
            })
        )))

    def test_non_finite(self):
        self.assertTrue(any("spawn" in e for e in self._test_document(
            lambda d: d.update(spawn=[0, float("inf"), 1])
        )))

    def test_missing_asset(self):
        self.assertTrue(any("file not found" in e for e in self._test_document(
            lambda d: d.update(environment_splat="assets/not-there.spz")
        )))

    def test_ingest_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = [root / "model.glb", root / "env.spz", root / "wind.mp3"]
            for source in sources:
                source.write_bytes(b"stub")
            world = root / "world"
            ingest_exports(world, "Generated Room", *sources)
            self.assertEqual([], validate_world(world))
            self.assertEqual(SCHEMA, read_world(world)["schema"])
            archive = root / "out.zip"
            pack_world(world, archive)
            with ZipFile(archive) as z:
                self.assertEqual(["world.json", "assets/env.spz", "assets/model.glb", "assets/wind.mp3"], z.namelist())

    def test_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "existing").mkdir()
            (root / "existing" / "data").write_text("do not touch")
            mesh = root / "model.glb"
            mesh.write_bytes(b"stub")
            with self.assertRaises(ValueError):
                ingest_exports(root / "existing", "Title", mesh=mesh)
            self.assertEqual("do not touch", (root / "existing" / "data").read_text())

if __name__ == "__main__":
    unittest.main()
