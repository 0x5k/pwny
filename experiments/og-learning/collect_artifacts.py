#!/usr/bin/env python3
"""Complete the wheel archive (including build tools), then record provenance."""
from pathlib import Path
import shutil
import subprocess
import sys

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze', '--all'], text=True)
Path('/tmp/installed.txt').write_text(freeze)
subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                '--find-links=/wheelhouse', '--wheel-dir=/wheelhouse', '-r', '/tmp/installed.txt'], check=True)
subprocess.run([sys.executable, str(Path(__file__).with_name('manifest.py')), str(out / 'manifest')], check=True)
(out / 'wheelhouse').mkdir(exist_ok=True)
for wheel in Path('/wheelhouse').glob('*.whl'):
    shutil.copyfile(str(wheel), str(out / 'wheelhouse' / wheel.name))
