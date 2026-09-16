#!/usr/bin/env python3
"""Run a previously host-validated rootfs in a bounded systemd test unit.

Requires root; never stops normal services, changes networking, or enables swap.
The mounted rootfs is read-only. Only /results is writable inside the worker.
"""
import argparse
import json
import platform
from pathlib import Path
import subprocess
import time

SERVICES = ('pwnagotchi.service', 'bettercap.service')


def properties(unit):
    result = subprocess.run(['systemctl', 'show', unit, '--no-pager',
                             '-p', 'ActiveState', '-p', 'NRestarts',
                             '-p', 'Result', '-p', 'ExecMainStatus',
                             '-p', 'MemoryPeak', '-p', 'ControlGroup'],
                            check=True, text=True, capture_output=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def memory():
    return {line.split(':')[0]: int(line.split()[1]) for line in
            Path('/proc/meminfo').read_text().splitlines()}


def oom_kills():
    return int(dict(line.split() for line in Path('/proc/vmstat').read_text().splitlines())['oom_kill'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rootfs', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    rootfs, output = args.rootfs.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any((output / name).exists() for name in ('train.json', 'restore.json', 'brain.nn', 'pi-monitor.json')):
        raise SystemExit('Use a fresh output directory; refusing stale benchmark artifacts')
    (output / 'tmp').mkdir(exist_ok=True)
    baseline = {s: properties(s) for s in SERVICES}
    initial_mem = memory()
    initial_oom = oom_kills()
    # Reserve the required 50 MiB plus 10 MiB for supervisor/service variation.
    limit_mib = (initial_mem['MemAvailable'] // 1024) - 60
    report = dict(status='fail', baseline_services=baseline,
                  kernel=platform.release(), architecture=platform.machine(),
                  device_model=Path('/proc/device-tree/model').read_text().rstrip('\x00'),
                  initial_memory_kib=initial_mem, memory_limit_mib=limit_mib,
                  sample_interval_seconds=0.1, phases=[])
    failure = None
    if any(v['ActiveState'] != 'active' for v in baseline.values()):
        failure = 'normal services are not active before test'
    elif initial_mem['SwapTotal'] != 0:
        failure = 'swap is configured; no-swap acceptance precondition failed'
    elif limit_mib < 64:
        failure = 'insufficient initial available memory'
    else:
        for phase in ('train', 'restore'):
            unit = 'og-learning-%s-%d.service' % (phase, time.time_ns())
            command = ['systemd-run', '--unit=' + unit, '--wait', '--pipe',
                       '-p', 'RootDirectory=' + str(rootfs),
                       '-p', 'MountAPIVFS=yes', '-p', 'PrivateNetwork=yes',
                       '-p', 'PrivateDevices=yes', '-p', 'NoNewPrivileges=yes',
                       '-p', 'ProtectSystem=strict', '-p', 'ProtectHome=yes',
                       '-p', 'BindPaths=%s:/results %s/tmp:/tmp' % (output, output),
                       '-p', 'ReadWritePaths=/results /tmp',
                       '-p', 'MemoryMax=%dM' % limit_mib,
                       '-p', 'MemorySwapMax=0', '-p', 'OOMPolicy=stop',
                       '-p', 'RuntimeMaxSec=%d' % args.timeout,
                       '-p', 'TimeoutStopSec=5',
                       '--setenv=OPENBLAS_NUM_THREADS=1', '--setenv=OMP_NUM_THREADS=1',
                       '--setenv=TF_NUM_INTRAOP_THREADS=1', '--setenv=TF_NUM_INTEROP_THREADS=1',
                       '--setenv=PYTHONUNBUFFERED=1', '--setenv=PYTHONDONTWRITEBYTECODE=1',
                       '--setenv=MPLCONFIGDIR=/results/matplotlib',
                       '--setenv=TMPDIR=/tmp',
                       '/usr/local/bin/python', '/workspace/experiments/og-learning/benchmark.py',
                       phase, '--output', '/results']
            samples = []
            service_samples = []
            peak_cgroup_bytes = 0
            cgroup_path = None
            start = time.monotonic()
            stopped = False
            with (output / (phase + '.log')).open('w') as log:
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                try:
                    while proc.poll() is None:
                        mem = memory()
                        samples.append([time.monotonic() - start, mem['MemAvailable'], mem['SwapFree']])
                        if len(samples) % 10 == 1:
                            worker = properties(unit)
                            if worker.get('ControlGroup'):
                                cgroup_path = Path('/sys/fs/cgroup') / worker['ControlGroup'].lstrip('/')
                            current = {s: properties(s) for s in SERVICES}
                            service_samples.append(current)
                            if any(current[s]['ActiveState'] != 'active' or
                                   current[s]['NRestarts'] != baseline[s]['NRestarts'] for s in SERVICES):
                                failure = 'normal service failure or restart'
                        if cgroup_path is not None:
                            try:
                                peak_cgroup_bytes = max(peak_cgroup_bytes,
                                    int((cgroup_path / 'memory.peak').read_text()))
                            except FileNotFoundError:
                                pass  # systemd removes the cgroup after process exit
                        if mem['MemAvailable'] < 50 * 1024:
                            failure = 'available memory fell below 50 MiB'
                        if time.monotonic() - start > args.timeout + 15:
                            failure = 'supervisor timeout'
                        if failure and not stopped:
                            subprocess.run(['systemctl', 'stop', unit], check=False)
                            stopped = True
                        time.sleep(0.1)
                    rc = proc.wait(timeout=10)
                finally:
                    if proc.poll() is None:
                        subprocess.run(['systemctl', 'stop', unit], check=False)
                        proc.wait(timeout=15)
            state = properties(unit)
            record = dict(phase=phase, exit_code=rc, unit=unit, unit_state=state,
                          sampled_cgroup_peak_mib=peak_cgroup_bytes / (1024 * 1024),
                          elapsed_seconds=time.monotonic() - start,
                          min_available_mib=min(s[1] for s in samples) / 1024,
                          memory_samples=samples, service_samples=service_samples)
            report['phases'].append(record)
            if rc != 0 or state.get('Result') not in ('success', ''):
                failure = failure or 'worker failed: ' + state.get('Result', 'unknown')
            if not (output / (phase + '.json')).exists():
                failure = failure or 'worker did not produce completed training report'
            if failure:
                break
    report['final_services'] = {s: properties(s) for s in SERVICES}
    report['oom_kills_delta'] = oom_kills() - initial_oom
    if report['oom_kills_delta']:
        failure = failure or 'OOM kill occurred'
    if any(report['final_services'][s]['ActiveState'] != 'active' or
           report['final_services'][s]['NRestarts'] != baseline[s]['NRestarts'] for s in SERVICES):
        failure = failure or 'normal services changed state or restarted'
    report['failure'] = failure
    report['status'] = 'fail' if failure else 'pass'
    (output / 'pi-monitor.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'phases'}, indent=2))
    raise SystemExit(1 if failure else 0)


if __name__ == '__main__':
    main()
