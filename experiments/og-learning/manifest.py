#!/usr/bin/env python3
"""Run inside the build container to lock installed wheels and their origins."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request
import zipfile
from email.parser import Parser

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
records = []
locks = []
for path in sorted(Path('/wheelhouse').glob('*.whl')):
    with zipfile.ZipFile(str(path)) as wheel:
        metadata = Parser().parsestr(wheel.read(next(n for n in wheel.namelist()
                                                    if n.endswith('.dist-info/METADATA'))).decode())
    name, version = metadata['Name'], metadata['Version']
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if name.lower() == 'tensorflow':
        sources = [dict(url='https://media.githubusercontent.com/media/noahzhy/tf-aarch64/'
                        '75a83c8e83b43834a1de73fa11822967e4634ad3/' + path.name,
                        sha256=digest, provenance='community binary; build recipe not supplied')]
    else:
        with urllib.request.urlopen('https://pypi.org/pypi/%s/%s/json' % (name, version)) as response:
            release = json.load(response)
        matching = [f for f in release['urls'] if f['filename'] == path.name]
        # Locally built wheels refer back to the release source archive.
        artifacts = matching or [f for f in release['urls'] if f['packagetype'] == 'sdist']
        sources = [dict(url=f['url'], sha256=f['digests']['sha256']) for f in artifacts]
        if matching:
            assert any(f['digests']['sha256'] == digest for f in matching), path.name
        assert sources, 'no source provenance for ' + path.name
    records.append(dict(name=name, version=version, wheel=path.name, sha256=digest,
                        source_artifacts=sources))
    locks.append('%s==%s --hash=sha256:%s' % (name, version, digest))
(out / 'requirements.lock').write_text('\n'.join(sorted(locks, key=str.lower)) + '\n')
(out / 'dependencies.json').write_text(json.dumps(dict(python=sys.version,
    architecture=platform.machine(), artifacts=records), indent=2) + '\n')
for filename, command in [('pip-freeze.txt', [sys.executable, '-m', 'pip', 'freeze', '--all']),
                          ('debian-packages.txt', ['dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\n'])]:
    (out / filename).write_text(subprocess.check_output(command, text=True))
