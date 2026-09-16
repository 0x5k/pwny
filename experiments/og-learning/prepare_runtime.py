#!/usr/bin/env python3
"""Copy only radio-free experiment inputs into the runtime build context."""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
context = HERE / 'artifacts/runtime-context'
context.mkdir(parents=True, exist_ok=True)
paths = ['pwnagotchi/__init__.py', 'pwnagotchi/_version.py',
         'pwnagotchi/defaults.toml', 'pwnagotchi/mesh/__init__.py',
         'pwnagotchi/mesh/wifi.py', 'pwnagotchi/ai/__init__.py',
         'pwnagotchi/ai/gym.py', 'pwnagotchi/ai/featurizer.py',
         'pwnagotchi/ai/parameter.py', 'pwnagotchi/ai/reward.py',
         'experiments/og-learning/benchmark.py']
for relative in paths:
    target = context / 'workspace' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(ROOT / relative), str(target))
shutil.copyfile(str(HERE / 'Dockerfile.runtime'), str(context / 'Dockerfile'))
shutil.copyfile(str(HERE / 'requirements.lock'), str(context / 'requirements.lock'))
shutil.copytree(str(HERE / 'artifacts/wheelhouse'), str(context / 'wheelhouse'), dirs_exist_ok=True)
print(context)
