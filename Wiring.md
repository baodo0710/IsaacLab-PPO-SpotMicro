# SpotMicro Wiring Pinout 

Pinout for every connector on the hardware modules.

---

## 20A 300W Buck Converter 

6–40V input, adjustable output. Set to **6V** for servo rail.

| Screw Terminal | Label | Connect To | Wire Color |
|---|---|---|---|
| Left + | IN+ | Battery positive  | XT60 connector |
| Left − | IN− | Battery negative  | XT60 connector |
| Right + | OUT+ | PCA9685 V+ pin, 5V buck input | 🔴 16 AWG |
| Right − | OUT− | Common GND bus | ⚫ 16 AWG |

---

## 4S LiPo Battery Connector (XT60)

| Pin | Signal | Connect To | Wire |
|---|---|---|---|
| 1 | BAT+ | IN+ | XT60 |
| 2 | BAT− | IN− | XT60 |

---

## 5V 3A Buck Converter

Steps 6V down to **5V** for logic.

| Pin / Pad | Label | Connect To | Wire |
|---|---|---|---|
| IN+ | VIN+ | OUT+ (6V rail) | 🟠 18 AWG |
| IN− | GND | Common GND | ⚫ 18 AWG |
| OUT+ | VOUT | STM32 5V, Jetson 5V | 🟠 18 AWG |
| OUT− | GND | Common GND | ⚫ 18 AWG |

---

## U1 — STM32F446RET6 


### Power & Reset

| Pin # | Name | Connect To | 
|---|---|---|
| CN6 - 8 | Vin | Buck Vout | 
| CN6 - 7 | GND | Buck GND | 
| CN6 - 5 | 5V | MPU6050 + PCA9685 VCC | 
| CN6 - 6 | GND | MPU6050 + PCA9685 + Jetson GND |

### I2C (to MPU6050 + PCA9685)

| Pin # | Name | Function | Connect To |
|---|---|---|
| CN5 - 10 | PB8 | I2C1_SCL | MPU6050 SCL, PCA9685 SCL |
| CN5 - 9 | PB9 | I2C1_SDA | MPU6050 SDA, PCA9685 SDA |

### UART (to Jetson Orin Nano)

| Pin # | Name | Function | Connect To |
|---|---|---|---|
| CN5 - 1 | PA9 | USART1_TX | Jetson Pin 10 (UART0_RX) |
| CN9 - 3 | PA10 | USART1_RX | Jetson Pin 8 (UART0_TX) |

> Baud rate: **115200, 8N1** 


## PCA9685 (16-Channel PWM Servo Driver)

### PWM Output Headers (right side, 16× 3-pin servo connectors)

| Channel | Silkscreen | Connect To | Servo |
|---|---|---|---|
| 0 | PWM 0 | J3 pin 1 (signal) | FL Hip |
| 1 | PWM 1 | J4 pin 1 (signal) | FL Knee |
| 2 | PWM 2 | J5 pin 1 (signal) | FL Ankle |
| 3 | PWM 3 | J9 pin 1 (signal) | RR Hip |
| 4 | PWM 4 | J10 pin 1 (signal) | RR Knee |
| 5 | PWM 5 | J11 pin 1 (signal) | RR Ankle |
| 6 | PWM 6 | J6 pin 1 (signal) | RL Hip |
| 7 | PWM 7 | J7 pin 1 (signal) | RL Knee |
| 8 | PWM 8 | J8 pin 1 (signal) | RL Ankle |
| 9 | PWM 9 | J12 pin 1 (signal) | FR Hip |
| 10 | PWM 10 | J13 pin 1 (signal) | FR Knee |
| 11 | PWM 11 | J14 pin 1 (signal) | FR Ankle |
| 12–15 | PWM 12–15 | — (spare) | Expansion |

---

### Servo Assignment

| Leg | Joint | PCA9685 Ch |
|---|---|---|
| Front-Left | Hip | 0 |
| Front-Left | Knee | 1 |
| Front-Left | Ankle | 2 |
| Rear-Left | Hip | 3 |
| Rear-Left | Knee | 4 |
| Rear-Left | Ankle | 5 |
| Rear-Right | Hip | 6 |
| Rear-Right | Knee | 7 |
| Rear-Right | Ankle | 8 |
| Front-Right | Hip | 9 |
| Front-Right | Knee | 10 |
| Front-Right | Ankle | 11 |

---

*Last updated: 2026-08-08*
