# Rex — Quadruped Locomotion in Isaac Lab

<div align="center">

<!-- TODO: Add hero image / robot render here -->
![Rex Quadruped Render](docs/images/rex_hero.png)

**A high-fidelity reinforcement learning framework for SpotMicro-class quadruped locomotion**

[![Isaac Lab](https://img.shields.io/badge/Built%20on-Isaac%20Lab-orange)](https://isaac-sim.github.io/IsaacLab/)
[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Pending-lightgrey)]()

</div>

---

## Overview

**Rex** is a custom manager-based RL task extension for [Isaac Lab](https://isaac-sim.github.io/IsaacLab/) that brings a servo-actuated SpotMicro-class quadruped into NVIDIA's GPU-accelerated simulation framework. Built on Isaac Lab's velocity-tracking locomotion pipeline, Rex enables large-scale parallel training of robust, terrain-adaptive gaits with full domain randomization.

The robot asset (`spot2.usd`) is modeled after the open-source SpotMicro platform and driven by realistic MG996R servo actuator dynamics.

<!-- TODO: Add side-by-side sim vs. real photo here -->
<div align="center">

![Simulation vs Reality](docs/images/sim_vs_real.png)
*Left: Isaac Lab simulation | Right: Target hardware platform*

</div>

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

<!-- TODO: Add pipeline diagram -->
<div align="center">

![Training Pipeline](docs/images/training_pipeline.png)
*Manager-based RL pipeline: Observations → Policy → Actuator Model → Simulation*

</div>

---

## Multi-Framework RL Support

Rex ships with pre-tuned hyperparameters for three major Isaac Lab RL backends:

| Framework | Status | Notes |
|---|---|---|
| **RSL-RL** | ✅ Ready | On-policy PPO with recurrent state encoders |
| **RL-Games** | ✅ Ready | GPU-accelerated PPO with adaptive learning rates |
| **SKRL** | ✅ Ready | Modular RL with shared observation normalization |

<!-- TODO: Add training curves comparison -->
<div align="center">

![Training Curves](docs/images/training_curves.png)
*Sample learning curves: mean reward vs. policy iterations (4096 environments)*

</div>

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

**Standing task (SKRL):**
```bash
python scripts/skrl/train.py --task Isaac-Stand-Rex-v0 --headless
```

<div align="center">

![Trained Gait](docs/images/trained_gait.gif)
*Trained trotting gait on flat terrain*

</div>

---

## Results

| Task | Mean Reward | Success Rate | Notes |
|---|---|---|---|
| Flat Velocity Tracking | --- | --- | In training |
| Rough Velocity Tracking | --- | --- | In training |
| Standing Balance | --- | --- | In training |

<div align="center">

![Gait Analysis](docs/images/gait_analysis.png)
*Foot contact schedule and base velocity tracking*

</div>

---

## Roadmap

- [x] Base velocity-tracking locomotion framework
- [x] Flat & rough terrain environment variants
- [x] Standing / balance task
- [x] Multi-framework RL agent configs (RSL-RL, RL-Games, SKRL)
- [ ] Rough-terrain class naming alignment (`RexRoughEnvCfg`)
- [ ] Symmetry-augmented RSL-RL runner configs
- [ ] Sim-to-real validation pipeline
- [ ] Hardware deployment on SpotMicro

<div align="center">

![Hardware Platform](docs/images/hardware_platform.jpg)
*Target hardware: SpotMicro with MG996R servos*

</div>

---

## Citation

If you use Rex in your research, please consider citing:

```bibtex
@misc{rex2026,
  title={Rex: SpotMicro Locomotion in Isaac Lab},
  author={Your Name},
  year={2026},
  url={https://github.com/yourusername/rex}
}
```

## License

*Pending* — Consider adding an open-source license (e.g., MIT or BSD-3-Clause) before public release.
