# stand_env_cfg.py
from isaaclab.utils import configclass
from .rough_env_cfg import RexRoughEnvCfg
from isaaclab.managers import RewardTermCfg as RewTerm, TerminationTermCfg as DoneTerm
import isaaclab_tasks.manager_based.locomotion.velocity.mdp as mdp
import math
import isaaclab.sim as sim_utils
from isaaclab.managers import SceneEntityCfg

@configclass
class RexStandEnvCfg(RexRoughEnvCfg):
    def __post_init__(self):
        super().__post_init__()

        # Setup - slightly taller for stability
        self.scene.robot.init_state.pos = (0.0, 0.0, 0.25)
        self.actions.joint_pos.scale = 0.02  

        # Zero velocity commands
        self.commands.base_velocity.ranges.lin_vel_x = (0.0, 0.0)
        self.commands.base_velocity.ranges.lin_vel_y = (0.0, 0.0)
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)

        self.episode_length_s = 10.0
        self.events.push_robot = None
        self.events.base_external_force_torque = None

        # Flat terrain
        self.scene.terrain.terrain_type = "plane"
        self.scene.terrain.terrain_generator = None
        self.curriculum = None

        # Remove height scanner
        self.scene.height_scanner = None
        self.observations.policy.height_scan = None

        # REWARD BALANCE - reduce action rate, increase others
        self.rewards.flat_orientation_l2.weight = -7.0  # REDUCED from -10.0
        self.rewards.base_height = RewTerm(
            func=mdp.base_height_l2,
            weight=-10.0,  
            params={"target_height": 0.25, "asset_cfg": SceneEntityCfg("robot")}
        )

        # Smooth movement - REDUCED penalties
        self.rewards.ang_vel_xy_l2.weight = -1.0  # REDUCED from -2.0
        self.rewards.lin_vel_z_l2.weight = -1.0   # REDUCED from -2.0
        self.rewards.action_rate_l2.weight = -0.005  
        self.rewards.dof_acc_l2.weight = -1.0e-5     # REDUCED from -1e-4

        # DISABLE contact penalties - not needed for standing
        self.rewards.undesired_contacts = None
        self.rewards.feet_contact = None

        # Remove velocity tracking
        self.rewards.track_lin_vel_xy_exp = None
        self.rewards.track_ang_vel_z_exp = None
        self.rewards.feet_air_time = None

        # Lenient termination
        self.terminations.bad_orientation = DoneTerm(
            func=mdp.bad_orientation,
            params={"limit_angle": 1.0},  # INCREASED from 0.8 (more lenient)
        )
