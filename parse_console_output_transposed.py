import os
import pandas as pd
from datetime import datetime
import re
import sys
import argparse


def parse_console_output(console_output):
    # Initialize base result dictionary for shared fields
    base_result = {
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Project_Name': '',
        'Script_Path': '',
        'Executable_Path': '',
        'Status': '',
        'VSG_Setup_Time_s': '',
        'VSA_Setup_Time_s': '',
        'VSA_Initialization_Time_s': '',
        'Waveform_Configuration': ''
    }

    # Define frequency-specific fields
    freq_fields = [
        'Test_Frequency_GHz', 'VSG_Configure_Time_s', 'VSA_Configure_Time_s',
        'Baseline_Power_Servo_Gain_dB', 'Baseline_Power_Servo_Time_s', 'Baseline_Power_Servo_Iterations',
        'Baseline_EVM_dB', 'Baseline_5G_App_Power_dBm', 'Baseline_Channel_Power_dBm',
        'Baseline_EVM_Power_Time_s', 'Baseline_ACLR_Time_s', 'Baseline_ET_Configure_Time_s',
        'Baseline_ET_Loop_Time_s', 'Baseline_ET_Delay_Sweep_Time_s', 'Baseline_ET_Delay_Sweep_Loops',
        'Baseline_ET_Avg_Loop_Time_s', 'Baseline_ET_Avg_EVM_dB', 'Baseline_ET_Disable_Time_s',
        'Baseline_ET_Sweep_Total_Time_s', 'Baseline_EVM_Total_Time_s', 'Poly_DPD_Amp_Setup_Time_s',
        'Poly_DPD_Setup_Time_s', 'Poly_DPD_Servo_Gain_dB', 'Poly_DPD_Servo_Time_s',
        'Poly_DPD_Servo_Iterations', 'Poly_DPD_EVM_dB', 'Poly_DPD_5G_App_Power_dBm',
        'Poly_DPD_Channel_Power_dBm', 'Poly_DPD_EVM_Power_Time_s', 'Poly_DPD_ACLR_Time_s',
        'Poly_DPD_ET_Configure_Time_s', 'Poly_DPD_ET_Loop_Time_s', 'Poly_DPD_ET_Delay_Sweep_Time_s',
        'Poly_DPD_ET_Delay_Sweep_Loops', 'Poly_DPD_ET_Avg_Loop_Time_s', 'Poly_DPD_ET_Avg_EVM_dB',
        'Poly_DPD_ET_Disable_Time_s', 'Poly_DPD_ET_Total_Time_s', 'Poly_DPD_EVM_Total_Time_s',
        'Total_Measurement_Time_s'
    ]

    # Initialize result dictionary with all fields set to empty strings
    def initialize_result():
        result = base_result.copy()
        for field in freq_fields:
            result[field] = ''
        return result

    # Extract shared metadata
    path_pattern = r'^(.*?\.exe)\s+(.*?)\s*\n'
    status_pattern = r'Process finished with exit code (\d+)$'

    path_match = re.search(path_pattern, console_output, re.MULTILINE)
    if path_match:
        base_result['Executable_Path'] = path_match.group(1)
        base_result['Script_Path'] = path_match.group(2)
        script_dir = os.path.dirname(base_result['Script_Path'])
        base_result['Project_Name'] = os.path.basename(script_dir) or 'Unknown'

    status_match = re.search(status_pattern, console_output, re.MULTILINE)
    if status_match:
        base_result['Status'] = 'Success' if status_match.group(1) == '0' else 'Failed'

    base_result['VSG_Setup_Time_s'] = re.search(r'VSG setup time,.*?([\d.]+)', console_output).group(1) if re.search(
        r'VSG setup time,.*?([\d.]+)', console_output) else ''
    base_result['VSA_Setup_Time_s'] = re.search(r'Total VSA setup time: ([\d.]+)', console_output).group(
        1) if re.search(r'Total VSA setup time: ([\d.]+)', console_output) else ''
    base_result['VSA_Initialization_Time_s'] = re.search(r'vsa initialization time,.*?([\d.]+)', console_output).group(
        1) if re.search(r'vsa initialization time,.*?([\d.]+)', console_output) else ''
    waveform_match = re.search(r'The 5GNR waveform used in this test is (.*?)\.', console_output)
    if waveform_match:
        base_result['Waveform_Configuration'] = waveform_match.group(1)

    # Split console output by frequency blocks
    freq_blocks = re.split(r'--- Testing Frequency: ([\d.]+) GHz ---', console_output)[1:]
    results = []

    for i in range(0, len(freq_blocks), 2):
        freq = freq_blocks[i]
        block = freq_blocks[i + 1]
        result = initialize_result()
        result['Test_Frequency_GHz'] = freq

        # Split block into sections for baseline and polynomial DPD
        baseline_section = re.search(r'------ Baseline EVM Test ------.*?------ polynomial dpd Test ------', block,
                                     re.DOTALL)
        poly_dpd_section = re.search(r'------ polynomial dpd Test ------.*?(?=--- Testing Frequency:|$)', block,
                                     re.DOTALL)

        baseline_section = baseline_section.group(0) if baseline_section else ''
        poly_dpd_section = poly_dpd_section.group(0) if poly_dpd_section else ''

        # Extract frequency-specific data
        result['VSG_Configure_Time_s'] = re.search(r'VSG configure time,.*?([\d.]+)', block).group(1) if re.search(
            r'VSG configure time,.*?([\d.]+)', block) else ''
        result['VSA_Configure_Time_s'] = re.search(r'VSA configure time,.*?([\d.]+)', block).group(1) if re.search(
            r'VSA configure time,.*?([\d.]+)', block) else ''

        # Baseline section
        gain_match = re.search(r'Measured gain in dB: ([\d.]+)', baseline_section)
        if gain_match:
            result['Baseline_Power_Servo_Gain_dB'] = gain_match.group(1)
        result['Baseline_Power_Servo_Time_s'] = re.search(r'External servo time,.*?([\d.]+)', baseline_section).group(
            1) if re.search(r'External servo time,.*?([\d.]+)', baseline_section) else ''
        result['Baseline_Power_Servo_Iterations'] = re.search(r'servo iterations (\d+)', baseline_section).group(
            1) if re.search(r'servo iterations (\d+)', baseline_section) else ''

        result['Baseline_EVM_dB'] = re.search(r'evm = (-?[\d.]+) dB', baseline_section).group(1) if re.search(
            r'evm = (-?[\d.]+) dB', baseline_section) else ''
        result['Baseline_5G_App_Power_dBm'] = re.search(r'5G app power = ([\d.]+) dBm', baseline_section).group(
            1) if re.search(r'5G app power = ([\d.]+) dBm', baseline_section) else ''
        result['Baseline_Channel_Power_dBm'] = re.search(r'5G app channel power = ([\d.]+) dBm',
                                                         baseline_section).group(1) if re.search(
            r'5G app channel power = ([\d.]+) dBm', baseline_section) else ''
        result['Baseline_EVM_Power_Time_s'] = re.search(r'Baseline EVM and VSA Power time,.*?([\d.]+)',
                                                        baseline_section).group(1) if re.search(
            r'Baseline EVM and VSA Power time,.*?([\d.]+)', baseline_section) else ''
        result['Baseline_ACLR_Time_s'] = re.search(r'Baseline ACLR time,.*?([\d.]+)', baseline_section).group(
            1) if re.search(r'Baseline ACLR time,.*?([\d.]+)', baseline_section) else ''

        result['Baseline_ET_Configure_Time_s'] = re.search(r'ET configure time,.*?([\d.]+)', baseline_section).group(
            1) if re.search(r'ET configure time,.*?([\d.]+)', baseline_section) else ''
        result['Baseline_ET_Loop_Time_s'] = re.search(r'ET total loop time,.*?([\d.]+)', baseline_section).group(
            1) if re.search(r'ET total loop time,.*?([\d.]+)', baseline_section) else ''
        result['Baseline_ET_Delay_Sweep_Time_s'] = re.search(r'ET Delay Sweep: Total time=([\d.]+)s',
                                                             baseline_section).group(1) if re.search(
            r'ET Delay Sweep: Total time=([\d.]+)s', baseline_section) else ''
        result['Baseline_ET_Delay_Sweep_Loops'] = re.search(r'Number of loops=(\d+)', baseline_section).group(
            1) if re.search(r'Number of loops=(\d+)', baseline_section) else ''
        result['Baseline_ET_Avg_Loop_Time_s'] = re.search(r'Average loop time=([\d.]+)s', baseline_section).group(
            1) if re.search(r'Average loop time=([\d.]+)s', baseline_section) else ''
        result['Baseline_ET_Avg_EVM_dB'] = re.search(r'Average EVM=(-?[\d.]+)dB', baseline_section).group(
            1) if re.search(r'Average EVM=(-?[\d.]+)dB', baseline_section) else ''
        result['Baseline_ET_Disable_Time_s'] = re.search(r'ET disable time,.*?([\d.]+)', baseline_section).group(
            1) if re.search(r'ET disable time,.*?([\d.]+)', baseline_section) else ''
        result['Baseline_ET_Sweep_Total_Time_s'] = re.search(r'baseline evm ET sweep total time ,.*?([\d.]+)',
                                                             baseline_section).group(1) if re.search(
            r'baseline evm ET sweep total time ,.*?([\d.]+)', baseline_section) else ''
        result['Baseline_EVM_Total_Time_s'] = re.search(r'Total baseline evm time,.*?([\d.]+)', baseline_section).group(
            1) if re.search(r'Total baseline evm time,.*?([\d.]+)', baseline_section) else ''

        # Polynomial DPD section
        result['Poly_DPD_Amp_Setup_Time_s'] = re.search(r'amp app setup time,.*?([\d.]+)', poly_dpd_section).group(
            1) if re.search(r'amp app setup time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Poly_DPD_Setup_Time_s'] = re.search(r'Polynomial DPD setup time,.*?([\d.]+)', poly_dpd_section).group(
            1) if re.search(r'Polynomial DPD setup time,.*?([\d.]+)', poly_dpd_section) else ''
        poly_gain_match = re.search(r'Measured gain in dB: ([\d.]+)', poly_dpd_section)
        if poly_gain_match:
            result['Poly_DPD_Servo_Gain_dB'] = poly_gain_match.group(1)
        result['Poly_DPD_Servo_Time_s'] = re.search(r'Polynomial DPD Servo loop time,.*?([\d.]+)',
                                                    poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD Servo loop time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Poly_DPD_Servo_Iterations'] = re.search(r'servo iterations (\d+)', poly_dpd_section).group(
            1) if re.search(r'servo iterations (\d+)', poly_dpd_section) else ''
        result['Poly_DPD_EVM_dB'] = re.search(r'poly dpd evm = (-?[\d.]+) dB', poly_dpd_section).group(1) if re.search(
            r'poly dpd evm = (-?[\d.]+) dB', poly_dpd_section) else ''
        result['Poly_DPD_5G_App_Power_dBm'] = re.search(r'5G app power after poly dpd = ([\d.]+) dBm',
                                                        poly_dpd_section).group(1) if re.search(
            r'5G app power after poly dpd = ([\d.]+) dBm', poly_dpd_section) else ''
        result['Poly_DPD_Channel_Power_dBm'] = re.search(r'5G app channel power after poly dpd = ([\d.]+) dBm',
                                                         poly_dpd_section).group(1) if re.search(
            r'5G app channel power after poly dpd = ([\d.]+) dBm', poly_dpd_section) else ''
        result['Poly_DPD_EVM_Power_Time_s'] = re.search(r'Polynomial DPD EVM and VSA Power time,.*?([\d.]+)',
                                                        poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD EVM and VSA Power time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Poly_DPD_ACLR_Time_s'] = re.search(r'Polynomial DPD ACLR time,.*?([\d.]+)', poly_dpd_section).group(
            1) if re.search(r'Polynomial DPD ACLR time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Poly_DPD_ET_Configure_Time_s'] = re.search(r'Polynomial DPD ET.*?ET configure time,.*?([\d.]+)',
                                                           poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET.*?ET configure time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Poly_DPD_ET_Loop_Time_s'] = re.search(r'Polynomial DPD ET.*?ET total loop time,.*?([\d.]+)',
                                                      poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET.*?ET total loop time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Poly_DPD_ET_Delay_Sweep_Time_s'] = re.search(
            r'Polynomial DPD ET.*?ET Delay Sweep: Total time=([\d.]+)s', poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET.*?ET Delay Sweep: Total time=([\d.]+)s', poly_dpd_section) else ''
        result['Poly_DPD_ET_Delay_Sweep_Loops'] = re.search(r'Polynomial DPD ET.*?Number of loops=(\d+)',
                                                            poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET.*?Number of loops=(\d+)', poly_dpd_section) else ''
        result['Poly_DPD_ET_Avg_Loop_Time_s'] = re.search(r'Polynomial DPD ET.*?Average loop time=([\d.]+)s',
                                                          poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET.*?Average loop time=([\d.]+)s', poly_dpd_section) else ''
        result['Poly_DPD_ET_Avg_EVM_dB'] = re.search(r'Polynomial DPD ET.*?Average EVM=(-?[\d.]+)dB',
                                                     poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET.*?Average EVM=(-?[\d.]+)dB', poly_dpd_section) else ''
        result['Poly_DPD_ET_Disable_Time_s'] = re.search(r'Polynomial DPD ET.*?ET disable time,.*?([\d.]+)',
                                                         poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET.*?ET disable time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Poly_DPD_ET_Total_Time_s'] = re.search(r'Polynomial DPD ET total time \(incl. config\),.*?([\d.]+)s',
                                                       poly_dpd_section).group(1) if re.search(
            r'Polynomial DPD ET total time \(incl. config\),.*?([\d.]+)s', poly_dpd_section) else ''
        result['Poly_DPD_EVM_Total_Time_s'] = re.search(r'Polynomial dpd evm time,.*?([\d.]+)', poly_dpd_section).group(
            1) if re.search(r'Polynomial dpd evm time,.*?([\d.]+)', poly_dpd_section) else ''
        result['Total_Measurement_Time_s'] = re.search(r'Total measurement time at [\d.]+ GHz:.*?([\d.]+)',
                                                       block).group(1) if re.search(
            r'Total measurement time at [\d.]+ GHz:.*?([\d.]+)', block) else ''

        results.append(result)

    return results


def save_to_csv(parsed_data_list, output_file='console_output_summary_transposed.csv'):
    # Define field names (will become rows)
    field_names = [
        'Timestamp', 'Project_Name', 'Script_Path', 'Executable_Path', 'Status',
        'VSG_Setup_Time_s', 'VSA_Setup_Time_s', 'VSA_Initialization_Time_s',
        'Waveform_Configuration', 'Test_Frequency_GHz', 'VSG_Configure_Time_s',
        'VSA_Configure_Time_s', 'Baseline_Power_Servo_Gain_dB', 'Baseline_Power_Servo_Time_s',
        'Baseline_Power_Servo_Iterations', 'Baseline_EVM_dB', 'Baseline_5G_App_Power_dBm',
        'Baseline_Channel_Power_dBm', 'Baseline_EVM_Power_Time_s', 'Baseline_ACLR_Time_s',
        'Baseline_ET_Configure_Time_s', 'Baseline_ET_Loop_Time_s', 'Baseline_ET_Delay_Sweep_Time_s',
        'Baseline_ET_Delay_Sweep_Loops', 'Baseline_ET_Avg_Loop_Time_s', 'Baseline_ET_Avg_EVM_dB',
        'Baseline_ET_Disable_Time_s', 'Baseline_ET_Sweep_Total_Time_s', 'Baseline_EVM_Total_Time_s',
        'Poly_DPD_Amp_Setup_Time_s', 'Poly_DPD_Setup_Time_s', 'Poly_DPD_Servo_Gain_dB',
        'Poly_DPD_Servo_Time_s', 'Poly_DPD_Servo_Iterations', 'Poly_DPD_EVM_dB',
        'Poly_DPD_5G_App_Power_dBm', 'Poly_DPD_Channel_Power_dBm', 'Poly_DPD_EVM_Power_Time_s',
        'Poly_DPD_ACLR_Time_s', 'Poly_DPD_ET_Configure_Time_s', 'Poly_DPD_ET_Loop_Time_s',
        'Poly_DPD_ET_Delay_Sweep_Time_s', 'Poly_DPD_ET_Delay_Sweep_Loops',
        'Poly_DPD_ET_Avg_Loop_Time_s', 'Poly_DPD_ET_Avg_EVM_dB', 'Poly_DPD_ET_Disable_Time_s',
        'Poly_DPD_ET_Total_Time_s', 'Poly_DPD_EVM_Total_Time_s', 'Total_Measurement_Time_s'
    ]

    # Create a DataFrame for the new data
    new_data = pd.DataFrame({
        f"{data['Test_Frequency_GHz']}_GHz_{data['Timestamp']}": [data[field] for field in field_names]
        for data in parsed_data_list
    }, index=field_names)

    # If the file exists, append the new columns; otherwise, create a new file
    if os.path.isfile(output_file):
        existing_data = pd.read_csv(output_file, index_col=0)
        updated_data = pd.concat([existing_data, new_data], axis=1)
    else:
        updated_data = new_data

    # Save to CSV
    updated_data.to_csv(output_file)
    print(f"CSV file saved: {output_file}")


def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Parse console output from a log file and generate a transposed CSV.")
    parser.add_argument(
        '--log-file',
        default=os.path.join(os.path.dirname(__file__), '..', 'logs', 'test_output.log'),
        help='Path to the log file containing console output (default: ../logs/test_output.log)'
    )
    args = parser.parse_args()
    log_file_path = args.log_file

    # Check if log file exists
    if not os.path.isfile(log_file_path):
        print(f"Error: Log file not found at {log_file_path}")
        print(
            "Please ensure the measurement script saves output to the specified log file or provide the correct path using --log-file.")
        sys.exit(1)

    # Read console output from log file
    try:
        with open(log_file_path, 'r') as f:
            console_output = f.read()
    except Exception as e:
        print(f"Error reading log file {log_file_path}: {e}")
        sys.exit(1)

    # Parse the console output
    parsed_data_list = parse_console_output(console_output.strip())

    # Save to transposed CSV
    output_file = os.path.join(
        os.path.dirname(__file__),
        'console_output_summary_transposed.csv'
    )
    save_to_csv(parsed_data_list, output_file)

    # Print user-friendly summary
    print("Console Output Summary (Transposed CSV created):")
    for data in parsed_data_list:
        print(f"\nFrequency: {data['Test_Frequency_GHz']} GHz")
        for key, value in data.items():
            if value:  # Only print non-empty values
                print(f"{key}: {value}")


if __name__ == "__main__":
    main()