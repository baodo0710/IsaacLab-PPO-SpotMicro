from isaaclab.utils import configclass
from isaaclab.terrains import TerrainGeneratorCfg
from isaaclab.terrains.trimesh.mesh_terrains_cfg import MeshPlaneTerrainCfg
from isaaclab.managers import (
    RewardTermCfg as RewTerm,
    SceneEntityCfg,
    TerminationTermCfg as DoneTerm,
    EventTermCfg,
    ObservationTermCfg as ObsTerm,
)
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise
import isaaclab_tasks.manager_based.locomotion.velocity.mdp as mdp
import math

from .quad_ws_articulation import QUAD_WS_CFG
from .rex_velocity_env_cfg import LocomotionVelocityRoughEnvCfg as RexVelocityRoughEnvCfg


@configclass
class RexFlatEnvCfg(RexVelocityRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        self.scene.robot = QUAD_WS_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        self.scene.height_scanner = None
        self.curriculum.terrain_levels = None

        self.scene.terrain.terrain_type = "generator"
        self.scene.terrain.terrain_generator = TerrainGeneratorCfg(
            curriculum=False,
            size=(8.0, 8.0),
            sub_terrains={"flat": MeshPlaneTerrainCfg(proportion=1.0)},
            num_rows=10,
            num_cols=20,
            horizontal_scale=0.1,
            vertical_scale=0.005,
            border_width=4,
        )

        self.observations.policy.base_lin_vel.noise      = Unoise(n_min=-0.2,  n_max=0.2)
        self.observations.policy.base_ang_vel.noise      = Unoise(n_min=-0.15, n_max=0.15)
        self.observations.policy.projected_gravity.noise = Unoise(n_min=-0.1,  n_max=0.1)
        self.observations.policy.joint_pos.noise         = Unoise(n_min=-0.03, n_max=0.03)

        self.events.randomize_rigid_body_mass = EventTermCfg(
            func=mdp.randomize_rigid_body_mass,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
                "mass_distribution_params": (0.8, 1.2),
                "operation": "scale",
                "distribution": "uniform",
            },
        )

        self.events.randomize_rigid_body_com = EventTermCfg(
            func=mdp.randomize_rigid_body_com,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
                "com_range": {"x": (-0.035, 0.035), "y": (-0.035, 0.035), "z": (-0.035, 0.035)},
            },
        )

        self.events.randomize_rigid_body_material = EventTermCfg(
            func=mdp.randomize_rigid_body_material,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
                "static_friction_range":  (0.65, 1.35),
                "dynamic_friction_range": (0.65, 1.35),
                "restitution_range":      (0.0, 0.1),
                "num_buckets": 64,
            },
        )

        self.events.randomize_joint_parameters = EventTermCfg(
            func=mdp.randomize_joint_parameters,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
                "friction_distribution_params": (0.85, 1.15),
                "armature_distribution_params": (0.85, 1.15),
                "operation": "scale",
                "distribution": "uniform",
            },
        )

        self.events.randomize_actuator_gains = EventTermCfg(
            func=mdp.randomize_actuator_gains,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
                "stiffness_distribution_params": (0.85, 1.15),
                "damping_distribution_params":   (0.85, 1.15),
                "operation": "scale",
                "distribution": "uniform",
            },
        )

        self.events.reset_robot_joints = EventTermCfg(
            func=mdp.reset_joints_by_offset,
            mode="reset",
            params={
                "position_range": (-0.04, 0.04),
                "velocity_range": (-0.1, 0.1),
            },
        )

        self.events.push_robot = EventTermCfg(
            func=mdp.push_by_setting_velocity,
            mode="interval",
            interval_range_s=(10.0, 15.0),
            params={
                "velocity_range": {
                    "x":   (-0.15, 0.15),
                    "y":   (-0.1, 0.1),
                    "yaw": (-0.15, 0.15),
                },
            },
        )

        if hasattr(mdp, "action_delay"):
            self.events.action_delay = EventTermCfg(
                func=mdp.action_delay,
                mode="reset",
                params={
                    "min_delay": 1,
                    "max_delay": 2,
                },
            )

        self.rewards.track_lin_vel_xy_exp.weight = 20.0
        self.rewards.track_lin_vel_xy_exp.params["std"] = math.sqrt(0.15)

        self.rewards.track_ang_vel_z_exp.weight = 8.0
        self.rewards.track_ang_vel_z_exp.params["std"] = math.sqrt(0.1)

        self.rewards.feet_air_time.weight = 40.0
        self.rewards.feet_air_time.params["threshold"] = 0.04

        self.rewards.base_height_l2.weight = -3.0
        self.rewards.base_height_l2.params["target_height"] = 0.17

        self.rewards.flat_orientation_l2.weight = -15.0
        self.rewards.lin_vel_z_l2.weight = -3.0
        self.rewards.dof_acc_l2.weight = -2.5e-7
        self.rewards.action_rate_l2.weight = -0.01

        self.rewards.survival.weight = 0.0
        self.rewards.joint_vel_l2 = RewTerm(
            func=mdp.joint_vel_l2,
            weight=-0.1,
        )

        self.rewards.dof_torques_l2.weight = -1.0e-5

        self.commands.base_velocity.ranges.lin_vel_x = (-0.8, 0.8)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.2, 0.2)
        self.commands.base_velocity.ranges.ang_vel_z = (-0.3, 0.3)
        self.commands.base_velocity.rel_standing_envs = 0.0
        self.commands.base_velocity.resampling_time_range = (4.0, 6.0)

        self.terminations.base_contact = DoneTerm(
            func=mdp.illegal_contact,
            params={
                "sensor_cfg": SceneEntityCfg("contact_forces", body_names=["base_link"]),
                "threshold": 10.0,
            },
        )

        self.episode_length_s = 20.0


@configclass
class RexFlatEnvCfg_PLAY(RexFlatEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 50
        self.scene.env_spacing = 1.0
        self.observations.policy.enable_corruption = False

        self.events.randomize_rigid_body_mass     = None
        self.events.randomize_rigid_body_com      = None
        self.events.randomize_rigid_body_material = None
        self.events.randomize_joint_parameters    = None
        self.events.randomize_actuator_gains      = None
        self.events.push_robot                    = None
        if hasattr(self.events, "action_delay"):
            self.events.action_delay = None

        self.commands.base_velocity.ranges.lin_vel_x = (-0.8, 0.8)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.2, 0.2)
        self.commands.base_velocity.ranges.ang_vel_z = (-0.3, 0.3)
