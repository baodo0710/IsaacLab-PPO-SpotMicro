# Copyright (c) 2022-2026, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""
FIXES applied vs original:
  - ActionsCfg scale: 0.025 → 0.05  (matches Jetson ACTION_SCALE=0.05)
  - push_robot: velocity_range was (0,0) → real perturbation range
  - reset_robot_joints: scale (1,1) → offset ±0.10 rad for pose diversity
  - base_external_force_torque: removed (was dead, force/torque both 0)
  - contact_forces prim_path: note added — verify against your USD hierarchy
"""

import math
from dataclasses import MISSING

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.managers import CurriculumTermCfg as CurrTerm
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg, RayCasterCfg, patterns
from isaaclab.terrains import TerrainImporterCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR, ISAACLAB_NUCLEUS_DIR
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise

import isaaclab_tasks.manager_based.locomotion.velocity.mdp as mdp

from isaaclab.terrains.config.rough import ROUGH_TERRAINS_CFG  # isort: skip


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

@configclass
class RexSceneCfg(InteractiveSceneCfg):
    """Terrain + robot + sensors."""

    terrain = TerrainImporterCfg(
        prim_path="/World/ground",
        terrain_type="generator",
        terrain_generator=ROUGH_TERRAINS_CFG,
        max_init_terrain_level=5,
        collision_group=-1,
        physics_material=sim_utils.RigidBodyMaterialCfg(
            friction_combine_mode="multiply",
            restitution_combine_mode="multiply",
            static_friction=1.5,
            dynamic_friction=1.5,
        ),
        visual_material=sim_utils.MdlFileCfg(
            mdl_path=f"{ISAACLAB_NUCLEUS_DIR}/Materials/TilesMarbleSpiderWhiteBrickBondHoned/TilesMarbleSpiderWhiteBrickBondHoned.mdl",
            project_uvw=True,
            texture_scale=(0.25, 0.25),
        ),
        debug_vis=False,
    )

    robot: ArticulationCfg = MISSING

    # NOTE: Verify this prim_path matches your USD hierarchy.
    # If your USD was converted directly from URDF, the structure may be
    #   {ENV_REGEX_NS}/Robot/base_link/...   (no 'rex' subdirectory)
    # In that case change to: "{ENV_REGEX_NS}/Robot/.*"
    contact_forces = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Robot/rex/.*",
        history_length=3,
        track_air_time=True,
        debug_vis=False,
    )

    light = AssetBaseCfg(
        prim_path="/World/light",
        spawn=sim_utils.DistantLightCfg(color=(0.75, 0.75, 0.75), intensity=3000.0),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@configclass
class CommandsCfg:
    base_velocity = mdp.UniformVelocityCommandCfg(
        asset_name="robot",
        resampling_time_range=(10.0, 10.0),
        rel_standing_envs=0.02,
        rel_heading_envs=1.0,
        heading_command=True,
        heading_control_stiffness=0.5,
        debug_vis=True,
        ranges=mdp.UniformVelocityCommandCfg.Ranges(
            lin_vel_x=(-0.5, 0.5),
            lin_vel_y=(-0.5, 0.5),
            ang_vel_z=(-0.5, 0.5),
            heading=(-math.pi, math.pi),
        ),
    )


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@configclass
class ActionsCfg:
    # FIXED: scale 0.025 → 0.05 to match Jetson ACTION_SCALE=0.05
    # At 0.025, policy outputs were halved vs real hardware → bad sim-to-real.
    joint_pos = mdp.JointPositionActionCfg(
        asset_name="robot",
        joint_names=[".*"],
        scale=0.05,             # [FIXED: was 0.025]
        use_default_offset=True,
    )


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------

@configclass
class ObservationsCfg:
    @configclass
    class PolicyCfg(ObsGroup):
        base_lin_vel      = ObsTerm(func=mdp.base_lin_vel,       noise=Unoise(n_min=-0.1,  n_max=0.1))
        base_ang_vel      = ObsTerm(func=mdp.base_ang_vel,       noise=Unoise(n_min=-0.05, n_max=0.05))
        projected_gravity = ObsTerm(func=mdp.projected_gravity,  noise=Unoise(n_min=-0.05, n_max=0.05))
        velocity_commands = ObsTerm(func=mdp.generated_commands, params={"command_name": "base_velocity"})
        joint_pos         = ObsTerm(func=mdp.joint_pos_rel,      noise=Unoise(n_min=-0.01, n_max=0.01))
        joint_vel         = ObsTerm(func=mdp.joint_vel_rel,      noise=Unoise(n_min=-0.38, n_max=0.38))
        actions           = ObsTerm(func=mdp.last_action)

        def __post_init__(self):
            self.enable_corruption = True
            self.concatenate_terms = True

    policy: PolicyCfg = PolicyCfg()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@configclass
class EventCfg:
    # -- startup (fire once, set baseline physics) ----------------------------

    physics_material = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
            "static_friction_range":  (0.8, 0.8),
            "dynamic_friction_range": (0.6, 0.6),
            "restitution_range":      (0.0, 0.0),
            "num_buckets": 64,
        },
    )

    add_base_mass = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
            "mass_distribution_params": (-0.05, 0.05),
            "operation": "add",
        },
    )

    base_com = EventTerm(
        func=mdp.randomize_rigid_body_com,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
            "com_range": {"x": (-0.05, 0.05), "y": (-0.05, 0.05), "z": (-0.05, 0.05)},
        },
    )

    # -- reset (fire every episode) -------------------------------------------

    reset_base = EventTerm(
        func=mdp.reset_root_state_uniform,
        mode="reset",
        params={
            "pose_range": {
                "x":   (-0.5, 0.5),
                "y":   (-0.5, 0.5),
                "z":   (0.3,  0.3),
                "yaw": (-3.14, 3.14),
            },
            "velocity_range": {
                "x":     (-0.2, 0.2),
                "y":     (-0.2, 0.2),
                "z":     (-0.1, 0.1),
                "roll":  (-0.2, 0.2),
                "pitch": (-0.2, 0.2),
                "yaw":   (-0.2, 0.2),
            },
        },
    )

    # FIXED: reset_joints_by_offset with ±0.10 rad gives pose diversity
    # Original used reset_joints_by_scale(1.0, 1.0) = always exact default pose
    reset_robot_joints = EventTerm(
        func=mdp.reset_joints_by_offset,   # [FIXED: was reset_joints_by_scale]
        mode="reset",
        params={
            "position_range": (-0.10, 0.10),  # ±5.7° — small but non-zero diversity
            "velocity_range": (-0.05, 0.05),
        },
    )

    # -- interval (fire periodically during episode) --------------------------

    # FIXED: push_robot now applies a real impulse.
    # Original had velocity_range x/y = (0,0) → zero impulse on every push.
    push_robot = EventTerm(
        func=mdp.push_by_setting_velocity,
        mode="interval",
        interval_range_s=(10.0, 15.0),
        params={
            "velocity_range": {
                "x":     (-0.3, 0.3),   # [FIXED: was (0,0)]
                "y":     (-0.2, 0.2),   # [FIXED: was (0,0)]
                "yaw":   (-0.3, 0.3),   # added — rotational disturbance
            },
        },
    )


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

@configclass
class RewardsCfg:
    # Task
    track_lin_vel_xy_exp = RewTerm(
        func=mdp.track_lin_vel_xy_exp,
        weight=1.0,
        params={"command_name": "base_velocity", "std": math.sqrt(0.1)},
    )
    track_ang_vel_z_exp = RewTerm(
        func=mdp.track_ang_vel_z_exp,
        weight=0.5,
        params={"command_name": "base_velocity", "std": math.sqrt(0.1)},
    )

    # Gait
    feet_air_time = RewTerm(
        func=mdp.feet_air_time,
        weight=4.0,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names=".*_toe_link"),
            "command_name": "base_velocity",
            "threshold": 0.15,
        },
    )

    # Stability
    survival         = RewTerm(func=mdp.is_alive,           weight=1.0)
    lin_vel_z_l2     = RewTerm(func=mdp.lin_vel_z_l2,       weight=-5.0)
    ang_vel_xy_l2    = RewTerm(func=mdp.ang_vel_xy_l2,      weight=-0.05)
    flat_orientation_l2 = RewTerm(func=mdp.flat_orientation_l2, weight=-1.0)
    base_height_l2   = RewTerm(
        func=mdp.base_height_l2,
        weight=-5.0,
        params={"target_height": 0.18},
    )

    # Safety
    undesired_contacts = RewTerm(
        func=mdp.undesired_contacts,
        weight=-0.1,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names=".*_shoulder_link"),
            "threshold": 1.0,
        },
    )
    dof_pos_limits   = RewTerm(func=mdp.joint_pos_limits,   weight=-1.0)

    # Smoothness
    dof_torques_l2   = RewTerm(func=mdp.joint_torques_l2,   weight=-1.0e-5)
    dof_acc_l2       = RewTerm(func=mdp.joint_acc_l2,       weight=-1.0e-7)
    action_rate_l2   = RewTerm(func=mdp.action_rate_l2,     weight=-0.01)


# ---------------------------------------------------------------------------
# Terminations
# ---------------------------------------------------------------------------

@configclass
class TerminationsCfg:
    time_out = DoneTerm(func=mdp.time_out, time_out=True)
    base_contact = DoneTerm(
        func=mdp.illegal_contact,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names="base_link"),
            "threshold": 10.0,
        },
    )


# ---------------------------------------------------------------------------
# Curriculum
# ---------------------------------------------------------------------------

@configclass
class CurriculumCfg:
    terrain_levels = CurrTerm(func=mdp.terrain_levels_vel)


# ---------------------------------------------------------------------------
# Top-level env config
# ---------------------------------------------------------------------------

@configclass
class LocomotionVelocityRoughEnvCfg(ManagerBasedRLEnvCfg):
    scene:        RexSceneCfg    = RexSceneCfg(num_envs=4096, env_spacing=2.5)
    observations: ObservationsCfg = ObservationsCfg()
    actions:      ActionsCfg     = ActionsCfg()
    commands:     CommandsCfg    = CommandsCfg()
    rewards:      RewardsCfg     = RewardsCfg()
    terminations: TerminationsCfg = TerminationsCfg()
    events:       EventCfg       = EventCfg()
    curriculum:   CurriculumCfg  = CurriculumCfg()

    def __post_init__(self):
        self.decimation = 4
        self.episode_length_s = 20.0
        self.sim.dt = 0.002                    # control dt = 0.008 s = 125 Hz
        self.sim.solver_type = "TGS"
        self.sim.render_interval = self.decimation
        self.sim.physics_material = self.scene.terrain.physics_material
        self.sim.physx.gpu_max_rigid_patch_count = 10 * 2**15

        if self.scene.contact_forces is not None:
            self.scene.contact_forces.update_period = self.sim.dt

        if getattr(self.curriculum, "terrain_levels", None) is not None:
            if self.scene.terrain.terrain_generator is not None:
                self.scene.terrain.terrain_generator.curriculum = True
        else:
            if self.scene.terrain.terrain_generator is not None:
                self.scene.terrain.terrain_generator.curriculum = False
