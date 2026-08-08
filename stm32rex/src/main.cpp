/*
 * Rex Quadruped — STM32F446RE firmware
 * ====================================
 * Role: dumb translator between Jetson and PCA9685+MPU6050.
 *   - Receives target joint angles in URDF radians, hardware leg-by-leg order
 *   - Sends raw IMU + commanded joint state at 125 Hz
 *   - Watchdog: if Jetson silent > 500 ms, slowly return to safe stand
 *
 * Joint indexing convention (HARDWARE LEG-BY-LEG, FL→RL→RR→FR, sh→leg→foot):
 *   [0]  FL shoulder    [1]  FL leg    [2]  FL foot
 *   [3]  RL shoulder    [4]  RL leg    [5]  RL foot
 *   [6]  RR shoulder    [7]  RR leg    [8]  RR foot
 *   [9]  FR shoulder   [10]  FR leg   [11]  FR foot
 *
 * The Jetson is responsible for converting the policy's DOF-grouped order
 * (4 shoulders, 4 legs, 4 feet) into this hardware order before sending.
 *
 * Protocol: 115200 baud, headers 0xA5 0x5A, radians end-to-end.
 * Control loop: 125 Hz (matches Isaac Lab training rate).
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <MPU6050.h>

// ────────────────────────────────────────────────────────────
// CONSTANTS
// ────────────────────────────────────────────────────────────
#define NUM_LEGS         4
#define DOF              3
#define NUM_JOINTS       (NUM_LEGS * DOF)   // 12

#define CONTROL_HZ       125
#define CONTROL_PERIOD_US (1000000UL / CONTROL_HZ)  // 8000 us

#define SERVO_FREQ_HZ    50    // PCA9685 PWM frequency for servos

#define WATCHDOG_MS      500   // declare comm loss after this silence
#define WATCHDOG_RAMP_MS 500   // duration of ramp to safe pose

#define BOOT_GRACE_MS    10000 // ignore watchdog for first N ms after boot

#define DEG2RAD          0.0174532925f
#define RAD2DEG          57.2957795f

// ────────────────────────────────────────────────────────────
// HARDWARE WIRING — ADJUST IF YOU REWIRE
// ────────────────────────────────────────────────────────────
// PCA9685 channel for each [leg][joint] in hardware order.
// Legs: 0=FL, 1=RL, 2=RR, 3=FR.  Joints: 0=shoulder, 1=leg, 2=foot.
const uint8_t SERVO_CHANNEL[NUM_LEGS][DOF] = {
    { 0,  1,  2},   // FL
    { 3,  4,  5},   // RL
    { 6,  7,  8},   // RR
    { 9, 10, 11},   // FR
};

// Sign of physical rotation relative to URDF rotation.
// +1 = servo turns the same direction as the URDF expects.
// -1 = servo is mounted mirrored, so command is negated before going to PCA.
const int8_t SERVO_DIR[NUM_LEGS][DOF] = {
    { 1,  -1, -1},   // FL
    {-1,  -1, -1},   // RL
    { 1,  1,  1},   // RR
    {-1,  1,  1},   // FR
};

// PCA9685 tick at the URDF zero pose for each servo.
// Found by manually finding the tick where each joint physically reads its
// URDF-zero orientation.
const uint16_t SERVO_TICK_AT_ZERO[NUM_LEGS][DOF] = {
    {297, 307, 437},   // FL
    {307, 307, 412},   // RL
    {307, 307, 187},   // RR
    {307, 307, 187},   // FR
};

// Hard mechanical/safe ticks — never command outside these.
const uint16_t SERVO_TICK_MIN[NUM_LEGS][DOF] = {
    {220, 150, 150},
    {220, 150, 140},
    {220, 150, 150},
    {220, 150, 150},
};
const uint16_t SERVO_TICK_MAX[NUM_LEGS][DOF] = {
    {395, 600, 700},
    {395, 600, 675},
    {395, 600, 600},
    {395, 600, 600},
};

// ────────────────────────────────────────────────────────────
// JOINT LIMITS (URDF radians) — same order as DOF index
// These are the limits Isaac Lab actually trained against (verified from
// robot.data.joint_pos_limits in the training env).
// ────────────────────────────────────────────────────────────
const float JOINT_LIMIT_MIN_RAD[DOF] = {
    -1.00f,    // shoulder: ±1.0 rad
    -2.17f,    // leg:      [-2.17, +0.97]
    -1.50f,    // foot:     [-1.50, +2.59]
};
const float JOINT_LIMIT_MAX_RAD[DOF] = {
    +1.00f,
    +0.97f,
    +2.59f,
};

// Servo's full mechanical range in URDF degrees, for tick conversion.
// MG996R: ~180° physical rotation. We pick a generous mapping then clip.
// These define how many ticks correspond to 1 degree (for tick<->angle math).
const float SERVO_FULL_RANGE_DEG[DOF] = {
    114.0f,    // shoulder: spans -57° to +57° = 114° (matches old code)
    180.0f,    // leg:      spans -124° to +56° = 180°
    154.0f,    // foot:     spans -6° to +148° = 154°
};

// ────────────────────────────────────────────────────────────
// SAFE POSE — wide-stance crouch the robot returns to on watchdog
// In URDF radians, hardware leg-by-leg order [shoulder, leg, foot].
// ────────────────────────────────────────────────────────────
const float SAFE_POSE_RAD[NUM_LEGS][DOF] = {
    { 0.0f, -0.52f, 1.05f},   // FL  ~ 0°, -30°, 60°
    { 0.0f, -0.52f, 1.05f},   // RL
    { 0.0f, -0.52f, 1.05f},   // RR
    { 0.0f, -0.52f, 1.05f},   // FR
};

// Default Isaac Lab pose (informational; Jetson sends this on boot).
// Not used directly here, but the joints settle here once Jetson connects.
// const float DEFAULT_POSE_RAD[DOF] = { 0.069f, -1.047f, 1.570f };

// ────────────────────────────────────────────────────────────
// PROTOCOL
// ────────────────────────────────────────────────────────────
// OBS packet (STM32 → Jetson, sent at 125 Hz):
//   header[2] = 0xA5 0x5A
//   type[1]   = 0x01
//   payload   = 30 floats = 120 bytes:
//                 accel[3]   raw, 'g' units
//                 gyro[3]    raw, deg/s
//                 jpos[12]   commanded URDF rad, hardware order
//                 jvel[12]   d(jpos)/dt, rad/s
//   checksum[1] = XOR of payload bytes
// Total: 3 + 120 + 1 = 124 bytes
//
// ACT packet (Jetson → STM32, expected at 125 Hz):
//   header[2] = 0xA5 0x5A
//   type[1]   = 0x02
//   payload   = 12 floats = 48 bytes:
//                 target_jpos[12]  URDF rad, hardware leg-by-leg order
//   checksum[1] = XOR of payload bytes
// Total: 3 + 48 + 1 = 52 bytes
// ────────────────────────────────────────────────────────────
#define HEADER_1     0xA5
#define HEADER_2     0x5A
#define TYPE_OBS     0x01
#define TYPE_ACT     0x02

#define OBS_FLOATS   30
#define ACT_FLOATS   12
#define OBS_SIZE     (3 + OBS_FLOATS * 4 + 1)   // 124
#define ACT_SIZE     (3 + ACT_FLOATS * 4 + 1)   // 52

// ────────────────────────────────────────────────────────────
// HARDWARE
// ────────────────────────────────────────────────────────────
Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver(0x40);
MPU6050 mpu;
HardwareSerial JetsonSerial(PA10, PA9);   // RX=PA10, TX=PA9
// 921600 baud is required for 125 Hz bidirectional. At 115200, the link
// saturates around 65 Hz with this packet size. STM32F446 and Jetson UART
// both handle 921600 cleanly.
#define JETSON_BAUD  921600

// ────────────────────────────────────────────────────────────
// STATE
// ────────────────────────────────────────────────────────────
// 12-element flat arrays in hardware leg-by-leg order, URDF radians.
float commandedRad[NUM_JOINTS]      = {0};   // what we last wrote to servos
float prevCommandedRad[NUM_JOINTS]  = {0};   // for velocity estimation
float jointVelRad[NUM_JOINTS]       = {0};   // estimated joint velocity rad/s

// Latest target from Jetson (gets applied each control tick).
float targetRad[NUM_JOINTS] = {0};

// Watchdog state.
uint32_t lastValidPacketMs = 0;
bool     watchdogActive    = false;
float    watchdogStartRad[NUM_JOINTS] = {0};
uint32_t watchdogStartMs   = 0;

// IMU.
struct {
    float ax, ay, az;   // raw g
    float gx, gy, gz;   // raw deg/s
} imu;

// Action receive state machine.
uint8_t  actBuf[ACT_SIZE];
uint8_t  actIdx       = 0;
uint32_t bootTimeMs   = 0;

// Control timing.
uint32_t lastControlUs = 0;
uint32_t loopCount     = 0;
const float DT = 1.0f / (float)CONTROL_HZ;

// ────────────────────────────────────────────────────────────
// HELPERS
// ────────────────────────────────────────────────────────────
inline uint8_t legOf(uint8_t j)   { return j / DOF; }
inline uint8_t dofOf(uint8_t j)   { return j % DOF; }

uint8_t xorChecksum(const uint8_t *data, uint16_t len) {
    uint8_t cs = 0;
    for (uint16_t i = 0; i < len; i++) cs ^= data[i];
    return cs;
}

// Convert URDF radians → PCA9685 ticks for given (leg, dof).
// Applies SERVO_DIR sign flip, clamps to mechanical tick limits.
uint16_t urdfRadToTicks(uint8_t leg, uint8_t dof, float rad_urdf) {
    // Apply sign convention to get physical rotation
    float rad_physical = rad_urdf * (float)SERVO_DIR[leg][dof];
    float deg_physical = rad_physical * RAD2DEG;

    // Tick range available
    float tickRange = (float)(SERVO_TICK_MAX[leg][dof] - SERVO_TICK_MIN[leg][dof]);
    float ticksPerDeg = tickRange / SERVO_FULL_RANGE_DEG[dof];

    float ticks = (float)SERVO_TICK_AT_ZERO[leg][dof] + deg_physical * ticksPerDeg;

    // Hard clamp
    if (ticks < SERVO_TICK_MIN[leg][dof]) ticks = SERVO_TICK_MIN[leg][dof];
    if (ticks > SERVO_TICK_MAX[leg][dof]) ticks = SERVO_TICK_MAX[leg][dof];
    return (uint16_t)ticks;
}

// Apply a target angle (URDF rad) to the servo, with limit clipping.
// Updates commandedRad[] with the actually-applied value.
void applyJoint(uint8_t j, float rad_urdf) {
    uint8_t d = dofOf(j);
    if (rad_urdf < JOINT_LIMIT_MIN_RAD[d]) rad_urdf = JOINT_LIMIT_MIN_RAD[d];
    if (rad_urdf > JOINT_LIMIT_MAX_RAD[d]) rad_urdf = JOINT_LIMIT_MAX_RAD[d];
    commandedRad[j] = rad_urdf;

    uint16_t ticks = urdfRadToTicks(legOf(j), d, rad_urdf);
    pca.setPWM(SERVO_CHANNEL[legOf(j)][d], 0, ticks);
}

void applyAllTargets(const float *targets) {
    for (uint8_t j = 0; j < NUM_JOINTS; j++) {
        applyJoint(j, targets[j]);
    }
}

void applySafePose() {
    for (uint8_t j = 0; j < NUM_JOINTS; j++) {
        applyJoint(j, SAFE_POSE_RAD[legOf(j)][dofOf(j)]);
    }
}

// ────────────────────────────────────────────────────────────
// IMU
// ────────────────────────────────────────────────────────────
void readIMU() {
    int16_t ax, ay, az, gx, gy, gz;
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    // ±2g range default → 16384 LSB/g. ±250 deg/s range → 131 LSB/(deg/s).
    imu.ax = ax / 16384.0f;
    imu.ay = ay / 16384.0f;
    imu.az = az / 16384.0f;
    imu.gx = gx / 131.0f;
    imu.gy = gy / 131.0f;
    imu.gz = gz / 131.0f;
}

// ────────────────────────────────────────────────────────────
// VELOCITY ESTIMATION (commanded-position differencing)
// MG996R has no encoder, so this is a noisy proxy. Match Isaac Lab's
// joint_vel observation noise (±0.38 rad/s) on the Jetson side.
// ────────────────────────────────────────────────────────────
void updateVelocities() {
    for (uint8_t j = 0; j < NUM_JOINTS; j++) {
        jointVelRad[j] = (commandedRad[j] - prevCommandedRad[j]) / DT;
        prevCommandedRad[j] = commandedRad[j];
    }
}

// ────────────────────────────────────────────────────────────
// COMMS
// ────────────────────────────────────────────────────────────
void sendObservation() {
    static uint8_t pkt[OBS_SIZE];
    float obs[OBS_FLOATS];

    // 0..2: accel raw g
    obs[0] = imu.ax;
    obs[1] = imu.ay;
    obs[2] = imu.az;
    // 3..5: gyro raw deg/s
    obs[3] = imu.gx;
    obs[4] = imu.gy;
    obs[5] = imu.gz;
    // 6..17: commanded joint pos URDF rad, hardware order
    for (uint8_t j = 0; j < NUM_JOINTS; j++) obs[6 + j] = commandedRad[j];
    // 18..29: joint vel rad/s, hardware order
    for (uint8_t j = 0; j < NUM_JOINTS; j++) obs[18 + j] = jointVelRad[j];

    pkt[0] = HEADER_1;
    pkt[1] = HEADER_2;
    pkt[2] = TYPE_OBS;
    memcpy(&pkt[3], obs, OBS_FLOATS * sizeof(float));
    pkt[OBS_SIZE - 1] = xorChecksum(&pkt[3], OBS_FLOATS * sizeof(float));
    JetsonSerial.write(pkt, OBS_SIZE);
}

void receiveActions() {
    while (JetsonSerial.available()) {
        uint8_t b = JetsonSerial.read();

        if (actIdx == 0) {
            if (b == HEADER_1) actBuf[actIdx++] = b;
            continue;
        }
        if (actIdx == 1) {
            if (b == HEADER_2) {
                actBuf[actIdx++] = b;
            } else if (b == HEADER_1) {
                actBuf[0] = b;
                actIdx = 1;
            } else {
                actIdx = 0;
            }
            continue;
        }
        if (actIdx == 2) {
            if (b == TYPE_ACT) {
                actBuf[actIdx++] = b;
            } else {
                actIdx = 0;
            }
            continue;
        }

        actBuf[actIdx++] = b;
        if (actIdx == ACT_SIZE) {
            actIdx = 0;
            uint8_t cs = xorChecksum(&actBuf[3], ACT_FLOATS * sizeof(float));
            if (cs != actBuf[ACT_SIZE - 1]) continue;  // bad packet, drop

            // Valid packet — copy 12 floats into targetRad
            memcpy(targetRad, &actBuf[3], ACT_FLOATS * sizeof(float));
            lastValidPacketMs = millis();
            if (watchdogActive) {
                watchdogActive = false;
                Serial.println("[wd] comms restored");
            }
        }
    }
}

// ────────────────────────────────────────────────────────────
// WATCHDOG: ramp from current commanded to safe pose over WATCHDOG_RAMP_MS
// ────────────────────────────────────────────────────────────
void enterWatchdog() {
    watchdogActive = true;
    watchdogStartMs = millis();
    for (uint8_t j = 0; j < NUM_JOINTS; j++) {
        watchdogStartRad[j] = commandedRad[j];
    }
    Serial.println("[wd] entering safe-pose ramp");
}

void applyWatchdogRamp() {
    uint32_t elapsed = millis() - watchdogStartMs;
    float t = (float)elapsed / (float)WATCHDOG_RAMP_MS;
    if (t > 1.0f) t = 1.0f;
    // Smoothstep for gentler motion
    float s = t * t * (3.0f - 2.0f * t);
    for (uint8_t j = 0; j < NUM_JOINTS; j++) {
        float safe_target = SAFE_POSE_RAD[legOf(j)][dofOf(j)];
        float interp = watchdogStartRad[j] + (safe_target - watchdogStartRad[j]) * s;
        applyJoint(j, interp);
    }
}

// ────────────────────────────────────────────────────────────
// SETUP
// ────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    JetsonSerial.begin(JETSON_BAUD);
    Wire.begin();
    Wire.setClock(400000);   // 400 kHz I2C for faster MPU reads

    // PCA9685
    pca.begin();
    pca.setOscillatorFrequency(27000000);
    pca.setPWMFreq(SERVO_FREQ_HZ);
    delay(10);

    // Initialize state to safe pose, write to servos
    for (uint8_t j = 0; j < NUM_JOINTS; j++) {
        float r = SAFE_POSE_RAD[legOf(j)][dofOf(j)];
        commandedRad[j]     = r;
        prevCommandedRad[j] = r;
        targetRad[j]        = r;
    }
    applySafePose();
    Serial.println("[init] servos -> safe pose");

    // MPU6050
    mpu.initialize();
    if (!mpu.testConnection()) {
        Serial.println("[init] MPU6050 NOT FOUND — halting");
        while (1) { delay(1000); }
    }
    // Note: hardware offsets here are device-specific. Recalibrate if you
    // swap the IMU. Final orientation correction happens on the Jetson.
    mpu.setXAccelOffset(-1742);
    mpu.setYAccelOffset(304);
    mpu.setZAccelOffset(0);
    mpu.setXGyroOffset(34);
    mpu.setYGyroOffset(-89);
    mpu.setZGyroOffset(177);
    Serial.println("[init] IMU ready");

    bootTimeMs        = millis();
    lastValidPacketMs = bootTimeMs + BOOT_GRACE_MS;   // grace period
    lastControlUs     = micros();
    Serial.println("[init] ready @ 125 Hz, awaiting Jetson");
}

// ────────────────────────────────────────────────────────────
// LOOP
// ────────────────────────────────────────────────────────────
void loop() {
    // Always service UART, regardless of control timing.
    receiveActions();

    // Rate-limit control to CONTROL_HZ.
    uint32_t now = micros();
    if ((uint32_t)(now - lastControlUs) < CONTROL_PERIOD_US) return;
    lastControlUs += CONTROL_PERIOD_US;
    // Catch up if we fell behind by more than one period (avoid drift accumulation)
    if ((uint32_t)(now - lastControlUs) > CONTROL_PERIOD_US * 4) {
        lastControlUs = now;
    }
    loopCount++;

    // Sense
    readIMU();

    // Decide whether comms are alive
    bool inGrace = (millis() - bootTimeMs) < BOOT_GRACE_MS;
    bool stale   = (millis() - lastValidPacketMs) > WATCHDOG_MS;

    if (stale && !inGrace) {
        if (!watchdogActive) enterWatchdog();
        applyWatchdogRamp();
    } else {
        // Normal: apply latest target from Jetson
        applyAllTargets(targetRad);
    }

    // Update velocity estimate AFTER applying (so commandedRad reflects latest)
    updateVelocities();

    // Send observation back to Jetson
    sendObservation();

    // 1 Hz heartbeat
    if (loopCount % CONTROL_HZ == 0) {
        Serial.print("[hb] ");
        Serial.print(loopCount / CONTROL_HZ);
        Serial.print("s | accel z="); Serial.print(imu.az, 2);
        Serial.print(" | FL_sh="); Serial.print(commandedRad[0], 2);
        Serial.print(" FL_leg="); Serial.print(commandedRad[1], 2);
        Serial.print(" FL_foot="); Serial.print(commandedRad[2], 2);
        if (watchdogActive) Serial.print(" [WD]");
        Serial.println();
    }
}