# OG learning feasibility experiment

This experiment uses the repository's OG `Environment`, `Parameter`, featurizer,
and reward implementation, with `A2C(MlpLstmPolicy, ...)` and the `[ai.params]`
values from `pwnagotchi/defaults.toml`. It substitutes only an in-memory agent
receiver and a deterministic simulated epoch source. It never imports the real
agent, connects to Bettercap, invokes plugins, or operates a radio.

The simulated source cycles through normalized channel histograms and finite
interaction counts. This validates execution and checkpoint behavior, not policy
quality or learning effectiveness in a physical environment. Channels 1–13 model
the Zero 2 W's 2.4 GHz band. OG still represents all 140 histogram bins.

## Acceptance

`benchmark.py train --output DIR` performs inference and 100 actual environment
steps / A2C optimizer updates, records all three returned training statistics
(policy loss, value loss, entropy), and requires finite losses and changed weights.
It saves the stock Stable Baselines checkpoint, exact reference parameter arrays,
and deterministic inference outputs.

`benchmark.py restore --output DIR` must run in a **new process**. It assigns
`A2C.load(...)`'s return value, compares every parameter with `numpy.array_equal`,
compares deterministic action and recurrent-state output, and performs another
100 updates with finite losses and changed weights. Each phase writes JSON only
after all assertions pass. Reuse a fresh output directory for each complete run.

Step latency includes rollout/inference and optimizer work; the first step also
includes learning setup. Update latency measures the original `_train_step` call.
Instrumentation wraps the call and does not alter its arguments or return value.
Peak RSS is Linux `getrusage` high-water RSS, including imports and model creation.

The Pi supervisor requires active OG and Bettercap services and no configured
swap. It reserves 60 MiB from initial available memory, sets a cgroup memory cap
and `MemorySwapMax=0`, polls `MemAvailable` every 100 ms, checks normal-service
states and restart counts roughly every second, and stops on a sample below
50 MiB. A worker OOM is a **failed experiment**, even if normal services survive.
Each phase is limited to 15 minutes. Sampling cannot prove that no sub-100 ms dip
occurred; the cgroup cap adds a separate bound on worker memory consumption.

## Isolation and checkpoints

The test runtime is ARM64 Python 3.7.17 with TensorFlow 1.15.5, Stable Baselines
2.7.0, and Gym 0.14.0. The TensorFlow wheel is a community binary from
[noahzhy/tf-aarch64](https://github.com/noahzhy/tf-aarch64/tree/75a83c8e83b43834a1de73fa11822967e4634ad3),
not an official TensorFlow ARM64 release. Its SHA-256 is
`3002e4e405b3c7d6c0453304aa40fd64353ffefa03e5b99ad722816bbc762052`.
The publisher does not supply sufficient build provenance to reconstruct that
binary from source. Exact binary replay is the reproducibility boundary.

The repository's OG loader calls `a2c.load(path, env)` and ignores the returned
model. Integration must instead use the returned model. This experiment does
not patch the running OG service. Stock SB 2.7.0 checkpoints save policy/model
parameters and hyperparameters, but do not promise a bit-exact continuation of
optimizer accumulators, environment state, RNG state, or an in-flight LSTM state.
The acceptance test requires identical model weights and subsequent training,
not an identical stochastic training trajectory after restart.

`Environment.params` is mutable class state extended by each constructor. Each
benchmark process constructs exactly one environment, matching the intended
worker lifecycle and avoiding duplicate channel actions. Integration must avoid
repeated construction in one process or address that bug separately.

## Integration gate

Only a passing **Pi** report permits planning the AI worker integration. An
import-only or host-only pass does not meet the gate. The future worker must
receive ordered epoch observations/rewards and return validated personality
parameters, including policy-selected channels. The modern OG process should
apply those parameters while Bettercap remains the sole radio owner.

Rust migration follows the validated OG baseline. Before Rust owns radio
operations it must accept policy-driven channel selection and emit the epoch
observations and operation-completion events required by the OG reward function.
There must be one channel controller at a time.
