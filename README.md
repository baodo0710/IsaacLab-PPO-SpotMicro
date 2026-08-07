# Rex — Quadruped Locomotion in Isaac Lab

<div align="center">
    
![Rex Quadruped Render](docs/images/rex_hero.png)
**A high-fidelity reinforcement learning framework for SpotMicro-class quadruped locomotion**

[![Isaac Lab](https://img.shields.io/badge/Built%20on-Isaac%20Lab-orange)](https://isaac-sim.github.io/IsaacLab/)
[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Pending-lightgrey)]()

</div>

---

## Overview

**Rex** is a custom manager-based RL task extension for [Isaac Lab](https://isaac-sim.github.io/IsaacLab/) that brings a servo-actuated SpotMicro-class quadruped (https://spotmicroai.readthedocs.io/en/latest/) into NVIDIA's GPU-accelerated simulation framework. Built on Isaac Lab's velocity-tracking locomotion pipeline, Rex enables large-scale parallel training of robust, terrain-adaptive gaits with full domain randomization.

The robot asset (`spot2.usd`) is modeled after the open-source SpotMicro platform and driven by realistic MG996R servo actuator dynamics.

<!-- TODO: Add side-by-side sim vs. real photo here -->
<div align="center">

![Simulation vs Reality](docs/images/sim_vs_real.png)
*Left: Isaac Lab simulation | Right: Target hardware platform*

</div>

---

## Hardware & Electronics

### Custom CAD Model

<!-- TODO: Add CAD model renders/screenshots here -->
<div align="center">

![CAD Model](docs/images/cad_model.png)
*Custom CAD design of the SpotMicro-class chassis and leg assemblies*

</div>

### Electronics & Wiring

<!-- TODO: Add wiring diagram / electronics photo here -->
<div align="center">

![Electronics Wiring](docs/images/electronics_wiring.png)
*Wiring diagram: STM32 controller, MG996R servos, power distribution, and sensors*

</div>

---

## Environments

Six Gym-registered tasks cover the full training-to-deployment lifecycle:

| Task ID | Config Class | Description |
|---|---|---|
| `Isaac-Velocity-Flat-Rex-v0` | `RexFlatEnvCfg` | Velocity tracking on flat terrain with full domain randomization. Trains robust forward locomotion with randomized friction, mass, and external perturbations across 4096 parallel environments. |
| `Isaac-Velocity-Flat-Rex-Play-v0` | `RexFlatEnvCfg_PLAY` | Flat terrain evaluation variant with all domain randomization disabled. Use for policy validation, benchmarking, and sim-to-real transfer. Deterministic behavior for reproducible gait analysis. |
| `Isaac-Velocity-Rough-Rex-v0` | `RexRoughEnvCfg` | Velocity tracking on procedurally generated rough terrain with height-field noise, slope variation, and obstacle gaps. Domain randomization includes terrain geometry, friction, and push recovery. |
| `Isaac-Velocity-Rough-Rex-Play-v0` | `RexRoughEnvCfg_PLAY` | Rough terrain evaluation with fixed terrain seeds and no randomization. Validates generalization to unseen rough terrain layouts and measures robustness under consistent conditions. |
| `Isaac-Stand-Rex-v0` | `RexStandEnvCfg` | Static balancing task with zero velocity command. Trains postural stability with randomized CoM shifts, external pushes, and joint configuration noise. Foundation for standing recovery behaviors. |
| `Isaac-Stand-Rex-Play-v0` | `RexStandEnvCfg_PLAY` | Standing evaluation with deterministic conditions. Measures static stability margin, sway amplitude, and disturbance rejection without training noise. |

<!-- TODO: Add terrain comparison image -->
<div align="center">

![Terrain Types](docs/images/terrain_comparison.png)
*Flat (top) vs. procedurally generated rough terrain (bottom)*

</div>

---

## System Architecture

```
rex/
├── __init__.py                  # Gym environment registration (6 tasks)
├── rex_velocity_env_cfg.py      # Base LocomotionVelocityRoughEnvCfg
│                                 #   → scene, rewards, events, terrain
├── quad_ws_articulation.py      # QUAD_WS_CFG
│                                 #   → robot articulation + MG996R actuator model
├── flat_env_cfg.py              # Flat-terrain training & play configs
├── rough_env_cfg.py             # Rough-terrain training & play configs
├── stand_env_cfg.py             # Standing / balance task configs
└── agents/
    ├── rsl_rl_ppo_cfg.py        # RSL-RL PPO runner configurations
    ├── rl_games_flat_ppo_cfg.yaml
    ├── rl_games_rough_ppo_cfg.yaml
    ├── skrl_flat_ppo_cfg.yaml
    └── skrl_rough_ppo_cfg.yaml
```
## Multi-Framework RL Support

Rex ships with pre-tuned hyperparameters for three major Isaac Lab RL backends:

| Framework | Status | Notes |
|---|---|---|
| **RSL-RL** | ✅ Ready | On-policy PPO with recurrent state encoders |

---

## Quick Start

### Prerequisites

- [Isaac Sim](https://developer.nvidia.com/isaac-sim) ≥ 4.0
- [Isaac Lab](https://isaac-sim.github.io/IsaacLab/) ≥ 1.0
- Python 3.10+

### Installation

Rex is designed as a native Isaac Lab task extension. Place the package under:

```bash
source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/config/rex/
```

Or register it as an external extension per the [official docs](https://isaac-sim.github.io/IsaacLab/).

> **⚠️ Asset Path:** Update the `usd_path` in `quad_ws_articulation.py` to point to your local `spot2.usd` before training.

### Training

**Flat terrain (RSL-RL):**
```bash
python scripts/rsl_rl/train.py --task Isaac-Velocity-Flat-Rex-v0 --headless
```

**Rough terrain (RSL-RL):**
```bash
python scripts/rsl_rl/train.py --task Isaac-Velocity-Rough-Rex-v0 --headless
```


<div align="center">

![Trained Gait](docs/images/trained_gait.gif)
*Trained trotting gait on flat terrain*

</div>

---

## Results

Resulting videos are attached in docs folder

---

## Sim-to-Sim Validation

Trained policies are cross-validated in a secondary simulator before hardware deployment, to catch policy artifacts specific to Isaac Lab's physics before they hit the real robot.

Sim-to-Sim videos are attached in docs folder

---

## License

*Pending*
