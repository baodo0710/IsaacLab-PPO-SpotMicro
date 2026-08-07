import isaaclab.sim as sim_utils
from isaaclab.actuators import DCMotorCfg
from isaaclab.assets.articulation import ArticulationCfg
from isaaclab.sim.spawners.materials.physics_materials_cfg import RigidBodyMaterialCfg

# ---------------------------------------------------------------------------
# Actuator
# ---------------------------------------------------------------------------
# MG996R datasheet:
#   stall torque   : ~1.1 N·m  @ 6 V
#   no-load speed  : ~6.0 rad/s @ 6 V
# Kp=25, Kd=0.5 are typical values for this class of servo at these limits.
# DCMotorCfg applies a linear torque-speed de-rating above the no-load speed,
# so the curve now actually saturates — unlike the original config which never
# reached 100 N·m in normal operation.

REX_SIMPLE_ACTUATOR_CFG = DCMotorCfg(
    joint_names_expr=[
        "motor_.*_shoulder",   # motor_front_left_shoulder, etc.
        "motor_.*_leg",        # motor_front_left_leg, etc.
        "foot_motor_.*",       # foot_motor_front_left, etc.
    ],
    saturation_effort=1.1,     # N·m — MG996R stall torque  [FIXED: was 100.0]
    effort_limit=1.1,          # N·m                         [FIXED: was 100.0]
    velocity_limit=6.0,        # rad/s — MG996R no-load speed [FIXED: was 7.5]
    stiffness={".*": 25.0},    # N·m/rad — realistic Kp       [FIXED: was 70.0]
    damping={".*": 0.5},       # N·m·s/rad — realistic Kd     [FIXED: was 7.0]
    armature=0.01,
)

# ---------------------------------------------------------------------------
# Physics material (terrain / foot contact)
# ---------------------------------------------------------------------------
ROBOT_ROUGH_TERRAIN_MATERIAL = RigidBodyMaterialCfg(
    static_friction=1.0,
    dynamic_friction=1.0,
    restitution=0.0,
)

# ---------------------------------------------------------------------------
# Articulation
# ---------------------------------------------------------------------------
QUAD_WS_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path="/home/baodoo/quad_ws/src/spot/spot2.usd",
        activate_contact_sensors=True,
        collision_props=sim_utils.CollisionPropertiesCfg(
            contact_offset=0.005,
            rest_offset=0.0,
        ),
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            retain_accelerations=False,
            linear_damping=0.0,        # removed artificial body damping — let physics drive it
            angular_damping=0.0,
            max_linear_velocity=1000.0,
            max_angular_velocity=1000.0,
            max_depenetration_velocity=0.1,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=True,
            solver_position_iteration_count=64,
            solver_velocity_iteration_count=4,
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.17),
        joint_pos={
            "motor_.*_shoulder": 0.069,
            "motor_.*_leg":     -0.87,
            "foot_motor_.*":     1.745,
        },
    ),
    actuators={"legs": REX_SIMPLE_ACTUATOR_CFG},
    soft_joint_pos_limit_factor=1.0,
)
