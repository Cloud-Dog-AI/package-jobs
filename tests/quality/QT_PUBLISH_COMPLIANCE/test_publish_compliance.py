"""Automated publish compliance test. FAILS if package is not publication-ready."""
# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0
import subprocess, pathlib, ast
import pytest

PKG_ROOT = pathlib.Path(__file__).resolve().parents[3]

def _grep(pattern, exclude=None):
    cmd = f"grep -rn '{pattern}' {PKG_ROOT} --include='*.py'"
    if exclude: cmd += f" | grep -v '{exclude}'"
    cmd += " | grep -v __pycache__ | grep -v .venv | grep -v venv"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return [l for l in r.stdout.strip().split('\n') if l]

class TestPublishCompliance:
    def test_apache_headers(self):
        missing = []
        for f in PKG_ROOT.rglob("*.py"):
            if "__pycache__" in str(f) or ".venv" in str(f): continue
            text = f.read_text(errors="ignore")[:500]
            if "Copyright" not in text and "Apache" not in text and "License" not in text:
                missing.append(str(f))
        assert len(missing) == 0, f"FAIL: {len(missing)} files missing Apache header:\n" + "\n".join(missing[:10])

    def test_public_docstrings(self):
        missing = []
        pkg_dir = next(PKG_ROOT.glob("cloud_dog_*"), None)
        if not pkg_dir: pytest.skip("No cloud_dog_* package dir found")
        for f in pkg_dir.rglob("*.py"):
            if "__pycache__" in str(f): continue
            try:
                tree = ast.parse(f.read_text())
            except: continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if not node.name.startswith("_") and not ast.get_docstring(node):
                        missing.append(f"{f}:{node.lineno} {node.name}")
        assert len(missing) == 0, f"FAIL: {len(missing)} missing docstrings:\n" + "\n".join(missing[:10])

    def test_no_secrets(self):
        hits = _grep("password.*=.*['\"]|secret.*=.*['\"]|api_key.*=.*['\"]")
        real = [h for h in hits if not any(x in h.lower() for x in ["test","example","placeholder","os.environ","config"])]
        assert len(real) == 0, f"FAIL: {len(real)} secrets:\n" + "\n".join(real[:10])

    def test_no_internal_hosts(self):
        hits = _grep("cloud-dog\\.net|viewdeck\\.com|vault0\\.|server0\\.")
        real = [h for h in hits if "#" not in h and '"""' not in h and "test" not in h.lower()]
        assert len(real) == 0, f"FAIL: {len(real)} internal hosts:\n" + "\n".join(real[:10])

    def test_licence_exists(self):
        assert (PKG_ROOT / "LICENCE").exists(), "FAIL: LICENCE missing"

    def test_readme_exists(self):
        assert (PKG_ROOT / "README.md").exists(), "FAIL: README.md missing"

    def test_changelog_exists(self):
        assert (PKG_ROOT / "CHANGELOG.md").exists(), "FAIL: CHANGELOG.md missing"
