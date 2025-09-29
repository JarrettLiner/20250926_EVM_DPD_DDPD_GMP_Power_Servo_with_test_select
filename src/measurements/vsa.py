# ==============================================================
# File: vsa.py
# Description:
#   Vector Signal Analyzer (VSA) control module for:
#     - Instrument initialization & setup
#     - Reference level / frequency configuration
#     - Baseline EVM and ACLR measurements
#     - Digital Pre-Distortion (DPD) tests:
#         * Polynomial DPD (formerly Single DPD)
#         * Direct DPD (formerly Iterative DPD)
#         * GMP DPD
#     - Power Servo controls:
#         * External NRX (via PowerServo)
#         * K18 internal VSA-based servo
#     - Envelope Tracking (ET) integration
# ==============================================================

import logging
from time import time, sleep
from src.instruments.bench import bench
from src.measurements.power_servo import PowerServo
import json
import os

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
# Load Test Input JSON Config (test_inputs.json)
# Provides global defaults for servo behavior
# --------------------------------------------------------------
config_path = os.path.join(os.getcwd(), "test_inputs.json")
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        test_config = json.load(f)
    sweep_cfg = test_config.get("Sweep_Measurement", {}).get("range", {})
else:
    test_config = {}
    sweep_cfg = {}

# Default flags (overridable via function args)
USE_POWER_SERVO = sweep_cfg.get("use_power_servo", True)
USE_K18_POWER_SERVO = sweep_cfg.get("use_K18_power_servo", True)


class VSA:
    # ----------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------
    def __init__(self, host="192.168.200.20", port=5025):
        """
        Initialize the VSA instrument.
        - Resets the analyzer
        - Loads the configured 5G NR setup (full frame or first slot)
        - Prepares measurement environment for EVM/ACLR/DPD
        """
        # Start instrument session (socket open)
        self.vsa = bench().VSA_start()
        self.bench = bench()
        start_time = time()
        try:
            vsa_setup_start = time()

            # Load configuration for signal bandwidth and frame type
            signal_bandwidth = test_config.get("Sweep_Measurement", {}).get("signal_bandwidth", "10MHz")
            frame_type = test_config.get("Sweep_Measurement", {}).get("frame_type", "full_frame")

            # Determine SCS, RB, RBO based on signal_bandwidth
            if signal_bandwidth == "10MHz":
                scs = "30kHz"
                rb = "24RB"
                rbo = "0RBO"
            elif signal_bandwidth == "100MHz":
                scs = "60kHz"
                rb = "135RB"
                rbo = "0RBO"
            else:
                raise ValueError(f"Unsupported signal_bandwidth: {signal_bandwidth}")

            # Determine frame suffix
            if frame_type == "full_frame":
                frame_suffix = "fullframe"
            elif frame_type == "first_slot":
                frame_suffix = "1slot"
            else:
                raise ValueError(f"Unsupported frame_type: {frame_type}")

            # Construct setup file path
            setup_file = fr'C:\R_S\instr\user\Qorvo\5GNR_UL_{signal_bandwidth}_256QAM_{scs}_{rb}_{rbo}_{frame_suffix}'
            print(f"VSA setup file:\n {setup_file}")

            # Start instrument connection
            self.instr = self.bench.VSA_start()
            self.instr.query('*RST; *OPC?')  # Reset analyzer
            self.instr.query('*OPC?')

            # Load selected memory setup file
            self.instr.query(fr'MMEM:LOAD:STAT 1,"{setup_file}"; *OPC?')
            self.instr.query('CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?')  # Disable RFU correction
            self.instr.query(
                f':SENS:SWE:TIME {0.0101}; *OPC?')  # Set sweep time to minimum (10.1ms) to speed up measurements
            self.instr.query('INIT:CONT OFF; *OPC?')  # Single trigger mode
            self.instr.query('INIT:IMM; *OPC?')  # Trigger single measurement

            # Amplifier/K18 setup
            self.write_command_opc('INST:SEL "Amplifier"')  # Select Amplifier application
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            self.instr.query(':CONF:DDPD:STAT OFF; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')  # Single trigger mode
            self.instr.query('INIT:IMM; *OPC?')  # Trigger single measurement
            self.instr.query('CONF:DPD:METH GEN; *OPC?')
            self.instr.query('CONF:DPD:SHAP:MODE POLY; *OPC?')
            self.instr.query(':CONF:DPD:TRAD 100; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')  # Trigger single measurement

            # Total setup timing
            self.setup_time = time() - start_time
            print(f"Total VSA setup time: {self.setup_time:.3f}")
            vsa_setup_time = time() - vsa_setup_start
            print("vsa initialization time, , , , {:.3f}".format(vsa_setup_time))
            print(
                "This includes reset\nretieveing the setup parameters\nfrom the test_input file\nand loading of the setup file\nupdate the poly DPD calculation\nnot included in the total test time")
            logger.info(
                f"VSA initialized in {self.setup_time:.3f}s using signal_bandwidth '{signal_bandwidth}' and frame_type '{frame_type}'")

        except Exception as e:
            logger.error(f"VSA initialization failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Utility methods
    # ----------------------------------------------------------
    def autolevel(self):
        """Automatically adjust analyzer input level."""
        self.instr.query(':SENS:ADJ:LEV; *OPC?')

    def autoEVM(self):
        """Automatically optimize EVM measurement settings."""
        self.instr.query(':SENS:ADJ:EVM; *OPC?')

    def set_ref_level(self, ref_level):
        """Set the reference level (dBm)."""
        try:
            self.instr.query(f'DISP:WIND:TRAC:Y:SCAL:RLEV {ref_level:.2f}; *OPC?')
            logger.info(f"VSA reference level set to {ref_level:.2f} dBm")
        except Exception as e:
            logger.error(f"Setting VSA reference level failed: {str(e)}")
            raise

    def get_evm(self):
        """Fetch EVM value from the VSA."""
        try:
            get_evm_start = time()
            evm_value = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?'))
            get_evm_time = time() - get_evm_start
            #  print(f"Get EVM time, , {get_evm_time:.3f}")
            #  print("This includes fetching the EVM value from the 5G app")
            return evm_value, get_evm_time
        except Exception as e:
            logger.error(f"Fetching EVM value failed: {str(e)}")
            raise

    def configure(self, freq, vsa_offset):
        """Configure analyzer frequency and offset."""
        try:
            vsa_configure_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(f':SENS:FREQ:CENT {freq}; *OPC?')
            self.instr.write(f':DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS {vsa_offset:.2f}')
            self.instr.query(':CONF:NR5G:MEAS EVM; *OPC?')
            vsa_configure_time = time() - vsa_configure_start
            print(f"VSA configure time, , {vsa_configure_time:.3f}")
            print("This includes the time to set frequency and offsets")
            logger.info(f"VSA configured for {freq} Hz with offset {vsa_offset:.2f} dB")
        except Exception as e:
            logger.error(f"VSA configuration failed: {str(e)}")
            raise

    def _resolve_servo_flags(self, use_power_servo, use_k18_power_servo):
        """Resolve servo flags to defaults if None."""
        if use_power_servo is None:
            use_power_servo = USE_POWER_SERVO
        if use_k18_power_servo is None:
            use_k18_power_servo = USE_K18_POWER_SERVO
        return use_power_servo, use_k18_power_servo

    def _run_servos(self, power_servo, freq_ghz, target_output, expected_gain, servo_iterations, use_power_servo,
                    use_k18_power_servo):
        """Execute power servos (external NRX and/or K18)."""
        servo_loops = 0
        ext_servo_time = 0
        k18_time = 0

        if use_power_servo:
            ext_servo_start = time()
            servo_loops, _ = power_servo.external_servo(freq_ghz, target_output, expected_gain, servo_iterations)
            ext_servo_time = time() - ext_servo_start
            print(f"External servo time, , {ext_servo_time:.3f}")

        if use_k18_power_servo:
            k18_start = time()
            k18_loops, _ = power_servo.k18_servo(target_output, servo_iterations)
            k18_time = time() - k18_start
            print(f"K18 servo time, , {k18_time:.3f}")
            if use_power_servo:
                servo_loops += k18_loops  # Accumulate if both servos used
            else:
                servo_loops = k18_loops

        return servo_loops, ext_servo_time, k18_time

    def _perform_et_sweep(self, et):
        """Perform envelope tracking delay sweep if ET is enabled."""
        if not et:
            return None

        et_start = time()
        self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')  # Ensure back to EVM mode
        et.configure()  # Configure ET (timing printed inside)

        et_starting_delay = test_config.get("Sweep_Measurement", {}).get("et_starting_delay", 0.0)
        et_delay_step = test_config.get("Sweep_Measurement", {}).get("et_delay_step", 0.0)

        et_delays, et_evms, et_step_times, et_total_loop_time = et.et_delay_evm(et_starting_delay, et_delay_step)
        et_total_time = time() - et_start

        return {
            "delays": et_delays,
            "evms": et_evms,
            "total_time": et_total_time
        }

    # ----------------------------------------------------------
    # Baseline EVM Measurement
    # ----------------------------------------------------------
    def measure_evm(self, freq_str, vsa_offset, target_output, servo_iterations, freq_ghz,
                    expected_gain, power_servo, use_power_servo=None, use_k18_power_servo=None, et=None):
        """Measure baseline EVM and ACLR (no DPD)."""
        try:
            print(f"\n------ Baseline EVM Test ------")
            total_evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')

            # Run servos
            print(f"\n------ power servo ------")
            power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(use_power_servo, use_k18_power_servo)
            servo_loops, ext_servo_time, k18_time = self._run_servos(
                power_servo, freq_ghz, target_output, expected_gain, servo_iterations,
                use_power_servo, use_k18_power_servo
            )
            power_servo_time = time() - power_servo_start
            #  print(f"\npower servo loop time, , {power_servo_time:.3f}s")
            print(f"use nrx {use_power_servo}\nuse K18 {use_k18_power_servo}\nservo iterations {servo_loops}")
            #  print("baseline evm power servo time, , {:.3f}".format(power_servo_time))

            # EVM measurement
            print(f"\n------ measure baseline EVM aclr & power ------")
            evm_start = time()
            self.instr.query('INIT:IMM; *OPC?')
            vsa_power = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?'))
            evm_value = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?'))
            evm_time = time() - evm_start
            print("evm = {:.3f} dB".format(evm_value))
            print("5G app power = {:.3f} dBm".format(vsa_power))
            print(f"Baseline EVM and VSA Power time, , {evm_time:.3f}")
            print("This includes VSA power and EVM measurement")

            # ACLR measurement
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            chan_pow, adj_chan_lower, adj_chan_upper = [float(x) for x in aclr_list.split(',')[:3]]
            aclr_time = time() - aclr_start
            print("5G app channel power = {:.3f} dBm".format(chan_pow))
            print(f"Baseline ACLR time, , {aclr_time:.3f}")
            print("This includes VSA ACLR measurement")

            # Envelope Tracking if enabled
            print(f"\n------ Baseline EVM ET  ------")
            baseline_et_data = self._perform_et_sweep(et)
            if baseline_et_data:
                print(f"\nbaseline evm ET sweep total time , , {baseline_et_data['total_time']:.3f}")
                print("This includes ET configuration and delay sweep\n")

            total_evm_time = time() - total_evm_start
            print(f"Total baseline evm time, , {total_evm_time:.3f}")
            print("This includes power servo ET sweep EVM and ACLR measurements")
            logger.info(f"Baseline done: Power={vsa_power}, EVM={evm_value}, Total={total_evm_time:.3f}")

            return (vsa_power, evm_value, evm_time, chan_pow, adj_chan_lower, adj_chan_upper,
                    aclr_time, total_evm_time, servo_loops, ext_servo_time, k18_time, baseline_et_data)

        except Exception as e:
            logger.error(f"Baseline EVM failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Polynomial DPD (formerly Single DPD)
    # ----------------------------------------------------------
    def perform_polynomial_dpd(self, freq_str, vsa_offset, target_output, servo_iterations,
                               freq_ghz, expected_gain, power_servo, use_power_servo=None,
                               use_k18_power_servo=None, et=None):
        """Run Polynomial DPD + measurement."""
        try:
            print(f"\n------ polynomial dpd Test ------")
            poly_total_start = time()

            # Amplifier app setup
            print(f"\n------ K18 setup ------")
            amp_setup_start = time()
            self.write_command_opc('INST:SEL "Amplifier"')
            #  self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            #  self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            #  self.instr.write('CONF:SETT')
            #  self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            amp_app_setup_time = time() - amp_setup_start
            print(f"amp app setup time, , {amp_app_setup_time:.3f}")
            print("This includes amplifier app setup before polynomial DPD calculation")

            # Polynomial DPD setup and calculation
            print(f"\n------ polynomial dpd setup and calculation ------")
            poly_setup_start = time()
            self.instr.query('CONF:DPD:SHAP:MODE POLY; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query('CONF:DPD:UPD; *OPC?')
            self.instr.query(':CONF:DPD:AMAM:STAT ON; *OPC?')
            self.instr.query(':CONF:DPD:AMPM:STAT ON; *OPC?')
            poly_setup_time = time() - poly_setup_start
            print(f"Polynomial DPD setup time, , {poly_setup_time:.3f}")
            print("This includes amplifier app setup poly DPD calculation and update")

            # Power servo
            print(f"\n------ polynomial dpd power servo ------")
            poly_power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(use_power_servo, use_k18_power_servo)
            poly_servo_loops, poly_ext_servo_time, poly_k18_time = self._run_servos(
                power_servo, freq_ghz, target_output, expected_gain, servo_iterations,
                use_power_servo, use_k18_power_servo
            )
            poly_power_servo_time = time() - poly_power_servo_start
            print(f"use nrx {use_power_servo}\nuse K18 {use_k18_power_servo}\nservo iterations {poly_servo_loops}\n")
            print(f"Polynomial DPD Servo loop time, , {poly_power_servo_time:.3f}")

            # EVM measurement
            print(f"\n------ measure polynomial dpd evm aclr & power ------")
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            poly_power = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?'))
            poly_evm = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?'))
            poly_time = time() - evm_start
            print("poly dpd evm = {:.3f} dB".format(poly_evm))
            print("5G app power after poly dpd = {:.3f} dBm".format(poly_power))

            print(f"Polynomial DPD EVM and VSA Power time, , {poly_time:.3f}")
            print("This includes VSA power and EVM measurement after polynomial DPD applied")

            # ACLR measurement
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            poly_chan_pow, poly_adj_chan_lower, poly_adj_chan_upper = [float(x) for x in aclr_list.split(',')[:3]]
            poly_aclr_time = time() - aclr_start
            print("5G app channel power after poly dpd = {:.3f} dBm".format(poly_chan_pow))
            print(f"Polynomial DPD ACLR time, , {poly_aclr_time:.3f}")
            print("This includes VSA ACLR measurement after polynomial DPD applied and power servo")

            # Envelope Tracking if enabled
            print(f"\n------ polynomial dpd ET  ------")
            poly_et_data = self._perform_et_sweep(et)
            if poly_et_data:
                print(f"Polynomial DPD ET total time (incl. config), , {poly_et_data['total_time']:.3f}s")

            poly_total_time = time() - poly_total_start
            print(f"Polynomial dpd evm time, , , , {poly_total_time:.3f}")
            print("This includes amplifier app setup poly DPD calculation power servo EVM and ACLR measurements")
            logger.info(f"Polynomial DPD done: Power={poly_power}, EVM={poly_evm}, Total={poly_total_time:.3f}s")

            return (poly_power, poly_evm, poly_time, poly_chan_pow, poly_adj_chan_lower,
                    poly_adj_chan_upper, poly_aclr_time, poly_total_time, poly_servo_loops,
                    poly_ext_servo_time, poly_k18_time, poly_et_data)

        except Exception as e:
            logger.error(f"Polynomial DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Direct DPD (formerly Iterative DPD)
    # ----------------------------------------------------------
    def perform_direct_dpd(self, freq_str, vsa_offset, target_output, ddpd_iterations,
                           servo_iterations, freq_ghz, expected_gain, power_servo,
                           use_power_servo=None, use_k18_power_servo=None, et=None):
        """Run Direct DPD + measurement."""
        try:
            ddpd_total_start = time()

            # Amplifier app setup
            amp_setup_start = time()
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            amp_app_setup_time = time() - amp_setup_start
            print(f"amp app setup time, , {amp_app_setup_time:.3f}s")

            # Direct DPD setup
            ddpd_setup_start = time()
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {ddpd_iterations}; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            ddpd_setup_time = time() - ddpd_setup_start
            print(f"direct DPD setup time, , {ddpd_setup_time:.3f}s")
            print(f"ddpd iterations: {ddpd_iterations}")

            # Power servo
            ddpd_power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(use_power_servo, use_k18_power_servo)
            servo_loops, ext_servo_time, k18_time = self._run_servos(
                power_servo, freq_ghz, target_output, expected_gain, servo_iterations,
                use_power_servo, use_k18_power_servo
            )
            ddpd_power_servo_time = time() - ddpd_power_servo_start
            print(f"direct DPD Servo loop time, , {ddpd_power_servo_time:.3f}s")
            print(f"use nrx {use_power_servo}, use K18 {use_k18_power_servo}, servo iterations {servo_loops}")

            # EVM measurement
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            ddpd_power = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?'))
            ddpd_evm = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?'))
            ddpd_evm_time = time() - evm_start
            print(f"direct DPD EVM and VSA Power time, , {ddpd_evm_time:.3f}s")
            print("This includes VSA power and EVM measurement after direct DPD applied")

            # ACLR measurement
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            ddpd_chan_pow, ddpd_adj_chan_lower, ddpd_adj_chan_upper = [float(x) for x in aclr_list.split(',')[:3]]
            ddpd_aclr_time = time() - aclr_start
            print(f"direct DPD ACLR time, , {ddpd_aclr_time:.3f}s")
            print("This includes VSA ACLR measurement after direct DPD applied and power servo")

            # Envelope Tracking if enabled (before disabling DPD)
            direct_et_data = self._perform_et_sweep(et)
            if direct_et_data:
                print(f"Direct DPD ET total time (incl. config), , {direct_et_data['total_time']:.3f}s")

            ddpd_total_time = time() - ddpd_total_start
            print(f"direct dpd evm time, , {ddpd_total_time:.3f}s")
            print("This includes amplifier app setup iterative DPD setup power servo EVM and ACLR measurements")
            logger.info(f"Direct DPD done: Power={ddpd_power}, EVM={ddpd_evm}, Total={ddpd_total_time:.3f}s")

            # Return to 5G NR and disable DPD
            return_to_5g_nr_start = time()
            self.instr.query(':INST:SEL "Amplifier"; *OPC?')
            self.instr.query(':CONF:DDPD:APPL:STAT OFF; *OPC?')
            self.instr.query(':CONF:DDPD:STAT OFF; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            return_to_5g_nr_time = time() - return_to_5g_nr_start
            print(f"Return to 5G NR app time, , {return_to_5g_nr_time:.3f}s")
            print("This includes restoring VSA to 5G NR app and disabling DPDs")

            return (ddpd_power, ddpd_evm, ddpd_evm_time, ddpd_chan_pow, ddpd_adj_chan_lower,
                    ddpd_adj_chan_upper, ddpd_aclr_time, ddpd_total_time, servo_loops,
                    ext_servo_time, k18_time, direct_et_data)

        except Exception as e:
            logger.error(f"Direct DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # GMP DPD
    # ----------------------------------------------------------
    def perform_gmp_dpd(self, freq_str, vsa_offset, target_output, ddpd_iterations,
                        servo_iterations, freq_ghz, expected_gain, power_servo,
                        use_power_servo=None, use_k18_power_servo=None, et=None):
        """Run GMP (Generalized Memory Polynomial) DPD + measurement."""
        try:
            total_start = time()

            # Amplifier app setup
            amp_setup_start = time()
            self.instr.query('INST:SEL "Amplifier"; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            amp_app_setup_time = time() - amp_setup_start
            print(f"amp app setup time, , {amp_app_setup_time:.3f}s")

            # DDPD setup (base for GMP)
            gmp_setup_start = time()
            gmp_ddpd_setup_start = time()
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {ddpd_iterations}; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            gmp_ddpd_setup_time = time() - gmp_ddpd_setup_start
            print(f"GMP DDPD setup time, , {gmp_ddpd_setup_time:.3f}s")
            print("this includes ddpd config and iterative dpd run")
            print(f"ddpd iterations: {ddpd_iterations}")

            # GMP-specific configuration
            gmp_calc_setup_start = time()
            self.instr.query('CONF:MDPD:STAT ON; *OPC?')
            self.instr.query('CALC:MDPD:MOD;*OPC?')
            self.instr.query('CONF:GMP:LAG:ORD:XTER 1;*OPC?')
            self.instr.query('CONF:GMP:LEAD:ORD:XTER 1;*OPC?')
            self.instr.query('CONF:MDPD:ITER 5;*OPC?')
            self.instr.query(':CALC:MDPD:MOD;*OPC?')
            self.instr.query(':CONF:MDPD:WAV:UPD;*OPC?')
            self.instr.query('CONF:MDPD:WAV:SEL MDPD;*OPC?')
            gmp_calc_setup_time = time() - gmp_calc_setup_start
            print(f"GMP Calc setup time, , {gmp_calc_setup_time:.3f}s")
            print(" this includes gmp config calc and sync to vsg")
            gmp_setup_time = time() - gmp_setup_start
            print(f"GMP total setup time, , {gmp_setup_time:.3f}s")
            print("This includes amplifier app setup ddpd setup and gmp calc and sync to vsg")

            # Power servo
            gmp_power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(use_power_servo, use_k18_power_servo)
            gmp_servo_loops, gmp_ext_servo_time, gmp_k18_time = self._run_servos(
                power_servo, freq_ghz, target_output, expected_gain, servo_iterations,
                use_power_servo, use_k18_power_servo
            )
            gmp_power_servo_time = time() - gmp_power_servo_start
            print(f"GMP DPD Servo loop time, , {gmp_power_servo_time:.3f}s")
            print(f"use nrx {use_power_servo}, use K18 {use_k18_power_servo}, servo iterations {gmp_servo_loops}")

            # EVM measurement
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            gmp_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            gmp_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            gmp_evm_time = time() - evm_start
            print(f"GMP DPD EVM and VSA Power time, , {gmp_evm_time:.3f}s")
            print(f"This includes VSA power and EVM measurement after GMP DPD applied")

            # ACLR measurement
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            gmp_chan_pow, gmp_adj_chan_lower, gmp_adj_chan_upper = [float(x) for x in aclr_list.split(',')[:3]]
            gmp_aclr_time = time() - aclr_start
            print(f"GMP DPD ACLR time, , {gmp_aclr_time:.3f}s")
            print("This includes VSA ACLR measurement after GMP DPD applied and power servo")

            # Envelope Tracking if enabled (before disabling DPD)
            gmp_et_data = self._perform_et_sweep(et)
            if gmp_et_data:
                print(f"GMP ET total time (incl. config), , {gmp_et_data['total_time']:.3f}s")

            gmp_total_time = time() - total_start
            print("GMP DPD total time, , {:.3f}s".format(gmp_total_time))
            print("This includes amplifier app setup ddpd setup gmp calc and sync power servo evm and aclr")
            logger.info(f"GMP DPD done: Power={gmp_power}, EVM={gmp_evm}, Total={gmp_total_time:.3f}s")

            # Return to 5G NR and disable DPD
            return_to_5g_nr_start = time()
            self.instr.query(':INST:SEL "Amplifier"; *OPC?')
            self.instr.query(':CONF:MDPD:WAV:SEL REF; *OPC?')
            self.instr.query(':CONF:DDPD:APPL:STAT OFF; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            return_to_5g_nr_time = time() - return_to_5g_nr_start
            print(f"Return to 5G NR app time, , {return_to_5g_nr_time:.3f}s")
            print("This includes restoring VSA to 5G NR app and disabling DPDs")

            return (gmp_power, gmp_evm, gmp_evm_time, gmp_chan_pow, gmp_adj_chan_lower,
                    gmp_adj_chan_upper, gmp_aclr_time, gmp_total_time, gmp_servo_loops,
                    gmp_ext_servo_time, gmp_k18_time, gmp_et_data)

        except Exception as e:
            logger.error(f"GMP DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------
    def close(self):
        """Close socket connection to VSA."""
        try:
            self.instr.close()
            logger.info("VSA socket closed")
        except Exception as e:
            logger.error(f"Error closing VSA socket: {str(e)}")
            raise

    def write_command_opc(self, command):
        """Write command with OPC synchronization."""
        self.instr.query(f'{command}; *OPC?')

    def queryFloat(self, query):
        """Query and return float value."""
        return float(self.instr.query(query))