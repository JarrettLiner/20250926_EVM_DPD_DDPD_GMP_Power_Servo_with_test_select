# ==============================================================
# File: et.py
# Description:
#   Envelope Tracking (ET) module for configuring ET on VSG and performing delay sweeps with EVM measurements.
# ==============================================================

import logging
from time import time, sleep

logger = logging.getLogger(__name__)

class ET:
    def __init__(self, vsg, et_delay_shifts=10, vsa=None, pm=None):
        """
        Initialize Envelope Tracking (ET).

        Args:
            vsg: VSG instance (contains vsg.vsg instrument handle)
            et_delay_shifts: Number of delay shift steps to perform
            vsa: VSA instance for EVM measurements
            pm: PowerMeter instance (optional, for future use)
        """
        logger.info("Initializing Envelope Tracking (ET)")
        self.vsg = vsg
        self.pm = pm
        self.vsa = vsa
        self.et_delay_shifts = et_delay_shifts
        self.logger = logging.getLogger(__name__)

    def configure(self):
        """
        Configure Envelope Tracking parameters on the VSG.
        Enables ET, sets output type to DIFF, initial delay to 0, and shaping mode to DETR.
        Returns the configuration time.
        """
        try:
            et_config_start_time = time()
            # Access the instrument handle through vsg.vsg
            self.vsg.vsg.query("SOURce1:IQ:OUTPut:ANALog:ENVelope:STATe 1; *OPC?")
            self.vsg.vsg.query("SOURce1:IQ:OUTPut:ANALog:TYPE DIFF; *OPC?")
            self.vsg.vsg.query("SOURce1:IQ:OUTPut:ANALog:ENVelope:DELay 0; *OPC?")
            self.vsg.vsg.query("SOURce1:IQ:OUTPut:ANALog:ENVelope:SHAPing:MODE DETR; *OPC?")
            et_config_time = time() - et_config_start_time
            print(f"ET configure time, , {et_config_time:.3f}")
            print("This includes the time to enable ET and set delay and shaping mode")
            logger.info(f"ET configured in {et_config_time:.3f}s")
            return et_config_time
        except Exception as e:
            logger.error(f"ET configuration failed: {str(e)}")
            raise

    def et_delay_evm(self, start_delay, step):
        """
        Perform ET delay sweep: set delays in a loop, measure EVM for each.

        Args:
            start_delay: Initial delay value in seconds
            step: Delay increment step in seconds

        Returns:
            tuple: (delays, evms, step_times, et_total_loop_time)
                - delays: list of delay values tested
                - evms: list of EVM measurements for each delay
                - step_times: list of time taken for each step
                - et_total_loop_time: total time for entire sweep

        Disables ET after the sweep.
        """
        try:
            logger.info("Starting ET delay EVM sweep")
            et_delay_start_time = time()
            delays = []
            evms = []
            step_times = []
            evm_times = []  # Store time for each get_evm call
            current_delay = start_delay

            # Perform sweep: iterate through delay values and measure EVM
            for i in range(self.et_delay_shifts + 1):  # Include starting delay
                step_start_time = time()

                # Set envelope tracking delay
                self.vsg.vsg.write(f"SOURce1:IQ:OUTPut:ANALog:ENVelope:DELay {current_delay}")

                # Trigger measurement on VSA
                self.vsa.instr.write('INIT:IMM')

                # Get EVM measurement and time
                evm, evm_time = self.vsa.get_evm()

                # Store results
                delays.append(current_delay)
                evms.append(evm)
                evm_times.append(evm_time)
                step_time = time() - step_start_time
                step_times.append(step_time)

                # Increment delay for next iteration
                current_delay += step

            et_total_loop_time = time() - et_delay_start_time
            num_loops = len(step_times)
            avg_loop_time = et_total_loop_time / num_loops if num_loops > 0 else 0
            total_evm_time = sum(evm_times)
            avg_evm_time = total_evm_time / num_loops if num_loops > 0 else 0
            avg_evm = sum(evms) / num_loops if num_loops > 0 else 0

            print("ET total loop time, , {:.3f}".format(et_total_loop_time))

            print(
                f"\nET Delay Sweep: Total time={et_total_loop_time:.3f}s\nNumber of loops={num_loops}\n"
                f"Average loop time={avg_loop_time:.3f}s\nAverage get_evm time={avg_evm_time:.3f}s\n"
                f"Average EVM={avg_evm:.2f}dB\n"
            )
            print ("\nthis includes time to set delay trigger VSA and get EVM measurement\n")

            # Disable ET after sweep
            disable_start = time()
            self.vsg.vsg.query("SOURce1:IQ:OUTPut:ANALog:ENVelope:STATe 0; *OPC?")
            disable_time = time() - disable_start
            print(f"ET disable time, , {disable_time:.3f}")
            logger.info(f"ET sweep completed: {len(delays)} points in {et_total_loop_time:.3f}s")

            return delays, evms, step_times, et_total_loop_time

        except Exception as e:
            logger.error(f"ET delay EVM sweep failed: {str(e)}")
            raise