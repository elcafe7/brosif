import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "scripts" / "brosif"


class LauncherTests(unittest.TestCase):
    def test_module_entrypoint_is_importable(self):
        from brosif.__main__ import main

        self.assertTrue(callable(main))

    def test_launcher_is_an_executable_shell_script(self):
        self.assertTrue(LAUNCHER.is_file())
        mode = LAUNCHER.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/bin/sh"))
        self.assertIn("venv interpreter is missing or broken", text)
        self.assertIn('exec "$VENV_PY" -m brosif "$@"', text)

    def test_python_module_help_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "brosif", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Offline multilingual terminal lexicon", result.stdout)

    def test_launcher_repairs_a_broken_venv_python(self):
        with tempfile.TemporaryDirectory() as tempdir:
            fake_root = Path(tempdir)
            (fake_root / "brosif").mkdir()
            (fake_root / "brosif" / "__init__.py").write_text("", encoding="utf-8")
            (fake_root / "brosif" / "__main__.py").write_text(
                "print('repaired-main')\n",
                encoding="utf-8",
            )
            (fake_root / "pyproject.toml").write_text(
                "\n".join(
                    [
                        "[build-system]",
                        'requires = ["setuptools>=68"]',
                        'build-backend = "setuptools.build_meta"',
                        "",
                        "[project]",
                        'name = "brosif"',
                        'version = "0"',
                        'requires-python = ">=3.10"',
                        "",
                        "[tool.setuptools.packages.find]",
                        'include = ["brosif*"]',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            venv_bin = fake_root / ".venv" / "bin"
            venv_bin.mkdir(parents=True)
            broken = venv_bin / "python"
            broken.symlink_to("/opt/homebrew/Cellar/python@3.12/missing/bin/python3.12")
            self.assertFalse(broken.exists())

            launcher = fake_root / "scripts" / "brosif"
            launcher.parent.mkdir()
            launcher.write_text(LAUNCHER.read_text(encoding="utf-8"), encoding="utf-8")
            launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            result = subprocess.run(
                [str(launcher), "--help"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=fake_root,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("repaired-main", result.stdout)
            self.assertIn("repairing", result.stderr)
            self.assertTrue((fake_root / ".venv" / "bin" / "python").exists())


if __name__ == "__main__":
    unittest.main()
