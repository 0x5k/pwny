# Rust recon on the Pi

This experimental backend is currently disabled on the Pi. OG 1.5.5 now uses
the existing bundled Jay Bettercap build for Wi-Fi capture, channel control
and handshake events. Do not start this service alongside Bettercap Wi-Fi:
they would compete for channel control. The description below documents the
retained Rust backend, not the active OG configuration.

`mon0-probe` is now a continuous passive capture service. Linux/Nexmon still
provides the radiotap monitor interface. Radio setup creates `mon0` and brings
the parent `wlan0` down so it does not reserve a channel. Rust captures packets
and runs `iw` to hop channels 1, 6 and 11 every two seconds.

The service publishes `/run/pwnagotchi/recon.json` atomically every second.
It includes APs, timestamps, current channel, frame counts and hop successes/errors.
APs expire after 120 seconds; the Python reader rejects snapshots over ten seconds
old. `main.rust_recon = true` makes the OG agent consume this data and suppresses
its Bettercap recon, channel, association and deauthentication commands.

Bettercap remains on loopback with its REST API on port 8081. Its Wi-Fi module
stays off. The OG dashboard uses port 8082; diagnostics use 8080.

Raw packets rotate between `capture.pcap` and `capture.previous.pcap` in
`/run/pwnagotchi`, capped at 8 MiB per file. These are temporary RAM files,
lost on reboot. This implements passive discovery and recording, not handshake
completion detection, injection or Rust identity/mesh support. RSSI is currently
unknown and the channel schedule is fixed. Raw captures may contain EAPOL frames,
but should not be reported as validated handshakes.

Build on the development host with Rust, the `aarch64-unknown-linux-gnu` target
and Zig installed:

```sh
./rust/build-pi.sh
cargo test --manifest-path rust/mon0-probe/Cargo.toml
python3 -m unittest discover -s tests -p test_recon_snapshot.py
```

The full image build invokes that cross-build and installs the executable and
systemd units. For live diagnostics on the Pi:

```sh
systemctl status pwnagotchi-rust-recon bettercap pwnagotchi
sudo cat /run/pwnagotchi/recon.json
iw dev mon0 info
journalctl -u pwnagotchi-rust-recon -u pwnagotchi
```

Start learning with `src/parser.rs` (radiotap and 802.11 management frames),
then `src/capture.rs` (Linux sockets, hopping, bounded files and snapshots),
and `../pwnagotchi/recon.py` plus `agent.py` (consumer integration). The driver
and Nexmon firmware remain necessary; Rust replaces the userspace radio owner.
