import os
import pandas as pd
import time

class NetworkAnalysis:
    def __init__(self, role, address):
        self.role = role # To determine if it is a client or server
        self.address = address # For the server IP and port
        self.stats_data = []

    def start_record_time(self):
        start_time = time.time()
        return start_time

    def stop_record_time(self, start_time, bytes_transferred=0):
        end_time = time.time()

        if start_time is None:
            print("Error: start time can't be None")
            return

        total_time = end_time - start_time
        if total_time > 0:
            data_rate = bytes_transferred / total_time

        self.stats_data.append({
            'Timestamp': pd.Timestamp.now(),
            'Role': self.role,
            'Address': self.address,
            'Duration_s': total_time,
            'Bytes_Transferred': bytes_transferred,
            'Data_Rate': data_rate,
        })

    def save_stats(self, filename = "network_stats.csv"):
        df = pd.DataFrame(self.stats_data)

        # Check if file exists to determine if header should be written
        if os.path.exists(filename):
            # Append without header
            df.to_csv(filename, mode='a', header=False, index=False)
        else:
            # Write with header
            df.to_csv(filename, mode='w', header=True, index=False)
        print(f"\n[{self.role}] Statistics saved to {filename}")


