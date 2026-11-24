"""Regression tests for the v2.0 design-parity validator.
Run on a throwaway project fixture so a verification never alters the real package.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix='sass-design-') as temp:
    project = Path(temp) / 'SASS_HRM_Enterprise'
    shutil.copytree(ROOT / 'web', project / 'web', ignore=shutil.ignore_patterns('node_modules', 'dist', '*.tsbuildinfo'))
    (project / 'server').mkdir(parents=True)
    shutil.copy2(ROOT / 'server/create_admin.py', project / 'server/create_admin.py')
    (project / 'scripts').mkdir(parents=True)
    shutil.copy2(ROOT / 'scripts/verify-design-parity.py', project / 'scripts/verify-design-parity.py')
    package_path = project / 'web/package.json'
    original = json.loads(package_path.read_text(encoding='utf-8'))

    def check(version: str, expect_success: bool) -> None:
        package = {**original, 'version': version}
        package_path.write_text(json.dumps(package, indent=2), encoding='utf-8')
        result = subprocess.run([sys.executable, str(project / 'scripts/verify-design-parity.py')],
                                capture_output=True, text=True, check=False)
        if (result.returncode == 0) != expect_success:
            raise AssertionError(f'Unexpected result for {version!r}:\n{result.stdout}\n{result.stderr}')

    check(original['version'], True)
    check('2.1.0', True)  # A version change alone must not break design parity.
    check('invalid-version', False)
    package_path.write_text(json.dumps(original, indent=2), encoding='utf-8')
    style_path = project / 'web/src/style.css'
    style_path.write_text(style_path.read_text(encoding='utf-8').replace('--sass-primary: #5a5fe9;',
                        '--sass-primary: #000000;'), encoding='utf-8')
    result = subprocess.run([sys.executable, str(project / 'scripts/verify-design-parity.py')],
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0, 'Validator must reject missing expected theme tokens'

print('PASS: current release, future version bump, invalid version rejection and design regression detection.')
