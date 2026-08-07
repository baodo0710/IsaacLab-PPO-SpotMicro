# Rex — Quadruped Locomotion in Isaac Lab

&lt;div align="center"&gt;

&lt;!-- TODO: Add hero image / robot render here --&gt;
![Rex Quadruped Render](docs/images/rex_hero.png)

**A high-fidelity reinforcement learning framework for SpotMicro-class quadruped locomotion**

[![Isaac Lab](https://img.shields.io/badge/Built%20on-Isaac%20Lab-orange)](https://isaac-sim.github.io/IsaacLab/)
[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Pending-lightgrey)]()

&lt;/div&gt;

---

## Overview

**Rex** is a custom manager-based RL task extension for [Isaac Lab](https://isaac-sim.github.io/IsaacLab/) that brings a servo-actuated SpotMicro-class quadruped into NVIDIA's GPU-accelerated simulation framework. Built on Isaac Lab's velocity-tracking locomotion pipeline, Rex enables large-scale parallel training of robust, terrain-adaptive gaits with full domain randomization.

The robot asset (`spot2.usd`) is modeled after the open-source SpotMicro platform and driven by realistic MG996R servo actuator dynamics.

&lt;!-- TODO: Add side-by-side sim vs. real photo here --&gt;
&lt;div align="center"&gt;

![Simulation vs Reality](docs/images/sim_vs_real.png)
*Left: Isaac Lab simulation | Right: Target hardware platform*

&lt;/div&gt;

---

## Environments

Six Gym-registered tasks cover the full training-to-deployment lifecycle:

| Task ID | Config Class | Description |
|---|---|---|
| `Isaac-Velocity-Flat-Rex-v0` | `RexFlatEnvCfg` | Velocity tracking on flat terrain with full domain randomization |
| `Isaac-Velocity-Flat-Rex-Play-v0` | `RexFlatEnvCfg_PLAY` | Flat terrain, zero randomization — optimized for evaluation & sim-to-real |
| `Isaac-Velocity-Rough-Rex-v0` | `RexRoughEnvCfg` | Velocity tracking on procedurally generated rough terrain |
| `Isaac-Velocity-Rough-Rex-Play-v0` | `RexRoughEnvCfg_PLAY` | Rough terrain evaluation variant |
| `Isaac-Stand-Rex-v0` | `RexStandEnvCfg` | Static balancing with zero velocity command |
| `Isaac-Stand-Rex-Play-v0` | `RexStandEnvCfg_PLAY` | Standing policy evaluation variant |

&lt;!-- TODO: Add terrain comparison image --&gt;
&lt;div align="center"&gt;

![Terrain Types](docs/images/terrain_comparison.png)
*Flat (top) vs. procedurally generated rough terrain (bottom)*

&lt;/div&gt;

---

## System Architecture

```
rex/
├── __init__.py                  # gym.register() calls for all 6 tasks
├── rex_velocity_env_cfg.py      # base LocomotionVelocityRoughEnvCfg (scene, rewards, events, etc.)
├── quad_ws_articulation.py      # QUAD_WS_CFG — robot articulation + MG996R actuator model
├── flat_env_cfg.py              # RexFlatEnvCfg / RexFlatEnvCfg_PLAY
├── rough_env_cfg.py             # rough-terrain env config
├── stand_env_cfg.py             # RexStandEnvCfg / RexStandEnvCfg_PLAY
└── agents/
    ├── __init__.py
    ├── rsl_rl_ppo_cfg.py         # RexRoughPPORunnerCfg, RexFlatPPORunnerCfg
    ├── rl_games_flat_ppo_cfg.yaml
    ├── rl_games_rough_ppo_cfg.yaml
    ├── skrl_flat_ppo_cfg.yaml
    └── skrl_rough_ppo_cfg.yaml
```

## Setup

This is a task extension meant to live inside (or alongside) an Isaac Lab
installation, e.g. under
`source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/config/rex/`,
or registered as an external extension per Isaac Lab's
[adding a new environment](https://isaac-sim.github.io/IsaacLab/) docs.
Adjust the import path in `__init__.py` if you place it elsewhere.

The robot's USD asset is currently referenced by an absolute local path in
`quad_ws_articulation.py`:

```python
usd_path="/home/baodoo/quad_ws/src/spot/spot2.usd"
```

Update this to wherever `spot2.usd` lives on the machine actually running
training, or swap it for a Nucleus/relative path before pushing to a shared
remote.

## License

No license file is included yet 
