"""Read the Rust capture snapshot. Never treat stale APs as current."""
import json
import time


def read_snapshot(path, now=None):
    now = time.time() if now is None else now
    with open(path) as stream:
        snapshot = json.load(stream)
    if snapshot.get('version') != 1 or snapshot.get('source') != 'rust':
        raise ValueError('unsupported recon snapshot')
    if not -5 <= now - snapshot['updated_at'] <= 10:
        raise ValueError('Rust recon snapshot is stale')
    snapshot['aps'] = [
        ap for ap in snapshot['aps']
        if isinstance(ap.get('channel'), int) and 1 <= ap['channel'] <= 196
        and -5 <= now - ap.get('last_seen', 0) <= 120
    ]
    return snapshot
