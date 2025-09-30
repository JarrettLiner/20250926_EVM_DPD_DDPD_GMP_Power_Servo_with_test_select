import os
import csv
from datetime import datetime
import re


def parse_console_output(console_output):
    # Initialize result dictionary with common fields
    result = {
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Project_Name': '',
        'Script_Path': '',
        'Executable_Path': '',
        'Status': '',
        'Test_Frequency_GHz': '',
        'VSG_Setup_Time_s': '',
        'VSA_Setup_Time_s': '',
        'VSA_Initialization_Time_s': '',
        'VSG_Configure_Time_s': '',
        'VSA_Configure_Time_s': '',
        'Baseline_Power_Servo_Gain_dB': '',
        'Baseline_Power_Servo_Time_s': '',
        'Baseline_Power_Servo_Iterations': '',
        'Baseline_EVM_dB': '',
        'Baseline_5G_App_Power_dBm': '',
        'Baseline_Channel_Power_dBm': '',
        'Baseline_EVM_Power_Time_s': '',
        'Baseline_ACLR_Time_s': '',
        'Baseline_ET_Configure_Time_s': '',
        'Baseline_ET_Loop_Time_s': '',
        'Baseline_ET_Delay_Sweep_Time_s': '',
        'Baseline_ET_Delay_Sweep_Loops': '',
        'Baseline_ET_Avg_Loop_Time_s': '',
        'Baseline_ET_Avg_EVM_dB': '',
        'Baseline_ET_Disable_Time_s': '',
        'Baseline_ET_Sweep_Total_Time_s': '',
        'Baseline_EVM_Total_Time_s': '',
        'Poly_DPD_Amp_Setup_Time_s': '',
        'Poly_DPD_Setup_Time_s': '',
        'Poly_DPD_Servo_Gain_dB': '',
        'Poly_DPD_Servo_Time_s': '',
        'Poly_DPD_Servo_Iterations': '',
        'Poly_DPD_EVM_dB': '',
        'Poly_DPD_5G_App_Power_dBm': '',
        'Poly_DPD_Channel_Power_dBm': '',
        'Poly_DPD_EVM_Power_Time_s': '',
        'Poly_DPD_ACLR_Time_s': '',
        'Poly_DPD_ET_Configure_Time_s': '',
        'Poly_DPD_ET_Loop_Time_s': '',
        'Poly_DPD_ET_Delay_Sweep_Time_s': '',
        'Poly_DPD_ET_Delay_Sweep_Loops': '',
        'Poly_DPD_ET_Avg_Loop_Time_s': '',
        'Poly_DPD_ET_Avg_EVM_dB': '',
        'Poly_DPD_ET_Disable_Time_s': '',
        'Poly_DPD_ET_Total_Time_s': '',
        'Poly_DPD_EVM_Total_Time_s': '',
        'Total_Measurement_Time_s': '',
        'Waveform_Configuration': ''
    }

    # Extract script and executable path, status
    path_pattern = r'^(.*?\.exe)\s+(.*?)\s*\n'
    status_pattern = r'Process finished with exit code (\d+)$'

    path_match = re.search(path_pattern, console_output, re.MULTILINE)
    if path_match:
        result['Executable_Path'] = path_match.group(1)
        result['Script_Path'] = path_match.group(2)
        # Derive project name from script path
        script_dir = os.path.dirname(result['Script_Path'])
        result['Project_Name'] = os.path.basename(script_dir) or 'Unknown'

    status_match = re.search(status_pattern, console_output, re.MULTILINE)
    if status_match:
        result['Status'] = 'Success' if status_match.group(1) == '0' else 'Failed'

    # Extract test frequency
    freq_match = re.search(r'--- Testing Frequency: ([\d.]+) GHz ---', console_output)
    if freq_match:
        result['Test_Frequency_GHz'] = freq_match.group(1)

    # Extract setup times
    result['VSG_Setup_Time_s'] = re.search(r'VSG setup time,.*?([\d.]+)', console_output).group(1) if re.search(
        r'VSG setup time,.*?([\d.]+)', console_output) else ''
    result['VSA_Setup_Time_s'] = re.search(r'Total VSA setup time: ([\d.]+)', console_output).group(1) if re.search(
        r'Total VSA setup time: ([\d.]+)', console_output) else ''
    result['VSA_Initialization_Time_s'] = re.search(r'vsa initialization time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'vsa initialization time,.*?([\d.]+)', console_output) else ''
    result['VSG_Configure_Time_s'] = re.search(r'VSG configure time,.*?([\d.]+)', console_output).group(1) if re.search(
        r'VSG configure time,.*?([\d.]+)', console_output) else ''
    result['VSA_Configure_Time_s'] = re.search(r'VSA configure time,.*?([\d.]+)', console_output).group(1) if re.search(
        r'VSA configure time,.*?([\d.]+)', console_output) else ''

    # Extract baseline power servo
    gain_match = re.search(r'Measured gain in dB: ([\d.]+)', console_output)
    if gain_match:
        result['Baseline_Power_Servo_Gain_dB'] = gain_match.group(1)
    result['Baseline_Power_Servo_Time_s'] = re.search(r'External servo time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'External servo time,.*?([\d.]+)', console_output) else ''
    result['Baseline_Power_Servo_Iterations'] = re.search(r'servo iterations (\d+)', console_output).group(
        1) if re.search(r'servo iterations (\d+)', console_output) else ''

    # Extract baseline EVM, power, and ACLR
    result['Baseline_EVM_dB'] = re.search(r'evm = (-?[\d.]+) dB', console_output).group(1) if re.search(
        r'evm = (-?[\d.]+) dB', console_output) else ''
    result['Baseline_5G_App_Power_dBm'] = re.search(r'5G app power = ([\d.]+) dBm', console_output).group(
        1) if re.search(r'5G app power = ([\d.]+) dBm', console_output) else ''
    result['Baseline_Channel_Power_dBm'] = re.search(r'5G app channel power = ([\d.]+) dBm', console_output).group(
        1) if re.search(r'5G app channel power = ([\d.]+) dBm', console_output) else ''
    result['Baseline_EVM_Power_Time_s'] = re.search(r'Baseline EVM and VSA Power time,.*?([\d.]+)',
                                                    console_output).group(1) if re.search(
        r'Baseline EVM and VSA Power time,.*?([\d.]+)', console_output) else ''
    result['Baseline_ACLR_Time_s'] = re.search(r'Baseline ACLR time,.*?([\d.]+)', console_output).group(1) if re.search(
        r'Baseline ACLR time,.*?([\d.]+)', console_output) else ''

    # Extract baseline ET
    result['Baseline_ET_Configure_Time_s'] = re.search(r'ET configure time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'ET configure time,.*?([\d.]+)', console_output) else ''
    result['Baseline_ET_Loop_Time_s'] = re.search(r'ET total loop time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'ET total loop time,.*?([\d.]+)', console_output) else ''
    result['Baseline_ET_Delay_Sweep_Time_s'] = re.search(r'ET Delay Sweep: Total time=([\d.]+)s', console_output).group(
        1) if re.search(r'ET Delay Sweep: Total time=([\d.]+)s', console_output) else ''
    result['Baseline_ET_Delay_Sweep_Loops'] = re.search(r'Number of loops=(\d+)', console_output).group(1) if re.search(
        r'Number of loops=(\d+)', console_output) else ''
    result['Baseline_ET_Avg_Loop_Time_s'] = re.search(r'Average loop time=([\d.]+)s', console_output).group(
        1) if re.search(r'Average loop time=([\d.]+)s', console_output) else ''
    result['Baseline_ET_Avg_EVM_dB'] = re.search(r'Average EVM=(-?[\d.]+)dB', console_output).group(1) if re.search(
        r'Average EVM=(-?[\d.]+)dB', console_output) else ''
    result['Baseline_ET_Disable_Time_s'] = re.search(r'ET disable time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'ET disable time,.*?([\d.]+)', console_output) else ''
    result['Baseline_ET_Sweep_Total_Time_s'] = re.search(r'baseline evm ET sweep total time ,.*?([\d.]+)',
                                                         console_output).group(1) if re.search(
        r'baseline evm ET sweep total time ,.*?([\d.]+)', console_output) else ''
    result['Baseline_EVM_Total_Time_s'] = re.search(r'Total baseline evm time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'Total baseline evm time,.*?([\d.]+)', console_output) else ''

    # Extract polynomial DPD
    result['Poly_DPD_Amp_Setup_Time_s'] = re.search(r'amp app setup time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'amp app setup time,.*?([\d.]+)', console_output) else ''
    result['Poly_DPD_Setup_Time_s'] = re.search(r'Polynomial DPD setup time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'Polynomial DPD setup time,.*?([\d.]+)', console_output) else ''
    poly_gain_match = re.search(r'Polynomial DPD power servo.*?Measured gain in dB: ([\d.]+)', console_output)
    if poly_gain_match:
        result['Poly_DPD_Servo_Gain_dB'] = poly_gain_match.group(1)
    result['Poly_DPD_Servo_Time_s'] = re.search(r'Polynomial DPD Servo loop time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'Polynomial DPD Servo loop time,.*?([\d.]+)', console_output) else ''
    result['Poly_DPD_Servo_Iterations'] = re.search(r'Polynomial DPD power servo.*?servo iterations (\d+)',
                                                    console_output).group(1) if re.search(
        r'Polynomial DPD power servo.*?servo iterations (\d+)', console_output) else ''
    result['Poly_DPD_EVM_dB'] = re.search(r'poly dpd evm = (-?[\d.]+) dB', console_output).group(1) if re.search(
        r'poly dpd evm = (-?[\d.]+) dB', console_output) else ''
    result['Poly_DPD_5G_App_Power_dBm'] = re.search(r'5G app power after poly dpd = ([\d.]+) dBm',
                                                    console_output).group(1) if re.search(
        r'5G app power after poly dpd = ([\d.]+) dBm', console_output) else ''
    result['Poly_DPD_Channel_Power_dBm'] = re.search(r'5G app channel power after poly dpd = ([\d.]+) dBm',
                                                     console_output).group(1) if re.search(
        r'5G app channel power after poly dpd = ([\d.]+) dBm', console_output) else ''
    result['Poly_DPD_EVM_Power_Time_s'] = re.search(r'Polynomial DPD EVM and VSA Power time,.*?([\d.]+)',
                                                    console_output).group(1) if re.search(
        r'Polynomial DPD EVM and VSA Power time,.*?([\d.]+)', console_output) else ''
    result['Poly_DPD_ACLR_Time_s'] = re.search(r'Polynomial DPD ACLR time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'Polynomial DPD ACLR time,.*?([\d.]+)', console_output) else ''
    result['Poly_DPD_ET_Configure_Time_s'] = re.search(r'Polynomial DPD ET.*?ET configure time,.*?([\d.]+)',
                                                       console_output).group(1) if re.search(
        r'Polynomial DPD ET.*?ET configure time,.*?([\d.]+)', console_output) else ''
    result['Poly_DPD_ET_Loop_Time_s'] = re.search(r'Polynomial DPD ET.*?ET total loop time,.*?([\d.]+)',
                                                  console_output).group(1) if re.search(
        r'Polynomial DPD ET.*?ET total loop time,.*?([\d.]+)', console_output) else ''
    result['Poly_DPD_ET_Delay_Sweep_Time_s'] = re.search(r'Polynomial DPD ET.*?ET Delay Sweep: Total time=([\d.]+)s',
                                                         console_output).group(1) if re.search(
        r'Polynomial DPD ET.*?ET Delay Sweep: Total time=([\d.]+)s', console_output) else ''
    result['Poly_DPD_ET_Delay_Sweep_Loops'] = re.search(r'Polynomial DPD ET.*?Number of loops=(\d+)',
                                                        console_output).group(1) if re.search(
        r'Polynomial DPD ET.*?Number of loops=(\d+)', console_output) else ''
    result['Poly_DPD_ET_Avg_Loop_Time_s'] = re.search(r'Polynomial DPD ET.*?Average loop time=([\d.]+)s',
                                                      console_output).group(1) if re.search(
        r'Polynomial DPD ET.*?Average loop time=([\d.]+)s', console_output) else ''
    result['Poly_DPD_ET_Avg_EVM_dB'] = re.search(r'Polynomial DPD ET.*?Average EVM=(-?[\d.]+)dB', console_output).group(
        1) if re.search(r'Polynomial DPD ET.*?Average EVM=(-?[\d.]+)dB', console_output) else ''
    result['Poly_DPD_ET_Disable_Time_s'] = re.search(r'Polynomial DPD ET.*?ET disable time,.*?([\d.]+)',
                                                     console_output).group(1) if re.search(
        r'Polynomial DPD ET.*?ET disable time,.*?([\d.]+)', console_output) else ''
    result['Poly_DPD_ET_Total_Time_s'] = re.search(r'Polynomial DPD ET total time \(incl. config\),.*?([\d.]+)s',
                                                   console_output).group(1) if re.search(
        r'Polynomial DPD ET total time \(incl. config\),.*?([\d.]+)s', console_output) else ''
    result['Poly_DPD_EVM_Total_Time_s'] = re.search(r'Polynomial dpd evm time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'Polynomial dpd evm time,.*?([\d.]+)', console_output) else ''

    # Extract total measurement time and waveform configuration
    result['Total_Measurement_Time_s'] = re.search(r'Total measurement time at [\d.]+ GHz:.*?([\d.]+)',
                                                   console_output).group(1) if re.search(
        r'Total measurement time at [\d.]+ GHz:.*?([\d.]+)', console_output) else ''
    waveform_match = re.search(r'The 5GNR waveform used in this test is (.*?)\.', console_output)
    if waveform_match:
        result['Waveform_Configuration'] = waveform_match.group(1)

    return result


def save_to_csv(parsed_data, output_file='console_output_summary.csv'):
    # Define CSV headers
    headers = [
        'Timestamp', 'Project_Name', 'Script_Path', 'Executable_Path', 'Status',
        'Test_Frequency_GHz', 'VSG_Setup_Time_s', 'VSA_Setup_Time_s', 'VSA_Initialization_Time_s',
        'VSG_Configure_Time_s', 'VSA_Configure_Time_s', 'Baseline_Power_Servo_Gain_dB',
        'Baseline_Power_Servo_Time_s', 'Baseline_Power_Servo_Iterations', 'Baseline_EVM_dB',
        'Baseline_5G_App_Power_dBm', 'Baseline_Channel_Power_dBm', 'Baseline_EVM_Power_Time_s',
        'Baseline_ACLR_Time_s', 'Baseline_ET_Configure_Time_s', 'Baseline_ET_Loop_Time_s',
        'Baseline_ET_Delay_Sweep_Time_s', 'Baseline_ET_Delay_Sweep_Loops', 'Baseline_ET_Avg_Loop_Time_s',
        'Baseline_ET_Avg_EVM_dB', 'Baseline_ET_Disable_Time_s', 'Baseline_ET_Sweep_Total_Time_s',
        'Baseline_EVM_Total_Time_s', 'Poly_DPD_Amp_Setup_Time_s', 'Poly_DPD_Setup_Time_s',
        'Poly_DPD_Servo_Gain_dB', 'Poly_DPD_Servo_Time_s', 'Poly_DPD_Servo_Iterations',
        'Poly_DPD_EVM_dB', 'Poly_DPD_5G_App_Power_dBm', 'Poly_DPD_Channel_Power_dBm',
        'Poly_DPD_EVM_Power_Time_s', 'Poly_DPD_ACLR_Time_s', 'Poly_DPD_ET_Configure_Time_s',
        'Poly_DPD_ET_Loop_Time_s', 'Poly_DPD_ET_Delay_Sweep_Time_s', 'Poly_DPD_ET_Delay_Sweep_Loops',
        'Poly_DPD_ET_Avg_Loop_Time_s', 'Poly_DPD_ET_Avg_EVM_dB', 'Poly_DPD_ET_Disable_Time_s',
        'Poly_DPD_ET_Total_Time_s', 'Poly_DPD_EVM_Total_Time_s', 'Total_Measurement_Time_s',
        'Waveform_Configuration'
    ]

    # Write to CSV
    file_exists = os.path.isfile(output_file)
    with open(output_file, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(parsed_data)


def main():
    # Example console output (replace with actual input or file read)
    console_output = r"""C:\Users\LINER\Documents\PycharmProjects\20250926_EVM_DPD_DDPD_GMP_Power_Servo_with_test_select\.venv\Scripts\python.exe C:\Users\LINER\Documents\PycharmProjects\20250926_EVM_DPD_DDPD_GMP_Power_Servo_with_test_select\main.py 
Test description, , individual test blocks, test block totals, not added to total time
VSG setup time, , , , 1.231
This includes the time to load the waveform file
not included in the total test time
VSA setup file:
 C:\R_S\instr\user\Qorvo\5GNR_UL_100MHz_256QAM_60kHz_135RB_0RBO_fullframe
Total VSA setup time: 16.021
vsa initialization time, , , , 16.021
This includes reset
retieveing the setup parameters
from the test_input file
and loading of the setup file
update the poly DPD calculation
not included in the total test time

--- Testing Frequency: 2.0 GHz ---
VSG configure time, , 0.090
This includes the time to set frequency power and offsets
VSA configure time, , 0.181
This includes the time to set frequency and offsets

------ Baseline EVM Test ------

------ power servo ------
Measured gain in dB: 18.432
External servo time, , 1.130
use nrx True
use K18 False
servo iterations 1

------ measure baseline EVM aclr & power ------
evm = -45.786 dB
5G app power = 6.080 dBm
Baseline EVM and VSA Power time, , 0.831
This includes VSA power and EVM measurement
5G app channel power = 6.188 dBm
Baseline ACLR time, , 0.698
This includes VSA ACLR measurement

------ Baseline EVM ET  ------
ET configure time, , 0.004
This includes the time to enable ET and set delay and shaping mode
ET total loop time, , 0.754

ET Delay Sweep: Total time=0.754s
Number of loops=15
Average loop time=0.050s
Average get_evm time=0.050s
Average EVM=-45.79dB


this includes time to set delay trigger VSA and get EVM measurement

ET disable time, , 0.001

baseline evm ET sweep total time , , 0.859
This includes ET configuration and delay sweep

Total baseline evm time, , 3.519
This includes power servo ET sweep EVM and ACLR measurements

------ polynomial dpd Test ------

------ K18 setup ------
amp app setup time, , 0.015
This includes amplifier app setup before polynomial DPD calculation

------ polynomial dpd setup and calculation ------
Polynomial DPD setup time, , 2.659
This includes amplifier app setup poly DPD calculation and update

------ polynomial dpd power servo ------
Measured gain in dB: 18.440
External servo time, , 1.735
use nrx True
use K18 False
servo iterations 2

Polynomial DPD Servo loop time, , 1.735

------ measure polynomial dpd evm aclr & power ------
poly dpd evm = -51.218 dB
5G app power after poly dpd = 6.100 dBm
Polynomial DPD EVM and VSA Power time, , 0.984
This includes VSA power and EVM measurement after polynomial DPD applied
5G app channel power after poly dpd = 6.224 dBm
Polynomial DPD ACLR time, , 0.677
This includes VSA ACLR measurement after polynomial DPD applied and power servo

------ polynomial dpd ET  ------
ET configure time, , 0.003
This includes the time to enable ET and set delay and shaping mode
ET total loop time, , 1.734

ET Delay Sweep: Total time=1.734s
Number of loops=15
Average loop time=0.116s
Average get_evm time=0.115s
Average EVM=-51.22dB


this includes time to set delay trigger VSA and get EVM measurement

ET disable time, , 0.001
Polynomial DPD ET total time (incl. config), , 1.834s
Polynomial dpd evm time, , , , 7.905
This includes amplifier app setup poly DPD calculation power servo EVM and ACLR measurements
Total measurement time at 2.0 GHz:, , , 11.425
The 5GNR waveform used in this test is a 100MHz UL 60kHz SCS 256QAM 135RB 0rbo configuration.
This test utilizes the full 5G frame.
The power servo is done after each DPD type to ensure accurate output power.
The power servo uses the NRX power meter and external sensors for power servo.

--- Testing Frequency: 2.05 GHz ---
VSG configure time, , 0.391
This includes the time to set frequency power and offsets
VSA configure time, , 0.459
This includes the time to set frequency and offsets

------ Baseline EVM Test ------

------ power servo ------
Measured gain in dB: 18.412
External servo time, , 1.029
use nrx True
use K18 False
servo iterations 1

------ measure baseline EVM aclr & power ------
evm = -50.935 dB
5G app power = 6.068 dBm
Baseline EVM and VSA Power time, , 0.839
This includes VSA power and EVM measurement
5G app channel power = 6.139 dBm
Baseline ACLR time, , 0.685
This includes VSA ACLR measurement

------ Baseline EVM ET  ------
ET configure time, , 0.004
This includes the time to enable ET and set delay and shaping mode
ET total loop time, , 3.626

ET Delay Sweep: Total time=3.626s
Number of loops=15
Average loop time=0.242s
Average get_evm time=0.241s
Average EVM=-50.93dB


this includes time to set delay trigger VSA and get EVM measurement

ET disable time, , 0.001

baseline evm ET sweep total time , , 3.736
This includes ET configuration and delay sweep

Total baseline evm time, , 6.291
This includes power servo ET sweep EVM and ACLR measurements

------ polynomial dpd Test ------

------ K18 setup ------
amp app setup time, , 0.045
This includes amplifier app setup before polynomial DPD calculation

------ polynomial dpd setup and calculation ------
Polynomial DPD setup time, , 2.306
This includes amplifier app setup poly DPD calculation and update

------ polynomial dpd power servo ------
Measured gain in dB: 18.420
External servo time, , 1.205
use nrx True
use K18 False
servo iterations 1

Polynomial DPD Servo loop time, , 1.205

------ measure polynomial dpd evm aclr & power ------
poly dpd evm = -50.939 dB
5G app power after poly dpd = 6.057 dBm
Polynomial DPD EVM and VSA Power time, , 0.955
This includes VSA power and EVM measurement after polynomial DPD applied
5G app channel power after poly dpd = 6.144 dBm
Polynomial DPD ACLR time, , 0.680
This includes VSA ACLR measurement after polynomial DPD applied and power servo

------ polynomial dpd ET  ------
ET configure time, , 0.003
This includes the time to enable ET and set delay and shaping mode
ET total loop time, , 0.767

ET Delay Sweep: Total time=0.767s
Number of loops=15
Average loop time=0.051s
Average get_evm time=0.051s
Average EVM=-50.94dB


this includes time to set delay trigger VSA and get EVM measurement

ET disable time, , 0.001
Polynomial DPD ET total time (incl. config), , 0.871s
Polynomial dpd evm time, , , , 6.061
This includes amplifier app setup poly DPD calculation power servo EVM and ACLR measurements
Total measurement time at 2.05 GHz:, , , 12.352
The 5GNR waveform used in this test is a 100MHz UL 60kHz SCS 256QAM 135RB 0rbo configuration.
This test utilizes the full 5G frame.
The power servo is done after each DPD type to ensure accurate output power.
The power servo uses the NRX power meter and external sensors for power servo.

--- Testing Frequency: 2.1 GHz ---
VSG configure time, , 0.340
This includes the time to set frequency power and offsets
VSA configure time, , 0.483
This includes the time to set frequency and offsets

------ Baseline EVM Test ------

------ power servo ------
Measured gain in dB: 18.408
External servo time, , 0.999
use nrx True
use K18 False
servo iterations 1

------ measure baseline EVM aclr & power ------
evm = -50.969 dB
5G app power = 6.047 dBm
Baseline EVM and VSA Power time, , 0.843
This includes VSA power and EVM measurement
5G app channel power = 6.122 dBm
Baseline ACLR time, , 0.675
This includes VSA ACLR measurement

------ Baseline EVM ET  ------
ET configure time, , 0.003
This includes the time to enable ET and set delay and shaping mode
ET total loop time, , 2.693

ET Delay Sweep: Total time=2.693s
Number of loops=15
Average loop time=0.180s
Average get_evm time=0.179s
Average EVM=-50.97dB


this includes time to set delay trigger VSA and get EVM measurement

ET disable time, , 0.001

baseline evm ET sweep total time , , 2.797
This includes ET configuration and delay sweep

Total baseline evm time, , 5.315
This includes power servo ET sweep EVM and ACLR measurements

------ polynomial dpd Test ------

------ K18 setup ------
amp app setup time, , 0.046
This includes amplifier app setup before polynomial DPD calculation

------ polynomial dpd setup and calculation ------
Polynomial DPD setup time, , 2.285
This includes amplifier app setup poly DPD calculation and update

------ polynomial dpd power servo ------
Measured gain in dB: 18.416
External servo time, , 1.756
use nrx True
use K18 False
servo iterations 2

Polynomial DPD Servo loop time, , 1.756

------ measure polynomial dpd evm aclr & power ------
poly dpd evm = -51.013 dB
5G app power after poly dpd = 6.093 dBm
Polynomial DPD EVM and VSA Power time, , 1.023
This includes VSA power and EVM measurement after polynomial DPD applied
5G app channel power after poly dpd = 6.183 dBm
Polynomial DPD ACLR time, , 0.674
This includes VSA ACLR measurement after polynomial DPD applied and power servo

------ polynomial dpd ET  ------
ET configure time, , 0.003
This includes the time to enable ET and set delay and shaping mode
ET total loop time, , 1.711

ET Delay Sweep: Total time=1.711s
Number of loops=15
Average loop time=0.114s
Average get_evm time=0.114s
Average EVM=-51.01dB


this includes time to set delay trigger VSA and get EVM measurement

ET disable time, , 0.002
Polynomial DPD ET total time (incl. config), , 1.819s
Polynomial dpd evm time, , , , 7.603
This includes amplifier app setup poly DPD calculation power servo EVM and ACLR measurements
Total measurement time at 2.1 GHz:, , , 12.919
The 5GNR waveform used in this test is a 100MHz UL 60kHz SCS 256QAM 135RB 0rbo configuration.
This test utilizes the full 5G frame.
The power servo is done after each DPD type to ensure accurate output power.
The power servo uses the NRX power meter and external sensors for power servo.

Process finished with exit code 0

    """

    # Parse the console output
    parsed_data = parse_console_output(console_output.strip())

    # Save to CSV
    save_to_csv(parsed_data)

    # Print user-friendly summary
    print("Console Output Summary:")
    for key, value in parsed_data.items():
        if value:  # Only print non-empty values
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()