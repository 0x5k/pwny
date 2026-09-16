#!/usr/bin/env python3
"""Radio-free OG environment test. Run train and restore in separate processes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['train', 'restore'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=100)
    args = parser.parse_args()
    assert args.steps >= 100
    assert platform.machine() == 'aarch64'
    assert sys.version_info[:2] == (3, 7)
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    import numpy as np
    import tensorflow as tf
    import gym
    import stable_baselines
    import toml
    from stable_baselines import A2C
    from stable_baselines.common.policies import MlpLstmPolicy
    from stable_baselines.common.vec_env import DummyVecEnv
    from pwnagotchi.ai.gym import Environment
    from pwnagotchi.ai.reward import RewardFunction
    from pwnagotchi.mesh.wifi import NumChannels

    class Agent:
        def __init__(self):
            self.steps = 0
            self.policy = None

        def supported_channels(self):
            return list(range(1, 14))

        def on_ai_policy(self, params):
            # Deliberately no real Agent, plugins, Bettercap, or radio access.
            self.policy = params

        def on_ai_step(self):
            self.steps += 1

        def is_training(self):
            return True

        def training_epochs(self):
            return args.steps

    class SimulatedEpoch:
        def __init__(self):
            self.n = 0
            self.reward = RewardFunction()

        def wait_for_epoch_data(self):
            self.n += 1
            n = self.n
            hist = np.zeros(NumChannels, dtype=np.float32)
            hist[(n - 1) % 13] = 1.0
            state = dict(aps_histogram=hist, sta_histogram=np.roll(hist, 1),
                         peers_histogram=np.roll(hist, 2), duration_secs=5 + n % 55,
                         inactive_for_epochs=0, active_for_epochs=1,
                         blind_for_epochs=0, sad_for_epochs=0, bored_for_epochs=0,
                         missed_interactions=n % 2, num_hops=1 + n % 13,
                         num_deauths=2 + n % 4, num_associations=1 + n % 3,
                         num_handshakes=n % 3)
            state['reward'] = self.reward(n, state)
            assert np.isfinite(state['reward'])
            return state

    params = toml.load(str(ROOT / 'pwnagotchi/defaults.toml'))['ai']['params']
    agent = Agent()
    raw_env = Environment(agent, SimulatedEpoch())
    env = DummyVecEnv([lambda: raw_env])
    checkpoint = args.output / 'brain.nn'
    reference = args.output / 'weights.npz'
    if args.phase == 'train':
        model = A2C(MlpLstmPolicy, env, **params)
    else:
        # load is a classmethod returning a NEW model. OG currently discards it.
        model = A2C.load(str(checkpoint), env=env)
    assert all(getattr(model, name) == value for name, value in params.items())

    def weights():
        return model.sess.run(model.params)

    before = weights()
    restored = None
    observation = np.zeros((1,) + raw_env.observation_space.shape, dtype=np.float32)
    action, recurrent_state = model.predict(observation, deterministic=True)
    assert all(np.isfinite(x).all() for x in (action, recurrent_state))
    if args.phase == 'restore':
        with np.load(str(reference)) as saved:
            assert len(before) == len(saved.files)
            assert all(np.array_equal(w, saved['arr_%d' % i]) for i, w in enumerate(before))
        expected = np.load(str(args.output / 'inference.npz'))
        assert np.array_equal(action, expected['action'])
        assert np.array_equal(recurrent_state, expected['state'])
        restored = True

    losses, update_seconds, step_seconds = [], [], []
    original_train_step = model._train_step

    def measured_train_step(*a, **kw):
        start = time.monotonic()
        result = original_train_step(*a, **kw)
        update_seconds.append(time.monotonic() - start)
        assert np.isfinite(result).all(), 'nonfinite training loss'
        losses.append([float(x) for x in result])
        return result

    model._train_step = measured_train_step
    previous = [time.monotonic()]

    def callback(_locals, _globals):
        now = time.monotonic()
        step_seconds.append(now - previous[0])
        previous[0] = now

    training_started = time.monotonic()
    model.learn(total_timesteps=args.steps, callback=callback, seed=155)
    training_seconds = time.monotonic() - training_started
    after = weights()
    assert agent.steps == args.steps and len(losses) == args.steps
    assert all(np.isfinite(w).all() for w in after)
    changed = sum(not np.array_equal(a, b) for a, b in zip(before, after))
    assert changed > 0, 'training did not change weights'
    if args.phase == 'train':
        model.save(str(checkpoint))
        np.savez(str(reference), *after)
        action, recurrent_state = model.predict(observation, deterministic=True)
        np.savez(str(args.output / 'inference.npz'), action=action, state=recurrent_state)

    def stats(values):
        return dict(mean=float(np.mean(values)), p50=float(np.percentile(values, 50)),
                    p95=float(np.percentile(values, 95)), maximum=float(np.max(values)))

    source_paths = ['pwnagotchi/ai/gym.py', 'pwnagotchi/ai/featurizer.py',
                  'pwnagotchi/ai/parameter.py', 'pwnagotchi/ai/reward.py',
                    'pwnagotchi/mesh/wifi.py', 'pwnagotchi/defaults.toml',
                    'experiments/og-learning/benchmark.py']
    report = dict(status='pass', phase=args.phase, python=sys.version,
                  architecture=platform.machine(), tensorflow=tf.__version__,
                  tensorflow_git_version=getattr(tf, 'GIT_VERSION', None),
                  tensorflow_compiler=getattr(tf, 'COMPILER_VERSION', None),
                  stable_baselines=stable_baselines.__version__, gym=gym.__version__,
                  params=params, channels=agent.supported_channels(),
                  observation_shape=raw_env.observation_space.shape,
                  action_dimensions=len(raw_env.action_space.nvec),
                  steps=agent.steps, finite_losses=True, losses=losses,
                  changed_weight_arrays=changed, total_weight_arrays=len(after),
                  restored_identical_weights_and_inference=restored,
                  training_seconds=training_seconds, step_seconds=stats(step_seconds),
                  update_seconds=stats(update_seconds),
                  peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                  total_seconds=time.monotonic() - started,
                  source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_paths})
    (args.output / (args.phase + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'losses'}, indent=2))


if __name__ == '__main__':
    main()
