import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from phiworldforge.catalog import build_catalog
from phiworldforge.core import pack_world, read_world, validate_world
from phiworldforge.image_blaster import import_project

BASE = Path(__file__).resolve().parents[1]

class ImageBlasterImportTests(unittest.TestCase):
    def make_fixture(self, root):
        project = root / "image-blaster" / "worlds" / "test-room"
        world = project / "output/world"
        sfx = project / "output/sfx"
        world.mkdir(parents=True)
        sfx.mkdir(parents=True)
        (project / "project.json").write_text(json.dumps({"slug": "test-room", "display_name": "Test Room"}))
        for generation in (0, 4):
            (world / f"{generation}-world.json").write_text(json.dumps({
                "assets": {"splats": {"semantics_metadata": {
                    "metric_scale_factor": 0.5, "ground_plane_offset": 1.25, "flip_y": True
                }}}
            }))
            (world / f"{generation}-world.glb").write_bytes(b"stub collider")
        (world / "0-world-100k.spz").write_bytes(b"old splat")
        (world / "4-world-500k.spz").write_bytes(b"new lower resolution")
        (world / "4-world-full_res.spz").write_bytes(b"new full resolution")
        (sfx / "0-ambient.mp3").write_bytes(b"sound")
        return project

    def test_latest_generation_and_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.make_fixture(root)
            output = root / "examples/test-room"
            result = import_project(project, output)
            self.assertEqual(4, result["world_index"])
            self.assertEqual("full_res", result["splat_quality"])
            self.assertEqual(3, result["assets_copied"])
            self.assertEqual([], validate_world(output))
            scene = read_world(output)
            self.assertEqual("collider-preview", scene["entities"][0]["role"])
            self.assertEqual(0.5, scene["source"]["splat_semantics"]["metric_scale_factor"])
            self.assertEqual(b"new full resolution", (output / scene["environment_splat"]).read_bytes())
            archive = root / "world.zip"
            self.assertEqual(4, len(pack_world(output, archive)))
            with ZipFile(archive) as z:
                self.assertEqual(4, len(z.namelist()))

    def test_explicit_generation_and_quality(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.make_fixture(root)
            world = root / "generated"
            result = import_project(project, world, world_index=0, quality="100k")
            self.assertEqual(0, result["world_index"])
            self.assertEqual("100k", result["splat_quality"])

    def test_fails_when_selected_splat_not_available(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.make_fixture(root)
            with self.assertRaisesRegex(ValueError, "not downloaded locally"):
                import_project(project, root / "not-created", world_index=0, quality="full_res")
            self.assertFalse((root / "not-created").exists())

    def test_no_remote_provider_only_world(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.make_fixture(root)
            world = project / "output/world"
            for file in list(world.glob("4-world*.glb")) + list(world.glob("4-world*.spz")):
                file.unlink()
            with self.assertRaisesRegex(ValueError, "no local collider"):
                import_project(project, root / "not-created")
            self.assertFalse((root / "not-created").exists())

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.make_fixture(root)
            output = root / "existing"
            output.mkdir()
            (output / "file.txt").write_text("keep")
            with self.assertRaisesRegex(ValueError, "empty directory"):
                import_project(project, output)
            self.assertEqual("keep", (output / "file.txt").read_text())

    def test_catalog_and_check(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            worlds = root / "examples"
            output = root / "viewer/worlds.json"
            worlds.mkdir()
            project = self.make_fixture(root)
            import_project(project, worlds / "test-room")
            catalog = build_catalog(worlds, output)
            self.assertEqual("../examples/test-room/world.json", catalog["worlds"][0]["manifest"])
            self.assertEqual(catalog, build_catalog(worlds, output, check=True))
            output.write_text("{}")
            with self.assertRaisesRegex(ValueError, "stale"):
                build_catalog(worlds, output, check=True)

    def test_existing_arclight_catalog(self):
        catalog = build_catalog(BASE / "examples", BASE / "viewer/worlds.json", check=True)
        self.assertEqual("arclight-genesis", catalog["worlds"][0]["id"])

if __name__ == "__main__":
    unittest.main()
