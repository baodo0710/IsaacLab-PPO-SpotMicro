from isaaclab.utils import configclass
from isaaclab.terrains import TerrainGeneratorCfg
from isaaclab.terrains.trimesh.mesh_terrains_cfg import MeshPlaneTerrainCfg
from isaaclab.managers import RewardTermCfg as RewTerm, ObservationTermCfg as ObsTerm, SceneEntityCfg, TerminationTermCfg as DoneTerm, EventTermCfg
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise
from isaaclab.sensors import ContactSensorCfg
import isaaclab_tasks.manager_based.locomotion.velocity.mdp as mdp
import math

from .quad_ws_articulation import QUAD_WS_CFG
from .rex_velocity_env_cfg import LocomotionVelocityRoughEnvCfg as RexVelocityRoughEnvCfg

@configclass
class RexFlatEnvCfg(RexVelocityRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        self.scene.robot = QUAD_WS_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        # ============================================
        # NO HEIGHT SCANNER - Flat terrain only
        # Reduces sim-to-real gap (no lidar needed)
        # ============================================
        self.scene.height_scanner = None

        # ============================================
        # FLAT TERRAIN ONLY
        # ============================================
        self.scene.terrain.terrain_type = "generator"
        self.scene.terrain.terrain_generator = TerrainGeneratorCfg(
            curriculum=False,  # No curriculum - flat only
            size=(8.0, 8.0),
            sub_terrains={
                "flat": MeshPlaneTerrainCfg(proportion=1.0),  # 100% flat
            },
            num_rows=10,
            num_cols=20,
            horizontal_scale=0.1,
            vertical_scale=0.005,
            border_width=4,
        )

        # ============================================
        # MAXIMUM DOMAIN RANDOMIZATION (Sim-to-Real)
        # ============================================
        
        # 1. Mass variation (±20%) - Battery, payload [^23^]
        self.events.randomize_rigid_body_mass = EventTermCfg(
            func=mdp.randomize_rigid_body_mass,
            mode="startup",
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
                "mass_distribution_params": (0.8, 1.2),
                "operation": "scale",
                "distribution": "uniform",
            },
        )

        # 2. Center of Mass shift (±3cm) - Assembly tolerance
        self.events.randomize_rigid_body_com = EventTermCfg(
            func=mdp.randomize_rigid_body_com,
            mode="startup",
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
                "com_range": {"x": (-0.03, 0.03), "y": (-0.03, 0.03), "z": (-0.03, 0.03)},
            },
        )

        # 3. Robot friction (0.5-1.5x) - Floor surface variations [^23^]
        self.events.randomize_rigid_body_material = EventTermCfg(
            func=mdp.randomize_rigid_body_material,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
                "static_friction_range": (0.5, 1.5),
                "dynamic_friction_range": (0.5, 1.5),
                "restitution_range": (0.0, 0.1),
                "num_buckets": 64,
            },
        )

        # 4. Joint friction/damping (0.7-1.3x) - Gear wear, temperature [^20^]
        self.events.randomize_joint_parameters = EventTermCfg(
            func=mdp.randomize_joint_parameters,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
                "friction_distribution_params": (0.7, 1.3),
                "armature_distribution_params": (0.8, 1.2),
                "operation": "scale",
                "distribution": "uniform",
            },
        )

        # 5. Actuator gains (±30%) - Motor model mismatch [^20^]
        self.events.randomize_actuator_gains = EventTermCfg(
            func=mdp.randomize_actuator_gains,
            mode="reset",
            params={
                "asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
                "stiffness_distribution_params": (0.7, 1.3),
                "damping_distribution_params": (0.7, 1.3),
                "operation": "scale",
                "distribution": "uniform",
            },
        )

        # 6. External pushes (±1N) - Bumps, interaction
        self.events.push_robot = EventTermCfg(
            func=mdp.push_by_setting_velocity,
            mode="interval",
            interval_range_s=(5.0, 10.0),  # More frequent than rough
            params={
                "velocity_range": {
                    "x": (-0.5, 0.5),
                    "y": (-0.5, 0.5),
                },
            },
        )

        # 7. Reset with variation
        self.events.reset_robot_joints = EventTermCfg(
            func=mdp.reset_joints_by_scale,
            mode="reset",
            params={
                "position_range": (0.8, 1.2),  # 80-120% of default
                "velocity_range": (-0.1, 0.1),
            },
        )

        # ============================================
        # OBSERVATION NOISE (Sim-to-Real) [^17^][^24^]
        # ============================================
        # Add noise to proprioceptive observations
        self.observations.policy.base_lin_vel.noise = Unoise(n_min=-0.1, n_max=0.1)
        self.observations.policy.base_ang_vel.noise = Unoise(n_min=-0.05, n_max=0.05)
        self.observations.policy.projected_gravity.noise = Unoise(n_min=-0.05, n_max=0.05)
        self.observations.policy.joint_pos.noise = Unoise(n_min=-0.01, n_max=0.01)
        self.observations.policy.joint_vel.noise = Unoise(n_min=-0.5, n_max=0.5)

        # ============================================
        # OPTIMIZED REWARDS FOR FLAT + SIM-TO-REAL
        # ============================================
        
        # Task: High weight for accurate tracking
        self.rewards.track_lin_vel_xy_exp.weight = 25.0
        self.rewards.track_lin_vel_xy_exp.params["std"] = math.sqrt(0.1)
        self.rewards.track_ang_vel_z_exp.weight = 12.0
        self.rewards.track_ang_vel_z_exp.params["std"] = math.sqrt(0.2)

        # Feet: Proper stepping (not shuffle), achievable threshold
        self.rewards.feet_air_time.weight = 8.0
        self.rewards.feet_air_time.params["threshold"] = 0.08  # 80ms proper step

        # Survival: LOW weight - don't reward standing still
        self.rewards.survival = RewTerm(func=mdp.is_alive, weight=0.5)

        # Stability
        self.rewards.base_height_l2 = RewTerm(
            func=mdp.base_height_l2,
            weight=-2.0,
            params={"target_height": 0.18}
        )
        self.rewards.flat_orientation_l2.weight = -3.0  # Prevent tilting
        self.rewards.lin_vel_z_l2.weight = -4.0  # No hopping

        # Smoothness: Critical for small robots
        self.rewards.dof_acc_l2.weight = -2.0e-7
        self.rewards.action_rate_l2.weight = -0.05  # Anti-jitter

        # Efficiency
        self.rewards.dof_torques_l2.weight = -1.0e-5
        self.rewards.dof_pos_limits.weight = -2.0

        # Contacts
        self.rewards.body_contact = RewTerm(
            func=mdp.undesired_contacts,
            weight=-4.0,
            params={
                "sensor_cfg": SceneEntityCfg("contact_forces", body_names=["base_link"]),
                "threshold": 1.0,
            },
        )

        # ============================================
        # COMMANDS: Force movement
        # ============================================
        self.commands.base_velocity.ranges.lin_vel_x = (-0.5, 1.0)
        self.commands.base_velocity.ranges.lin_vel_y = (-0.3, 0.3)
        self.commands.base_velocity.ranges.ang_vel_z = (-0.5, 0.5)
        self.commands.base_velocity.rel_standing_envs = 0.05  # 5% stand, 95% move
        self.commands.base_velocity.resampling_time_range = (6.0, 10.0)

        # ============================================
        # TERMINATIONS
        # ============================================
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
        self.scene.env_spacing = 2.5
        self.observations.policy.enable_corruption = False  # No noise for deployment
        # Disable domain randomization for play
        self.events.randomize_rigid_body_mass = None
        self.events.randomize_rigid_body_com = None
        self.events.randomize_rigid_body_material = None
        self.events.randomize_joint_parameters = None
        self.events.randomize_actuator_gains = None
        self.events.push_robot = None
