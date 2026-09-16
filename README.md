# Pwnagotchi

> **Zero 2 W ARM64 branch:** this branch is building an OG-derived
> `og-gen-rs:1.5.5` image with Docker, Raspberry Pi's official image generator,
> USB SSH, and native Waveshare 2.13-inch V4 support. See
> [image/README.md](image/README.md) for the quick start and
> [image/BUILDING.md](image/BUILDING.md) for the complete reproducible guide.
> The display milestone is summarized chapter-by-chapter in
> [image/MILESTONE-DISPLAY.md](image/MILESTONE-DISPLAY.md).
> Live SSH observability, mock-face testing, radio preflight, and the flash gate
> are documented in [image/DEBUGGING.md](image/DEBUGGING.md).

<p align="center">
    <a href="https://github.com/evilsocket/pwnagotchi/releases/latest"><img alt="Release" src="https://img.shields.io/github/release/evilsocket/pwnagotchi.svg?style=flat-square"></a>
    <a href="https://github.com/evilsocket/pwnagotchi/blob/master/LICENSE.md"><img alt="Software License" src="https://img.shields.io/badge/license-GPL3-brightgreen.svg?style=flat-square"></a>
    <a href="https://github.com/evilsocket/pwnagotchi/graphs/contributors"><img alt="Contributors" src="https://img.shields.io/github/contributors/evilsocket/pwnagotchi"/></a>
    <a href="https://travis-ci.org/evilsocket/pwnagotchi"><img alt="Travis" src="https://img.shields.io/travis/evilsocket/pwnagotchi/master.svg?style=flat-square"></a>
    <a href="https://invite.pwnagotchi.ai/"><img alt="Slack" src="https://invite.pwnagotchi.ai/badge.svg"></a>
    <a href="https://community.pwnagotchi.ai/"><img alt="Forum" src="https://img.shields.io/discourse/posts?server=https%3A%2F%2Fcommunity.pwnagotchi.ai%2F&style=flat-square"></a>
    <a href="https://twitter.com/intent/follow?screen_name=pwnagotchi"><img src="https://img.shields.io/twitter/follow/pwnagotchi?style=social&logo=twitter" alt="follow on Twitter"></a>
</p>

[Pwnagotchi](https://pwnagotchi.ai/) is an [A2C](https://hackernoon.com/intuitive-rl-intro-to-advantage-actor-critic-a2c-4ff545978752)-based "AI" leveraging [bettercap](https://www.bettercap.org/) that learns from its surrounding WiFi environment to maximize the crackable WPA key material it captures (either passively, or by performing authentication and association attacks). This material is collected as PCAP files containing any form of handshake supported by [hashcat](https://hashcat.net/hashcat/), including [PMKIDs](https://www.evilsocket.net/2019/02/13/Pwning-WiFi-networks-with-bettercap-and-the-PMKID-client-less-attack/), 
full and half WPA handshakes.

![ui](https://i.imgur.com/X68GXrn.png)

Instead of merely playing [Super Mario or Atari games](https://becominghuman.ai/getting-mario-back-into-the-gym-setting-up-super-mario-bros-in-openais-gym-8e39a96c1e41?gi=c4b66c3d5ced) like most reinforcement learning-based "AI" *(yawn)*, Pwnagotchi tunes [its parameters](https://github.com/evilsocket/pwnagotchi/blob/master/pwnagotchi/defaults.toml) over time to **get better at pwning WiFi things to** in the environments you expose it to. 

More specifically, Pwnagotchi is using an [LSTM with MLP feature extractor](https://stable-baselines.readthedocs.io/en/master/modules/policies.html#stable_baselines.common.policies.MlpLstmPolicy) as its policy network for the [A2C agent](https://stable-baselines.readthedocs.io/en/master/modules/a2c.html). If you're unfamiliar with A2C, here is [a very good introductory explanation](https://hackernoon.com/intuitive-rl-intro-to-advantage-actor-critic-a2c-4ff545978752) (in comic form!) of the basic principles behind how Pwnagotchi learns. (You can read more about how Pwnagotchi learns in the [Usage](https://www.pwnagotchi.ai/usage/#training-the-ai) doc.)

**Keep in mind:** Unlike the usual RL simulations, Pwnagotchi learns over time. Time for a Pwnagotchi is measured in epochs; a single epoch can last from a few seconds to minutes, depending on how many access points and client stations are visible. Do not expect your Pwnagotchi to perform amazingly well at the very beginning, as it will be [exploring](https://hackernoon.com/intuitive-rl-intro-to-advantage-actor-critic-a2c-4ff545978752) several combinations of [key parameters](https://www.pwnagotchi.ai/usage/#training-the-ai) to determine ideal adjustments for pwning the particular environment you are exposing it to during its beginning epochs ... but ** listen to your Pwnagotchi when it tells you it's boring!** Bring it into novel WiFi environments with you and have it observe new networks and capture new handshakes—and you'll see. :)

Multiple units within close physical proximity can "talk" to each other, advertising their presence to each other by broadcasting custom information elements using a parasite protocol I've built on top of the existing dot11 standard. Over time, two or more units trained together will learn to cooperate upon detecting each other's presence by dividing the available channels among them for optimal pwnage.

## Documentation

https://www.pwnagotchi.ai

## Links

&nbsp; | Official Links
---------|-------
Website | [pwnagotchi.ai](https://pwnagotchi.ai/)
Forum | [community.pwnagotchi.ai](https://community.pwnagotchi.ai/)
Slack | [pwnagotchi.slack.com](https://invite.pwnagotchi.ai/)
Subreddit | [r/pwnagotchi](https://www.reddit.com/r/pwnagotchi/)
Twitter | [@pwnagotchi](https://twitter.com/pwnagotchi)

## License

`pwnagotchi` is made with ♥  by [@evilsocket](https://twitter.com/evilsocket) and the [amazing dev team](https://github.com/evilsocket/pwnagotchi/graphs/contributors). It is released under the GPL3 license.


 The important distinction is this:

  - Identity generation is a userspace detail. Jay uses pwngrid -generate -keys /etc/pwnagotchi; our PyCryptodome fallback produces the same kind of persistent RSA identity.
  - The capture limitation is below Pwnagotchi. It is the interaction between the Nexmon firmware, the brcmfmac kernel module, iw, and Bettercap’s rfmon handling.
  - pwngrid will not fix capture. It only provides the local grid API for peers, inbox, identity advertisement, and optional AP reports.

  Jay’s working radio sequence is:

  wlan0 managed
    -> Nexmon/brcmfmac
    -> create wlan0mon
    -> Bettercap opens wlan0mon
    -> Pwnagotchi runs wifi.recon

  Our current sequence is:

  wlan0 managed
    -> create mon0
    -> Bettercap opens mon0
    -> Bettercap tries rfmon again
    -> this driver returns "Cannot set rfmon for this handle"

  That is why the service can stay alive only with the temporary “preconfigured monitor” mode, which skips recon. The service is running now, but it is effectively blind and
  should not yet be considered fully fixed.

  The Nexmon/driver layer is therefore important. It determines:

  - whether monitor interfaces can be created;
  - whether the interface is really receiving radiotap frames;
  - whether channels can be changed;
  - whether Bettercap can open it;
  - whether recon and handshake capture work.

  The most useful files to study in this project are:

  - image/nexmon-install.sh: installs firmware and the patched brcmfmac module.
  - image/patches/brcmfmac-6.18-nexmon.patch: kernel behavior changed for Nexmon.
  - image/layer/pwnagotchi-diagnostic/rootfs/usr/local/bin/pwnagotchi-radio-setup: creates mon0.
  - image/layer/pwnagotchi-diagnostic/rootfs/usr/local/bin/pwnagotchi-bettercap: starts Bettercap.
  - pwnagotchi/agent.py: starts recon, changes channels, handles APs and handshakes.
  - pwnagotchi/bettercap.py: sends commands to Bettercap’s REST API.
  - pwnagotchi/ui/hw/waveshare2in13_v4.py: display hardware boundary.

  There are currently no Rust files or Cargo project in this repository. The project is Python plus shell/systemd, despite the repository name. A sensible Rust migration
  would keep the kernel and Bettercap boundaries intact:

  Rust supervisor
    -> radio setup / status
    -> Bettercap process and REST API
    -> Pwnagotchi control loop
    -> display backend

  Start learning in this order:

  1. Linux interfaces: ip, iw, /sys/class/net, monitor-mode interfaces.
  2. Nexmon and brcmfmac: firmware versus kernel module responsibilities.
  3. Bettercap caplets and REST API.
  4. The Pwnagotchi Agent loop in agent.py.
  5. Rust process management, HTTP clients, TOML configuration, and systemd services.

  Useful experiments are:

  iw dev
  iw phy
  iw dev mon0 info
  ip link show mon0
  journalctl -u bettercap.service
  journalctl -u pwnagotchi.service

  The deployed OG 1.5.5 radio path uses the bundled Jay Bettercap 2.41.7-pcapng
  build for capture, channels and handshake events. The old live Bettercap
  2.31.0 failed to open the monitor interface; the bundled build's fallback
  works with the existing driver once wlan0 releases its channel reservation.
  Rust recon remains available as an experiment but is disabled during OG use.
  Association and deauthentication are disabled in the device configuration.
  OG's handshake file counter accepts both pcap and pcapng files.
