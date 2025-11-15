import socket
import os
import hashlib
from analysis import NetworkAnalysis as NA
import time
import getpass  # Kept for potential future console use, but GUI will handle input

# --- CONSTANTS ---
IP = "192.168.131.12"
PORT = 4450
SIZE = 1024
FORMAT = "utf-8"
SERVER_DATA_PATH = "server_data"  # Not used directly in client class, but kept for context


class FileClient:
    def __init__(self, ip=IP, port=PORT, log_callback=None):
        self.ip = ip
        self.port = port
        self.addr = (ip, port)
        self.client_socket = None
        self.analyzer = None
        self.is_connected = False
        self.is_authenticated = False
        self.username = None
        self.log_callback = log_callback  # Function passed by the UI for logging

        self._log(f"Initialized with target server: {self.ip}:{self.port}")

    # --- Internal Helpers ---

    def _log(self, message):
        """Internal logging method that calls the GUI callback or prints."""
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] [CLIENT]")
        full_message = f"{timestamp} {message}"

        if self.log_callback:
            # Send the message to the GUI's log widget
            self.log_callback(full_message)
        else:
            # Fallback to console printing
            print(full_message)

    @staticmethod
    def _hash_password(password):
        """Hash password using SHA-256 for secure transmission."""
        return hashlib.sha256(password.encode()).hexdigest()

    # --- Connection and Authentication ---

    def connect(self):
        """Creates socket, connects to server, and initializes analyzer."""
        if self.is_connected:
            self._log("Already connected.")
            return True

        self._log(f"Attempting to connect to {self.ip}:{self.port}...")

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)  # Set 10 second timeout
            self.client_socket.connect(self.addr)
            self.is_connected = True
            self._log(f"Successfully connected to server at {self.ip}:{self.port}")

            # Initialize network analyzer
            self.analyzer = NA(role="Client", address=f"{self.ip}:{self.port}")

            # Receive welcome message from server (if any)
            try:
                welcome_msg = self.client_socket.recv(SIZE).decode(FORMAT)
                if "@" in welcome_msg:
                    cmd, msg = welcome_msg.split("@", 1)
                    if cmd == "OK":
                        self._log(f"Server Welcome: {msg}")
            except socket.timeout:
                self._log("Warning: No welcome message received from server.")

            return True

        except ConnectionRefusedError:
            self.is_connected = False
            self._log(f"Error: Could not connect to server at {self.ip}:{self.port}")
            return False
        except Exception as e:
            self.is_connected = False
            self._log(f"Connection error: {e}")
            return False

    def authenticate(self, username, password):
        """Handle client authentication with provided credentials."""
        if not self.is_connected:
            return "ERROR: Not connected to server."

        try:
            # Receive authentication prompt
            msg = self.client_socket.recv(SIZE).decode(FORMAT)
            self._log(f"Server Prompt: {msg}")

            # Hash password before sending
            hashed_password = self._hash_password(password)

            # Send credentials
            self.client_socket.send(f"{username}@{hashed_password}".encode(FORMAT))

            # Receive authentication result
            response = self.client_socket.recv(SIZE).decode(FORMAT)

            if response == "AUTH_SUCCESS":
                self.is_authenticated = True
                self.username = username
                self._log("Authentication successful!")
                return "AUTH_SUCCESS"
            else:
                self._log("Authentication failed. Invalid credentials.")
                return "AUTH_FAILED"
        except Exception as e:
            self._log(f"Authentication error: {e}")
            self.disconnect()
            return f"ERROR: {e}"

    def disconnect(self):
        """Logs out and closes the client socket."""
        if self.is_connected:
            try:
                if self.is_authenticated:
                    self.client_socket.send("LOGOUT".encode(FORMAT))
                    self._log("Logging out...")

                self.client_socket.close()
                self._log("Disconnected from the server.")
            except Exception as e:
                self._log(f"Error during disconnect: {e}")
            finally:
                # Save statistics before closing
                if self.analyzer:
                    self.analyzer.save_stats(filename="client_network_stats.csv")

        self.client_socket = None
        self.is_connected = False
        self.is_authenticated = False
        self.username = None
        return "DISCONNECTED"

    # --- File Operations ---

    def send_file(self, filepath, overwrite="no"):
        """Send file to server. Returns status message."""
        if not self.is_authenticated:
            return "ERROR: Not authenticated."

        self.client_socket.send("UPLOAD".encode(FORMAT))
        self.client_socket.recv(SIZE)  # Wait for server READY signal

        try:
            filesize = os.path.getsize(filepath)
            filename = os.path.basename(filepath)

            start_time = self.analyzer.start_record_time()
            bytes_transferred = 0

            self.client_socket.send(f"{filename}@{filesize}".encode(FORMAT))

            response = self.client_socket.recv(SIZE).decode(FORMAT)

            if response == "EXISTS":
                # overwrite is provided by the GUI now
                self.client_socket.send(overwrite.encode(FORMAT))
                if overwrite.lower() != "yes":
                    self._log("Upload cancelled by user (file exists).")
                    return "CANCELLED: File already exists on server."

                response = self.client_socket.recv(SIZE).decode(FORMAT)

            if response == "OK":
                with open(filepath, "rb") as f:
                    while True:
                        data = f.read(SIZE)
                        if not data:
                            break
                        self.client_socket.send(data)
                        bytes_transferred += len(data)

                msg = self.client_socket.recv(SIZE).decode(FORMAT)
                self._log(msg)

                self.analyzer.stop_record_time(start_time, bytes_transferred, operation="CLIENT_UPLOAD")
                return f"SUCCESS: {msg}"

            return f"ERROR: Unexpected server response during upload: {response}"

        except FileNotFoundError:
            return f"ERROR: File '{filepath}' not found."
        except Exception as e:
            self._log(f"Error uploading file: {e}")
            return f"ERROR: Upload failed - {e}"

    def receive_file(self, filename):
        """Download file from server. Returns status message."""
        if not self.is_authenticated:
            return "ERROR: Not authenticated."

        self.client_socket.send("DOWNLOAD".encode(FORMAT))
        self.client_socket.recv(SIZE)  # Wait for server READY signal

        try:
            start_time = self.analyzer.start_record_time()
            self.client_socket.send(filename.encode(FORMAT))

            response = self.client_socket.recv(SIZE).decode(FORMAT)

            if response.startswith("ERROR"):
                self._log(response)
                return response

            filesize = int(response)
            self.client_socket.send("READY".encode(FORMAT))

            # Use filedialog.asksaveasfilename in the GUI, but here we use a simple path
            save_path = os.path.join(os.getcwd(), filename)

            bytes_transferred = 0
            with open(save_path, "wb") as f:
                received = 0
                while received < filesize:
                    data = self.client_socket.recv(SIZE)
                    if not data:
                        break
                    f.write(data)
                    received += len(data)
                    bytes_transferred += len(data)

            self._log(f"File '{filename}' downloaded successfully to {save_path}.")

            self.analyzer.stop_record_time(start_time, bytes_transferred, operation="CLIENT_DOWNLOAD")
            return f"SUCCESS: File '{filename}' downloaded successfully to {os.getcwd()}."

        except Exception as e:
            self._log(f"Error downloading file: {e}")
            return f"ERROR: Download failed - {e}"

    def handle_delete(self, filename):
        """Handle delete command. Returns server response."""
        if not self.is_authenticated:
            return "ERROR: Not authenticated."

        start_time = self.analyzer.start_record_time()
        self.client_socket.send(f"DELETE@{filename}".encode(FORMAT))
        response = self.client_socket.recv(SIZE).decode(FORMAT)
        self._log(response)
        self.analyzer.stop_record_time(start_time, 0, operation="CLIENT_DELETE")
        return response

    def handle_dir(self):
        """Handle directory listing. Returns directory listing string."""
        if not self.is_authenticated:
            return "ERROR: Not authenticated."

        start_time = self.analyzer.start_record_time()
        self.client_socket.send("DIR".encode(FORMAT))
        response = self.client_socket.recv(SIZE).decode(FORMAT)
        self._log("\n--- Server Directory Listing ---")
        self._log(response)

        self.analyzer.stop_record_time(start_time, len(response.encode(FORMAT)), operation="CLIENT_DIR")
        return response

    def handle_subfolder(self, action, path):
        """Handle subfolder operations. Returns server response."""
        if not self.is_authenticated:
            return "ERROR: Not authenticated."

        start_time = self.analyzer.start_record_time()
        self.client_socket.send(f"SUBFOLDER@{action}@{path}".encode(FORMAT))
        response = self.client_socket.recv(SIZE).decode(FORMAT)
        self._log(response)
        self.analyzer.stop_record_time(start_time, 0, operation="CLIENT_SUBFOLDER")
        return response