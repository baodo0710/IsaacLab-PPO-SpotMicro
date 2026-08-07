# Rex — Isaac Lab Locomotion Task Extension

A custom [Isaac Lab](https://isaac-sim.github.io/IsaacLab/) manager-based RL task
extension for **Rex**, a small servo-actuated quadruped (`quad_ws`, USD asset
`spot2.usd`), built on Isaac Lab's velocity-tracking locomotion framework, a modified version using SpotMicro (https://spotmicroai.readthedocs.io/en/latest/).

Six Gym tasks are registered:

| Task ID | Config | Description |
|---|---|---|
| `Isaac-Velocity-Flat-Rex-v0` | `flat_env_cfg.RexFlatEnvCfg` | Velocity tracking on flat terrain |
| `Isaac-Velocity-Flat-Rex-Play-v0` | `flat_env_cfg.RexFlatEnvCfg_PLAY` | Flat, no domain randomization (eval/deploy) |
| `Isaac-Velocity-Rough-Rex-v0` | `rough_env_cfg.RexRoughEnvCfg`* | Velocity tracking on rough/generated terrain |
| `Isaac-Velocity-Rough-Rex-Play-v0` | `rough_env_cfg.RexRoughEnvCfg_PLAY`* | Rough, no domain randomization (eval/deploy) |
| `Isaac-Stand-Rex-v0` | `stand_env_cfg.RexStandEnvCfg` | Standing/balance task, zero velocity command |
| `Isaac-Stand-Rex-Play-v0` | `stand_env_cfg.RexStandEnvCfg_PLAY` | Standing eval variant |

RL framework configs are provided for **rsl_rl**, **rl_games**, and **skrl**
under `rex/agents/`.

\* See **Known issue** below — these two entry points currently point at class
names that don't exist yet in `rough_env_cfg.py`.

## Layout

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
