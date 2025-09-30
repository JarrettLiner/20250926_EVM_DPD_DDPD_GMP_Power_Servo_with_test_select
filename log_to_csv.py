import csv
import os
from datetime import datetime

class CSVLogger:
    def __init__(self, output_dir, filename_prefix="test_results"):
        """
        Initialize CSV logger.

        Args:
            output_dir (str): Directory to save CSV files.
            filename_prefix (str): Prefix for CSV filenames.
        """
        self.output_dir = output_dir
        self.filename_prefix = filename_prefix
        self.data = []
        self.headers = [
            "Test description",
            "individual test blocks",
            "test function totals",
            "test block totals",
            "not added to total time"
        ]

    def add_data(self, description, individual="", function_total="", block_total="", not_added=""):
        """
        Add a row of data to the CSV.

        Args:
            description (str): Test description or metric name.
            individual (str/float): Value for individual test blocks.
            function_total (str/float): Value for test function totals.
            block_total (str/float): Value for test block totals.
            not_added (str/float): Value for non-test block times.
        """
        self.data.append([description, individual, function_total, block_total, not_added])

    def add_from_module(self, module):
        """
        Add data from a module's csv_data attribute.

        Args:
            module: Module instance with csv_data attribute (e.g., ET, VSA).
        """
        if hasattr(module, 'csv_data'):
            self.data.extend(module.csv_data)

    def write_csv(self):
        """
        Write collected data to a CSV file with a timestamped filename.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.filename_prefix}_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        os.makedirs(self.output_dir, exist_ok=True)

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            for row in self.data:
                writer.writerow(row)
        return filepath