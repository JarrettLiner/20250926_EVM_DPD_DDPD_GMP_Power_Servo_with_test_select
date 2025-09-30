# ==============================================================
# File: vsg.py
# Description:
#   Vector Signal Generator (VSG) control module for:
#     - Initialization and default waveform load
#     - Frequency + power configuration
#     - Output power adjustments
#     - Cleanup and socket close
# ==============================================================

import logging
from src.instruments.bench import bench
from time import time
import json
import os

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
# Load Test Input JSON Config (test_inputs.json)
# Provides global defaults for setup mode
# --------------------------------------------------------------
config_path = os.path.join(os.getcwd(), "test_inputs.json")
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        test_config = json.load(f)
else:
    test_config = {}

class VSG:
    # ----------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------
    def __init__(self):
        """
        Initialize the VSG instrument:
          - Connect via bench helper
          - Reset instrument
          - Load default 5G NR waveform configuration based on test_inputs.json
          - Record initialization/setup time
        """
        start_time = time()
        logger.info("Initializing VSG")

        # Load configuration for signal bandwidth and frame type
        signal_bandwidth = test_config.get("Sweep_Measurement", {}).get("signal_bandwidth", "10MHz")
        frame_type = test_config.get("Sweep_Measurement", {}).get("frame_type", "full_frame")

        # Determine SCS, rb, rbo based on signal_bandwidth (lowercase for VSG paths)
        if signal_bandwidth == "10MHz":
            scs = "30kHz"
            rb = "24rb"
            rbo = "0rbo"
        elif signal_bandwidth == "100MHz":
            scs = "60kHz"
            rb = "135rb"
            rbo = "0rbo"
        else:
            raise ValueError(f"Unsupported signal_bandwidth: {signal_bandwidth}")

        # Determine frame suffix
        if frame_type == "full_frame":
            frame_suffix = "fullframe"
        elif frame_type == "first_slot":
            frame_suffix = "1slot"
        else:
            raise ValueError(f"Unsupported frame_type: {frame_type}")

        # Construct waveform file path
        self.waveform_file = f'/var/user/Qorvo/NR5G_{signal_bandwidth}_UL_{scs}SCS_256QAM_{rb}_{rbo}_{frame_suffix}.wv'

        # Start instrument session (socket open)
        self.vsg = bench().VSG_start()

        # Reset instrument to known state
        self.vsg.query('*RST; *OPC?')
        self.vsg.query('*OPC?')  # Wait until reset complete
        self.vsg.query('SOURce1:CORRection:OPTimize:RF:CHARacteristics EVM; *OPC?')
        self.vsg.query('OUTPut1:AMODe AUTO; *OPC?')  # Set ATTN mode to AUTO
        self.vsg.query(f'SOURce1:POWer:LIM:AMPL {20}; *OPC?')  # Set power limit to +10dBm
        self.vsg.query(f'SOURce1:POWer:ATTenuation:DIGital {-3.522}; *OPC?')  # Set digital attenuation

        # Load predefined 5G NR waveform file
        self.vsg.query(f'SOURce1:BB:ARBitrary:WAVeform:SELect "{self.waveform_file}"; *OPC?')
        self.vsg.query('SOURce1:BB:ARBitrary:STATe 1; *OPC?')  # Ensure ARB state is enabled
        self.vsg.query(f':SOUR1:FREQ:CW {2e9}; *OPC?')  # Set CW frequency
        self.vsg.query('OUTPut1:STATe ON; *OPC?')  # Ensure output state is ON

        # Track and log setup time
        self.setup_time = time() - start_time
        print(f"VSG setup time, , , , , , {self.setup_time:.3f}\nThis includes the time to load the waveform file\nnot included in the total test time")
        #  print("This includes the time to load the waveform file\nnot included in the total test time")
        logger.info(f"VSG initialized in {self.setup_time:.3f}s using signal_bandwidth '{signal_bandwidth}' and frame_type '{frame_type}'")

    # ----------------------------------------------------------
    # Configuration
    # ----------------------------------------------------------
    def configure(self, freq, initial_power, vsg_offset):
        """
        Configure VSG for test:
          - Apply power offset
          - Set frequency
          - Set power level
          - Enable RF output

        Args:
            freq (float): Center frequency in Hz.
            initial_power (float): Initial power level in dBm.
            vsg_offset (float): Output power offset in dB.
        """
        vsg_configure_start_time = time()
        #  self.vsg.query(':OUTP1:STAT 0; *OPC?')
        #  self.vsg.query('SOURce1:BB:ARBitrary:STATe 0; *OPC?')  # Disable ARB state
        self.vsg.query(f'SOURce1:BB:ARBitrary:WAVeform:SELect "{self.waveform_file}"; *OPC?')
        # Apply output power offset
        self.vsg.write(f':SOUR1:POW:LEV:IMM:OFFS {vsg_offset:.3f}')
        self.vsg.query(':OUTput1:AMODe AUTO; *OPC?')  # Set ATTN mode to AUTO

        # Set RF frequency
        self.vsg.query(f':SOUR1:FREQ:CW {freq}; *OPC?')  # Set CW frequency

        # Set output power
        self.vsg.query(f':SOUR1:POW:LEV:IMM:AMPL {initial_power}; *OPC?')
        self.vsg.query(f'SOURce1:POWer:LIM:AMPL {20}; *OPC?')  # Set power limit to +10dBm

        # Enable baseband ARB
        #  self.vsg.query('SOURce1:BB:ARBitrary:STATe 1; *OPC?')  # Ensure ARB state is enabled

        # Enable RF output
        #  self.vsg.query(':OUTP1:STAT 1; *OPC?')
        self.vsg.query('*OPC?')  # Wait until all operations complete
        vsg_configure_time = time() - vsg_configure_start_time
        print(f"VSG configure time, , {vsg_configure_time:.3f}\nThis includes the time to set frequency power and offsets")
        #  print("This includes the time to set frequency power and offsets")
    # ----------------------------------------------------------
    # Power adjustment
    # ----------------------------------------------------------
    def set_power(self, pwr):
        """
        Adjust VSG output power level.

        Args:
            pwr (float): Desired power level in dBm.
        """
        self.vsg.query(f':SOUR1:POW:LEV:IMM:AMPL {pwr}; *OPC?')

    def set_waveform(self, waveform_file):
        """
        Load a different waveform file into the VSG.

        Args:
            waveform_file (str): Path to the waveform file.
        """
        self.vsg.query(f'SOURce1:BB:ARBitrary:WAVeform:SELect "{waveform_file}"; *OPC?')

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------
    def close(self):
        """
        Close the VSG instrument session and socket.
        """
        self.vsg.sock.close()
        logger.info("VSG socket closed")