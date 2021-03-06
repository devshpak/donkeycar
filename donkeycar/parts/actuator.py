"""
actuators.py
Classes to control the motors and servos. These classes
are wrapped in a mixer class before being used in the drive loop.
"""

import time
import donkeycar as dk

class AMSL293D:
    """
    L293D controler or "Arduino Motor Shield L293D from Raspberry Pi (using RPi.GPIO)".
    """
    def __init__(self):
        from AMSpi import AMSpi

        amspi = AMSpi()
        amspi.set_74HC595_pins(21, 20, 16)
        amspi.set_L293D_pins(5, 6, 13, 19)
        self.amspi = amspi

        self.throttleL = 0
        self.throttleR = 0

    def runLeftMotors(self, throttle):
        self.amspi.run_dc_motors(dc_motors = [self.amspi.DC_Motor_1, self.amspi.DC_Motor_2],
                                 speed = self.convert(abs(throttle)),
                                 clockwise = throttle > 0)

    def runRightMotors(self, throttle):
        self.amspi.run_dc_motor(dc_motor = self.amspi.DC_Motor_3,
                                 speed = self.convert(abs(throttle)),
                                 clockwise = throttle > 0)
        self.amspi.run_dc_motor(dc_motor = self.amspi.DC_Motor_4,
                                 speed = self.convert(abs(throttle)),
                                 clockwise = not(throttle > 0))

    def run(self, steering, throttle):
        '''
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        '''

        if throttle > 1 or throttle < -1:
            raise ValueError( "Speed must be between 1(forward) and -1(reverse)")

        if steering > 1 or steering < -1:
            raise ValueError( "Steering must be between 1 and -1")

        if (steering == 0):
            self.throttleL = throttle
            self.throttleR = throttle
        elif ( steering > 0 and throttle > 0 ):       # Quadrant 1
            self.throttleL = throttle
            self.throttleR = throttle - steering

        elif ( steering < 0 and throttle > 0 ):     # Quadrant 2
            self.throttleL = throttle + steering
            self.throttleR = throttle

        elif ( steering > 0 and throttle < 0 ):     # Quadrant 4
            self.throttleL = throttle
            self.throttleR = throttle + steering

        elif ( steering < 0 and throttle < 0 ):     # Quadrant 3
            self.throttleL = throttle - steering
            self.throttleR = throttle

        self.runLeftMotors(self.throttleL)
        self.runRightMotors(self.throttleR)

    def convert(self, value):
        return int(dk.util.data.map_range(abs(value), 0, 1, 0, 100))

class PCA9685:
    """
    PWM motor controler using PCA9685 boards.
    This is used for most RC Cars
    """
    def __init__(self, channel, frequency=60):
        import Adafruit_PCA9685
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = Adafruit_PCA9685.PCA9685()
        self.pwm.set_pwm_freq(frequency)
        self.channel = channel

    def set_pulse(self, pulse):
        try:
            self.pwm.set_pwm(self.channel, 0, pulse)
        except OSError as err:
            print("Unexpected issue setting PWM (check wires to motor board): {0}".format(err))

    def run(self, pulse):
        self.set_pulse(pulse)


class PWMSteering:
    """
    Wrapper over a PWM motor cotnroller to convert angles to PWM pulses.
    """
    LEFT_ANGLE = -1
    RIGHT_ANGLE = 1

    def __init__(self, controller=None,
                 left_pulse=290, right_pulse=490):

        self.controller = controller
        self.left_pulse = left_pulse
        self.right_pulse = right_pulse

    def run(self, angle):
        # map absolute angle to angle that vehicle can implement.
        pulse = dk.util.data.map_range(
            angle,
            self.LEFT_ANGLE, self.RIGHT_ANGLE,
            self.left_pulse, self.right_pulse
        )

        self.controller.set_pulse(pulse)

    def shutdown(self):
        self.run(0)  # set steering straight


class PWMThrottle:
    """
    Wrapper over a PWM motor cotnroller to convert -1 to 1 throttle
    values to PWM pulses.
    """
    MIN_THROTTLE = -1
    MAX_THROTTLE = 1

    def __init__(self,
                 controller=None,
                 max_pulse=300,
                 min_pulse=490,
                 zero_pulse=350):

        self.controller = controller
        self.max_pulse = max_pulse
        self.min_pulse = min_pulse
        self.zero_pulse = zero_pulse

        # send zero pulse to calibrate ESC
        self.controller.set_pulse(self.zero_pulse)
        time.sleep(1)

    def run(self, throttle):
        if throttle > 0:
            pulse = dk.util.data.map_range(throttle,
                                           0, self.MAX_THROTTLE,
                                           self.zero_pulse, self.max_pulse)
        else:
            pulse = dk.util.data.map_range(throttle,
                                           self.MIN_THROTTLE, 0,
                                           self.min_pulse, self.zero_pulse)

        self.controller.set_pulse(pulse)

    def shutdown(self):
        self.run(0)  # stop vehicle


class Adafruit_DCMotor_Hat:
    """
    Adafruit DC Motor Controller
    Used for each motor on a differential drive car.
    """
    def __init__(self, motor_num):
        from Adafruit_MotorHAT import Adafruit_MotorHAT
        import atexit

        self.FORWARD = Adafruit_MotorHAT.FORWARD
        self.BACKWARD = Adafruit_MotorHAT.BACKWARD
        self.mh = Adafruit_MotorHAT(addr=0x60)

        self.motor = self.mh.getMotor(motor_num)
        self.motor_num = motor_num

        atexit.register(self.turn_off_motors)
        self.speed = 0
        self.throttle = 0

    def run(self, speed):
        """
        Update the speed of the motor where 1 is full forward and
        -1 is full backwards.
        """
        if speed > 1 or speed < -1:
            raise ValueError("Speed must be between 1(forward) and -1(reverse)")

        self.speed = speed
        self.throttle = int(dk.util.data.map_range(abs(speed), -1, 1, -255, 255))

        if speed > 0:
            self.motor.run(self.FORWARD)
        else:
            self.motor.run(self.BACKWARD)

        self.motor.setSpeed(self.throttle)

    def shutdown(self):
        self.mh.getMotor(self.motor_num).run(Adafruit_MotorHAT.RELEASE)
