# ==============================================================
# File: power_servo.py
# Description:
#   Power servo module for:
#     - External NRX-based servo (via PowerMeter)
#     - Internal K18 VSA-based servo
#     - Supports tolerance + iteration limits
# ==============================================================

import logging
from time import time, sleep

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)


class PowerServo:
    # ----------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------
    def __init__(self, vsg, pm, vsa, max_iterations=10, tolerance=0.1):
        """
        Initialize PowerServo.

        Args:
            vsg: VSG instance for setting input power.
            pm: PowerMeter instance for measuring DUT power.
            vsa: VSA instance (used to update reference level or run K18 servo).
            max_iterations (int): Max allowed servo iterations.
            tolerance (float): Power tolerance in dB for convergence.
        """
        self.vsg = vsg
        self.pm = pm
        self.vsa = vsa
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.logger = logging.getLogger(__name__)

    # ----------------------------------------------------------
    # External NRX Power Servo (wraps old servo_power)
    # ----------------------------------------------------------
    def external_servo(self, freq_ghz, target_output, expected_gain, servo_iterations):
        """
        Run servo loop using NRX PowerMeter feedback.

        Args:
            freq_ghz (float): Frequency in GHz (for logging).
            target_output (float): Desired output power (dBm).
            expected_gain (float): Expected DUT gain (dB).
            servo_iterations (int): Max number of iterations.

        Returns:
            tuple: (servo_iterations, servo_settle_time)
        """
        self.max_iterations = servo_iterations
        return self.servo_power(freq_ghz, target_output, expected_gain)

    def servo_power(self, freq_ghz, target_output, expected_gain):
        """
        Iterative loop to drive DUT output power to target using NRX.

        Returns:
            tuple: (servo_iterations, servo_settle_time)
        """
        # Estimate gain from measurement
        measured_in, measured_out = self.pm.measure()
        measured_gain = measured_out - measured_in
        self.logger.info(f"Measured DUT gain: {measured_gain:.3f} dB")
        print(f"Measured gain in dB: {measured_gain:.3f}")

        # Initial input power estimate
        input_power = target_output - measured_gain
        self.vsg.set_power(input_power)

        servo_start = time()
        servo_loops = 0
        servo_settle_time = None

        for i in range(self.max_iterations):
            _, current_output = self.pm.measure()
            servo_loops = i + 1

            if abs(current_output - target_output) < self.tolerance:
                servo_settle_time = round(time() - servo_start, 3)
                self.logger.info(
                    f"NRX servo converged after {servo_loops} iterations "
                    f"(time={servo_settle_time:.3f}s, freq={freq_ghz} GHz)"
                )
                break

            adjustment = target_output - current_output
            input_power += adjustment
            self.vsg.set_power(input_power)
        else:
            servo_settle_time = round(time() - servo_start, 3)
            self.logger.warning(
                f"NRX servo did not converge within {self.max_iterations} iterations "
                f"at {freq_ghz} GHz (time={servo_settle_time:.3f}s)"
            )

        return servo_loops, servo_settle_time

    # ----------------------------------------------------------
    # Internal K18 Power Servo
    # ----------------------------------------------------------
    def k18_servo(self, target_output, servo_iterations, tolerance=0.1):
        """
        Run internal K18 power servo on the VSA.

        Args:
            target_output (float): Desired output power (dBm).
            servo_iterations (int): Max number of iterations.
            tolerance (float): Allowed tolerance in dB.

        Returns:
            tuple: (servo_iterations, k18_servo_time)
        """
        k18_start = time()

        try:
            self.vsa.instr.query('INST:SEL "Amplifier"; *OPC?')
            self.vsa.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.vsa.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.vsa.instr.query('CONF:GEN:POW:LEV:STAT ON; *OPC?')
            self.vsa.instr.query(f'CONF:GEN:POW:LEV:TARG {target_output:.2f}; *OPC?')
            self.vsa.instr.query(f'CONF:GEN:POW:LEV:ITER {servo_iterations}; *OPC?')
            self.vsa.instr.query(f'CONF:GEN:POW:LEV:TOL {tolerance:.2f}; *OPC?')
            self.vsa.instr.query('CONF:GEN:POW:LEV:STAR; *OPC?')

            k18_time = time() - k18_start
            print(f"K18 servo time, , {k18_time:.3f}")
            self.logger.info(f"K18 servo completed in {k18_time:.3f}s (target={target_output} dBm)")

            # Switch back to 5G NR app
            self.vsa.instr.query('INST:SEL "5G NR"; *OPC?')

        except Exception as e:
            self.logger.error(f"K18 servo failed: {str(e)}")
            raise

        return servo_iterations, round(k18_time, 3)
