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
            self.instr.query('*RST; *OPC?')   # Reset analyzer
            self.instr.query('*OPC?')

            # Load selected memory setup file
            self.instr.query(fr'MMEM:LOAD:STAT 1,"{setup_file}"; *OPC?')
            self.instr.query('CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?') # Disable RFU correction
            self.instr.query(f':SENS:SWE:TIME {0.0101}; *OPC?')  # Set sweep time to minimum (10.1ms) to speed up measurements
            self.instr.query('INIT:CONT OFF; *OPC?') # Single trigger mode
            self.instr.query('INIT:IMM; *OPC?') # Trigger single measurement

            # Ensure 5G NR measurement setup
            '''
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:RFO:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:SETT:UPD:RF; *OPC?')
            self.instr.query('CONF:SETT:RF; *OPC?')
            self.instr.query('CONF:SETT:NR5G; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')            
            #  self.instr.query(':CONF:NR5G:DL:CC1:RFUC:FZER:MODE CF; *OPC?')
            self.instr.query(':INIT:IMM; *OPC?')
            '''
            # Amplifier/K18 setup
            self.write_command_opc('INST:SEL "Amplifier"') # Select Amplifier application
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
            #  self.instr.query('CONF:DPD:UPD; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')  # Trigger single measurement

            # Total setup timing
            self.setup_time = time() - start_time
            print(f"Total VSA setup time: {self.setup_time:.3f}")
            vsa_setup_time = time() - vsa_setup_start
            print("vsa initialization time, , , , {:.3f}".format(vsa_setup_time))
            print("This includes reset\nretieveing the setup parameters\nfrom the test_input file\nand loading of the setup file\nupdate the poly DPD calculation\nnot included in the total test time")
            logger.info(f"VSA initialized in {self.setup_time:.3f}s using signal_bandwidth '{signal_bandwidth}' and frame_type '{frame_type}'")

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
        try:
            get_evm_start = time()
            evm_value = float(self.instr.query('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?'))
            get_evm_time = time() - get_evm_start
            print(f"Get EVM time, , {get_evm_time:.3f}")
            print("This includes fetching the EVM value from the 5G app")
            return evm_value
        except Exception as e:
            logger.error(f"Fetching EVM value failed: {str(e)}")
            raise

    def configure(self, freq, vsa_offset):
        """Configure analyzer frequency and offset."""
        try:
            vsa_configure_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            #  self.instr.query('CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?')
            #  self.instr.query('CONF:NR5G:DL:CC1:RFUC:FZER:MODE CF; *OPC?')
            self.instr.query(f':SENS:FREQ:CENT {freq}; *OPC?')
            self.instr.write(f':DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS {vsa_offset:.2f}')
            self.instr.query(':CONF:NR5G:MEAS EVM; *OPC?')
            #  self.instr.query('INIT:CONT OFF; *OPC?')
            #  self.instr.query('INIT:IMM; *OPC?')
            #  self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            #  self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            vsa_configure_time = time() - vsa_configure_start
            print(f"VSA configure time, , {vsa_configure_time:.3f}")
            print("This includes the time to set frequency and offsets")
            logger.info(f"VSA configured for {freq} Hz with offset {vsa_offset}")
        except Exception as e:
            logger.error(f"VSA configuration failed: {str(e)}")
            raise

    def write_command_opc(self, command: str) -> None:
        """
        Write a SCPI command to the VSA with OPC synchronization.
        """
        try:
            self.instr.write('*ESE 1')
            self.instr.write('*SRE 32')
            self.instr.write(f'{command};*OPC')
            while (int(self.instr.query('*ESR?')) & 1) != 1:
                sleep(0.2)
            logger.info(f"Command '{command}' completed with OPC sync.")
        except Exception as e:
            logger.error(f"Error during OPC write: {str(e)}")
            raise

    def queryFloat(self, command):
        try:
            return float(self.instr.query(command))
        except:
            return None

    def _resolve_servo_flags(self, use_power_servo, use_k18_power_servo):
        """Resolve servo flags, falling back to globals if None."""
        if use_power_servo is None:
            use_power_servo = USE_POWER_SERVO
        if use_k18_power_servo is None:
            use_k18_power_servo = USE_K18_POWER_SERVO
        return use_power_servo, use_k18_power_servo

    def _run_servos(self, power_servo, freq_ghz, target_output, expected_gain,
                    servo_iterations, use_power_servo, use_k18_power_servo):
        """Run selected power servos and track metrics."""
        servo_loops = ext_servo_time = k18_time = 0
        if use_power_servo:
            ext_servo_start = time()
            servo_loops, servo_settle_time = power_servo.servo_power(
                freq_ghz, target_output, expected_gain
            )
            ext_servo_time = time() - ext_servo_start
            #  print(f"nrx servo converged after {servo_loops} iterations")
            #  print(f"nrx power servo time , ,{ext_servo_time:.3f}")
        if use_k18_power_servo:
            k18_servo_start = time()
            self.instr.query('INST:SEL "Amplifier"; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:TARG {target_output:.2f}; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:ITER {servo_iterations}; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:TOL {0.1}; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:STAR; *OPC?')
            k18_time = time() - k18_servo_start
            print(f"K18 servo time, , {k18_time:.3f}")
            self.instr.query('INST:SEL "5G NR"; *OPC?')
        return servo_loops, ext_servo_time, k18_time

    # ----------------------------------------------------------
    # Baseline EVM/ACLR Measurement
    # ----------------------------------------------------------
    def measure_evm(self, freq_str, vsa_offset, target_output, servo_iterations,
                    freq_ghz, expected_gain, power_servo,
                    USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):
        """Measure baseline EVM and ACLR (no DPD)."""
        try:
            total_start = time()
            servo_start = time()
            print("Starting baseline EVM power servo")
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            print("Baseline power servo complete")
            servo_time = time() - servo_start
            print(f"use nrx", {use_power_servo}, "\nuse K18", {use_k18_power_servo}, "\nservo iterations", {servo_loops})
            print(f"nrx servo loops,  {servo_loops}")
            print(f"baseline power servo loop time, , {servo_time:.3f}")

            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            vsa_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            evm_value = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"Baseline measurement\nPower={vsa_power}\nEVM={evm_value}")
            evm_time = time() - evm_start
            print(f"baseline EVM and VSA Power time, , {evm_time:.3f}")
            print(f"This includes VSA power from the 5G app\nEVM measurement\nno DPD applied\npower servo is separate")
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            chan_pow, adj_chan_lower, adj_chan_upper = [float(x) for x in aclr_list.split(',')[:3]]
            aclr_time = time() - aclr_start
            print(f"baseline ACLR time, , {aclr_time:.3f}")
            print("This includes VSA ACLR measurement \nno DPD applied")
            total_evm_time = time() - total_start
            print(f"*** bbaseline evm total test time***, , , {total_evm_time:.3f}")
            print("This includes power servo EVM and ACLR measurements")
            logger.info(f"Baseline done: Power={vsa_power}, EVM={evm_value}, Total={total_evm_time:.3f}s")
            return (vsa_power, evm_value, evm_time,
                    chan_pow, adj_chan_lower, adj_chan_upper,
                    aclr_time, total_evm_time, servo_loops,
                    ext_servo_time, k18_time)

        except Exception as e:
            logger.error(f"Baseline EVM measurement failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Polynomial DPD (formerly Single DPD)
    # ----------------------------------------------------------
    def perform_polynomial_dpd(self, freq_str, vsa_offset, target_output, servo_iterations,
                               freq_ghz, expected_gain, power_servo,
                               USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):
        """Run Polynomial DPD + measurement."""
        try:
            print("Hey Jerk boy! the poly DPD starts right here!")
            poly_dpd_start = time()
            amp_setup_start = time()

            self.write_command_opc('INST:SEL "Amplifier"')
            '''
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')            
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            self.instr.query('CONF:DDPD:STAT OFF; *OPC?')
            '''
            amp_app_setup_time = time() - amp_setup_start
            print(f"amp app setup time, , {amp_app_setup_time:.3f}")
            poly_dpd_setup_start = time()
            k18_single_sweep_start = time()
            self.instr.query('INIT:IMM; *OPC?')
            k18_single_sweep_time = time() - k18_single_sweep_start
            print(f"K18 single sweep time, , {k18_single_sweep_time:.3f}")
            poly_config_start = time()
            #  self.instr.query('CONF:DPD:METH GEN; *OPC?')
            #  self.instr.query('CONF:DPD:SHAP:MODE POLY; *OPC?')
            #  self.instr.query(':CONF:DPD:TRAD 100; *OPC?')
            poly_config_time = time() - poly_config_start
            print(f"poly config time, , {poly_config_time:.3f}")
            poly_calc_start = time()
            self.instr.query(':CONF:DPD:UPD; *OPC?')
            poly_calc_time = time() - poly_calc_start
            print(f"poly calc time, , {poly_calc_time:.3f}")
            enable_poly_dpd_start = time()
            self.instr.query('CONF:DPD:AMAM:STAT ON; *OPC?')
            self.instr.query('CONF:DPD:AMPM:STAT ON; *OPC?')
            enable_poly_dpd_time = time() - enable_poly_dpd_start
            print(f"enable poly dpd time, , {enable_poly_dpd_time:.3f}")
            '''
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            self.instr.query('CONF:DDPD:APPL:STAT ON; *OPC?')
            self.instr.query(':CONF:DDPD:WAV:UPD; *OPC?')
            '''
            poly_dpd_setup_time = time() - poly_dpd_setup_start
            print(f"poly dpd setup time, , , {poly_dpd_setup_time:.3f}")
            print("This includes poly dpd config calc and sync to vsg")
            poly_power_servo_start = time()
            print("Starting polynomial DPD power servo")
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            poly_power_servo_time = time() - poly_power_servo_start
            print(f"poly DPD Servo loop time, , {poly_power_servo_time:.3f}")
            print(f"use nrx", {use_power_servo}, "use K18", {use_k18_power_servo}, "servo iterations", {servo_loops})
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            poly_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            poly_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"poly DPD measurement\n Power={poly_power}\n EVM={poly_evm}")
            poly_evm_time = time() - evm_start
            print(f"poly DPD EVM and VSA Power time, , {poly_evm_time:.3f}")
            print(f"This includes VSA power and EVM measurement after poly DPD applied")
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            poly_chan_pow, poly_adj_chan_lower, poly_adj_chan_upper = [float(x) for x in aclr_list.split(',')[:3]]
            poly_aclr_time = time() - aclr_start
            print(f"poly DPD ACLR time, , {poly_aclr_time:.3f}")
            print("This includes VSA ACLR measurement after poly DPD applied and power servo")
            poly_total_time = time() - poly_dpd_start
            print(f"***polynomial DPD total test time***, , , {poly_total_time:.3f}")
            print("This includes amplifier app setup\npoly DPD setup power servo\nEVM and ACLR measurements")
            print(" OK dumbass the poly DPD test is over.")
            logger.info(f"Polynomial DPD done: Power={poly_power}, EVM={poly_evm}, Total={poly_total_time:.3f}s")
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            '''
            return_to_5g_nr_start = time()
            self.instr.query(':INST:SEL "Amplifier"; *OPC?')
            self.instr.query(':CONF:DDPD:APPL:STAT OFF; *OPC?')
            self.instr.query(':CONF:DDPD:STAT OFF; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            #  self.instr.query(f':CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            return_to_5g_nr_time = time() - return_to_5g_nr_start
            print(f"Return to 5G NR app time, , {return_to_5g_nr_time:.3f}s")
            print("This includes restoring VSA to 5G NR app and disabling DPDs")
            '''
            return (poly_power, poly_evm, poly_evm_time,
                    poly_chan_pow, poly_adj_chan_lower, poly_adj_chan_upper,
                    poly_aclr_time, poly_total_time,
                    servo_loops, ext_servo_time, k18_time)

        except Exception as e:
            logger.error(f"Polynomial DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Direct DPD (formerly Iterative DPD)
    # ----------------------------------------------------------
    def perform_direct_dpd(self, freq_str, vsa_offset, target_output, ddpd_iterations, servo_iterations,
                           freq_ghz, expected_gain, power_servo,
                           USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):
        """Run Direct DPD + measurement."""
        try:
            ddpd_total_start = time()
            amp_setup_start = time()
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            amp_app_setup_time = time() - amp_setup_start
            print(f"amp app setup time, , {amp_app_setup_time:.3f}s")
            ddpd_setup_start = time()
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {ddpd_iterations}; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            self.instr.query('CONF:DDPD:APPL:STAT ON; *OPC?')
            self.instr.query(':CONF:DDPD:WAV:UPD; *OPC?')
            ddpd_setup_time = time() - ddpd_setup_start
            print(f"direct dpd setup time, , {ddpd_setup_time:.3f}s")
            print(f"this includes direct dpd config and iterative dpd run")
            print(f"ddpd iterations: {ddpd_iterations}")
            ddpd_power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            ddpd_power_servo_time = time() - ddpd_power_servo_start
            print(f"direct DPD Servo loop time, , {ddpd_power_servo_time:.3f}s")
            print(f"use nrx", {use_power_servo}, "use K18", {use_k18_power_servo}, "servo iterations", {servo_loops})
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            ddpd_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            ddpd_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"direct DPD measurement\n Power={ddpd_power}\n EVM={ddpd_evm}")
            ddpd_evm_time = time() - evm_start
            print(f"direct DPD EVM and VSA Power time, , {ddpd_evm_time:.3f}s")
            print(f"This includes VSA power and EVM measurement after direct DPD applied")
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            ddpd_chan_pow, ddpd_adj_chan_lower, ddpd_adj_chan_upper = [float(x) for x in aclr_list.split(',')[:3]]
            ddpd_aclr_time = time() - aclr_start
            print(f"direct DPD ACLR time, , {ddpd_aclr_time:.3f}s")
            print("This includes VSA ACLR measurement after direct DPD applied and power servo")
            ddpd_total_time = time() - ddpd_total_start
            print(f"direct dpd evm time, , {ddpd_total_time:.3f}s")
            print("This includes amplifier app setup iterative DPD setup power servo EVM and ACLR measurements")
            logger.info(f"Direct DPD done: Power={ddpd_power}, EVM={ddpd_evm}, Total={ddpd_total_time:.3f}s")
            #  self.instr.query(':CONF:DDPD:STAT OFF; *OPC?')
            #  self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            #  self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            return_to_5g_nr_start = time()
            self.instr.query(':INST:SEL "Amplifier"; *OPC?')
            self.instr.query(':CONF:DDPD:APPL:STAT OFF; *OPC?')
            self.instr.query(':CONF:DDPD:STAT OFF; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            #  self.instr.query(f':CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            return_to_5g_nr_time = time() - return_to_5g_nr_start
            print(f"Return to 5G NR app time, , {return_to_5g_nr_time:.3f}s")
            print("This includes restoring VSA to 5G NR app and disabling DPDs")
            return (ddpd_power, ddpd_evm, ddpd_evm_time,
                    ddpd_chan_pow, ddpd_adj_chan_lower, ddpd_adj_chan_upper,
                    ddpd_aclr_time, ddpd_total_time,
                    servo_loops, ext_servo_time, k18_time)

        except Exception as e:
            logger.error(f"Direct DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # GMP DPD
    # ----------------------------------------------------------
    def perform_gmp_dpd(self, freq_str, vsa_offset, target_output, ddpd_iterations, servo_iterations,
                        freq_ghz, expected_gain, power_servo,
                        USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):
        """Run GMP (Generalized Memory Polynomial) DPD + measurement."""
        try:
            total_start = time()
            amp_setup_start = time()
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            amp_app_setup_time = time() - amp_setup_start
            print(f"amp app setup time, , {amp_app_setup_time:.3f}s")
            gmp_setup_start = time()
            # Select amplifier + run DDPD as base
            gmp_ddpd_setup_start = time()
            self.write_command_opc('INST:SEL "Amplifier"')
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
            #  self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            #  self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')

            # Run servos
            gmp_power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            gmp_power_servo_time = time() - gmp_power_servo_start
            print(f"GMP DPD Servo loop time, , {gmp_power_servo_time:.3f}s")
            print(f"use nrx", {use_power_servo}, "use K18", {use_k18_power_servo}, "servo iterations", {servo_loops})

            # EVM measurement
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            gmp_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            gmp_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"GMP DPD measurement\n Power={gmp_power}\n EVM={gmp_evm}")
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
            total_time = time() - total_start
            print("GMP DPD total time, , {:.3f}s".format(total_time))
            print("This includes amplifier app setup ddpd setup gmp calc and sync power servo evm and aclr")
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            #  print(f"Total GMP dpd evm time: {total_time:.3f}s")
            #  print("this includes gmp setup, ddpd, gmp calc and sync, power servo, evm and aclr")
            logger.info(f"GMP DPD done: Power={gmp_power}, EVM={gmp_evm}, Total={total_time:.3f}s")

            # Restore EVM mode
            return_to_5g_nr_start = time()
            self.instr.query(':INST:SEL "Amplifier"; *OPC?')
            self.instr.query(':CONF:MDPD:WAV:SEL REF; *OPC?')
            self.instr.query(':CONF:DDPD:APPL:STAT OFF; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':CONF:NR5G:MEAS EVM; *OPC?')
            #  self.instr.query(f':CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            return_to_5g_nr_time = time() - return_to_5g_nr_start
            print(f"Return to 5G NR app time, , {return_to_5g_nr_time:.3f}s")
            print("This includes restoring VSA to 5G NR app and disabling DPDs")
            return (gmp_power, gmp_evm, gmp_evm_time,
                    gmp_chan_pow, gmp_adj_chan_lower, gmp_adj_chan_upper,
                    gmp_aclr_time, total_time,
                    servo_loops, ext_servo_time, k18_time)

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
# ==============================================================