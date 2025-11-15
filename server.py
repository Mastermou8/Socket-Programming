import socket
import os
import hashlib
import threading
import mimetypes
from collections import defaultdict
from analysis import NetworkAnalysis
import time

# --- CONSTANTS ---
IP = socket.gethostbyname(socket.gethostname())
PORT = 4450
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_DATA_PATH = "server_data"

# Simple user database (username: hashed_password)
USERS = {
    "admin": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",
    "user1": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
}


# --- HELPER FUNCTIONS (Kept outside the class for simplicity/modularity) ---

def get_file_type_prefix(filename):
    """Determine file type prefix based on MIME type"""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        if mime_type.startswith('text/'):
            return 'TS'
        elif mime_type.startswith('video/'):
            return 'VS'
        elif mime_type.startswith('image/'):
            return 'IS'
        elif mime_type.startswith('audio/'):
            return 'AS'
        elif mime_type.startswith('application/pdf'):
            return 'PS'
        elif mime_type.startswith('application/'):
            return 'DS'
    return 'FS'


class FileServer:
    def __init__(self, ip=IP, port=PORT, data_path=SERVER_DATA_PATH):
        self.ip = ip
        self.port = port
        self.addr = (ip, port)
        self.data_path = data_path

        self.server = None
        self.server_analyzer = NetworkAnalysis(role="Server", address=f"{self.ip}:{self.port}")

        # Multithreading components
        self.shutdown_flag = threading.Event()
        self.accept_thread = None

        # State tracking
        self.active_clients = {}
        self.clients_lock = threading.Lock()
        self.files_in_use = set()
        self.files_lock = threading.Lock()
        self.file_counters = defaultdict(int)
        self.counter_lock = threading.Lock()

        # Initial setup
        self._setup_data_directory()
        self._get_existing_file_count()

    # --- Setup Methods ---

    def _setup_data_directory(self):
        """Create the server data directory if it doesn't exist"""
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

    def _get_existing_file_count(self):
        """Count existing files by type to initialize counters"""
        if not os.path.exists(self.data_path):
            return

        with self.counter_lock:
            for filename in os.listdir(self.data_path):
                if len(filename) >= 5:
                    prefix = filename[:2]
                    try:
                        num = int(filename[2:5])
                        if num > self.file_counters[prefix]:
                            self.file_counters[prefix] = num
                    except ValueError:
                        pass
        print(f"[INIT] File counters initialized: {dict(self.file_counters)}")

    def _generate_logical_filename(self, original_filename):
        """Generate logical filename with type prefix and counter"""
        _, ext = os.path.splitext(original_filename)
        prefix = get_file_type_prefix(original_filename)

        with self.counter_lock:
            self.file_counters[prefix] += 1
            counter = self.file_counters[prefix]

        return f"{prefix}{counter:03d}{ext}"

    # --- Client Pool Management ---

    def _add_client_to_pool(self, addr, username):
        """Add client to connection pool"""
        with self.clients_lock:
            self.active_clients[addr] = {
                'username': username,
                'connected_at': threading.current_thread().name
            }
            print(f"[CLIENT POOL] Added {username}@{addr}. Total clients: {len(self.active_clients)}")

    def _remove_client_from_pool(self, addr):
        """Remove client from connection pool"""
        with self.clients_lock:
            if addr in self.active_clients:
                username = self.active_clients[addr]['username']
                del self.active_clients[addr]
                print(f"[CLIENT POOL] Removed {username}@{addr}. Total clients: {len(self.active_clients)}")

    def list_active_clients(self):
        """Return list of active clients"""
        with self.clients_lock:
            return list(self.active_clients.items())

    # --- Core Server Methods ---

    def start(self):
        """Initialize and start the server listener thread"""
        if self.server:
            print("[ERROR] Server is already running.")
            return

        print(f"[STARTING] Server is starting on {self.ip}:{self.port}...")

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(self.addr)
            self.server.listen()
            self.server.settimeout(1.0)

            self.shutdown_flag.clear()
            self.accept_thread = threading.Thread(target=self._accept_clients_loop, name="AcceptThread")
            self.accept_thread.start()

            print(f"[LISTENING] Server is listening on {self.ip}:{self.port}")
            return True

        except Exception as e:
            print(f"[FATAL ERROR] Could not start server: {e}")
            self.server = None
            return False

    def stop(self):
        """Gracefully stop the server"""
        if not self.server:
            print("[STOP] Server is not running.")
            return

        print("[STOPPING] Server shutdown initiated...")
        self.shutdown_flag.set()

        # Give the accept thread a moment to finish its current loop
        self.accept_thread.join(timeout=2)

        # Close the server socket
        self.server.close()
        self.server = None

        # Save statistics
        self.server_analyzer.save_stats(filename="server_network_stats.csv")

        print("[SHUTDOWN] Server closed.")
        print(f"[FINAL STATS] Total active clients at shutdown: {len(self.list_active_clients())}")

    def _accept_clients_loop(self):
        """The main loop for accepting new client connections"""
        while not self.shutdown_flag.is_set():
            try:
                conn, addr = self.server.accept()
                thread = threading.Thread(target=self._handle_client, args=(conn, addr), name=f"Client-{addr[1]}")
                thread.start()
                print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 2}")
            except socket.timeout:
                continue
            except Exception as e:
                if not self.shutdown_flag.is_set():
                    print(f"[ERROR in Accept Loop] {e}")

    # --- Client Handler Methods (Mostly unchanged logic, now prefixed with _) ---

    def _authenticate_client(self, conn):
        """Authenticate client with username and hashed password"""
        try:
            conn.send("Please authenticate to continue.".encode(FORMAT))
            credentials = conn.recv(SIZE).decode(FORMAT)
            username, hashed_password = credentials.split("@")

            if username in USERS and USERS[username] == hashed_password:
                conn.send("AUTH_SUCCESS".encode(FORMAT))
                return True, username
            else:
                conn.send("AUTH_FAILED".encode(FORMAT))
                return False, None
        except Exception as e:
            print(f"Authentication error: {e}")
            return False, None

    def _handle_upload(self, conn, addr):
        """Handle file upload from client"""
        try:
            conn.send("READY".encode(FORMAT))
            data = conn.recv(SIZE).decode(FORMAT)
            original_filename, filesize = data.split("@")
            filesize = int(filesize)

            logical_filename = self._generate_logical_filename(original_filename)
            filepath = os.path.join(self.data_path, logical_filename)

            if os.path.exists(filepath):
                conn.send("EXISTS".encode(FORMAT))
                overwrite = conn.recv(SIZE).decode(FORMAT)
                if overwrite.lower() != "yes":
                    return

            conn.send("OK".encode(FORMAT))

            with open(filepath, "wb") as f:
                received = 0
                while received < filesize:
                    data = conn.recv(SIZE)
                    if not data:
                        break
                    f.write(data)
                    received += len(data)

            print(f"[{addr}] File '{original_filename}' uploaded as '{logical_filename}'.")
            conn.send(f"File uploaded successfully as '{logical_filename}'.".encode(FORMAT))
        except Exception as e:
            print(f"[{addr}] Upload error: {e}")
            conn.send(f"ERROR: Upload failed - {e}".encode(FORMAT))

    def _handle_download(self, conn, addr):
        """Handle file download request"""
        filename = ""  # Initialize filename for finally block
        try:
            conn.send("READY".encode(FORMAT))
            filename = conn.recv(SIZE).decode(FORMAT)
            filepath = os.path.join(self.data_path, filename)

            if not os.path.exists(filepath):
                conn.send(f"ERROR: File '{filename}' not found.".encode(FORMAT))
                return

            with self.files_lock:
                if filename in self.files_in_use:
                    conn.send(f"ERROR: File '{filename}' is currently being processed.".encode(FORMAT))
                    return
                self.files_in_use.add(filename)

            try:
                filesize = os.path.getsize(filepath)
                conn.send(str(filesize).encode(FORMAT))
                conn.recv(SIZE)  # Wait for READY signal

                with open(filepath, "rb") as f:
                    while True:
                        data = f.read(SIZE)
                        if not data:
                            break
                        conn.send(data)

                print(f"[{addr}] File '{filename}' downloaded.")
            finally:
                with self.files_lock:
                    self.files_in_use.discard(filename)
        except Exception as e:
            print(f"[{addr}] Download error: {e}")
            with self.files_lock:
                self.files_in_use.discard(filename)

    def _handle_delete(self, conn, addr, filename):
        """Handle file deletion request"""
        try:
            filepath = os.path.join(self.data_path, filename)

            if not os.path.exists(filepath):
                conn.send(f"ERROR: File '{filename}' not found.".encode(FORMAT))
                return

            with self.files_lock:
                if filename in self.files_in_use:
                    conn.send(f"ERROR: File '{filename}' is currently being processed.".encode(FORMAT))
                    return

            os.remove(filepath)
            print(f"[{addr}] File '{filename}' deleted.")
            conn.send(f"File '{filename}' deleted successfully.".encode(FORMAT))
        except Exception as e:
            print(f"[{addr}] Delete error: {e}")
            conn.send(f"ERROR: Could not delete file - {e}".encode(FORMAT))

    def _handle_dir(self, conn, addr):
        """Handle directory listing request"""
        try:
            items = []
            # ... (DIR formatting logic is the same)
            items.append(f"{'Filename':<20} {'Type':<10} {'Size (bytes)':<15}")
            items.append("-" * 50)

            type_map = {
                'TS': 'Text', 'VS': 'Video', 'IS': 'Image', 'AS': 'Audio',
                'PS': 'PDF', 'DS': 'Document', 'FS': 'File'
            }

            for root, dirs, files in os.walk(self.data_path):
                level = root.replace(self.data_path, '').count(os.sep)
                indent = ' ' * 2 * level
                rel_path = os.path.relpath(root, self.data_path)

                if rel_path == '.':
                    items.append(f"\n[{self.data_path}]")
                else:
                    items.append(f"{indent}[{os.path.basename(root)}/]")

                sub_indent = ' ' * 2 * (level + 1)
                for file in sorted(files):
                    file_type = file[:2] if len(file) >= 2 else "??"
                    type_name = type_map.get(file_type, 'Unknown')
                    filepath = os.path.join(root, file)
                    size = os.path.getsize(filepath)
                    items.append(f"{sub_indent}{file:<20} {type_name:<10} {size:<15}")

            if len(items) <= 2:
                response = "Directory is empty."
            else:
                response = "\n".join(items)

            conn.send(response.encode(FORMAT))
            print(f"[{addr}] Directory listing sent.")
        except Exception as e:
            print(f"[{addr}] Dir error: {e}")
            conn.send(f"ERROR: Could not list directory - {e}".encode(FORMAT))

    def _handle_subfolder(self, conn, addr, action, path):
        """Handle subfolder creation/deletion"""
        try:
            full_path = os.path.join(self.data_path, path)

            if action == "CREATE":
                if os.path.exists(full_path):
                    conn.send(f"ERROR: Folder '{path}' already exists.".encode(FORMAT))
                else:
                    os.makedirs(full_path)
                    print(f"[{addr}] Folder '{path}' created.")
                    conn.send(f"Folder '{path}' created successfully.".encode(FORMAT))

            elif action == "DELETE":
                if not os.path.exists(full_path):
                    conn.send(f"ERROR: Folder '{path}' not found.".encode(FORMAT))
                elif not os.path.isdir(full_path):
                    conn.send(f"ERROR: '{path}' is not a directory.".encode(FORMAT))
                else:
                    os.rmdir(full_path)
                    print(f"[{addr}] Folder '{path}' deleted.")
                    conn.send(f"Folder '{path}' deleted successfully.".encode(FORMAT))

        except OSError as e:
            if action == "DELETE":
                conn.send(f"ERROR: Cannot delete folder (may not be empty) - {e}".encode(FORMAT))
            else:
                conn.send(f"ERROR: Folder operation failed - {e}".encode(FORMAT))
        except Exception as e:
            print(f"[{addr}] Subfolder error: {e}")
            conn.send(f"ERROR: Operation failed - {e}".encode(FORMAT))

    def _handle_client(self, conn, addr):
        """Handle client connection in a separate thread"""
        print(f"[NEW CONNECTION] {addr} connected.")
        session_start_time = self.server_analyzer.start_record_time()
        username = "N/A"  # Default username

        try:
            conn.send("OK@Welcome to the server".encode(FORMAT))

            start_time_auth = self.server_analyzer.start_record_time()
            authenticated, username = self._authenticate_client(conn)
            self.server_analyzer.stop_record_time(start_time_auth, bytes_transferred=0, operation="SERVER_AUTH")

            if not authenticated:
                print(f"[{addr}] Authentication failed.")
                conn.close()
                return

            print(f"[{addr}] User '{username}' authenticated.")
            self._add_client_to_pool(addr, username)

        except Exception as e:
            print(f"[{addr}] Connection error during auth: {e}")
            conn.close()
            return

        try:
            while not self.shutdown_flag.is_set():
                data = conn.recv(SIZE).decode(FORMAT)

                if not data:
                    break

                # --- Command Handling with Server Response Time Recording ---
                start_time_op = self.server_analyzer.start_record_time()
                operation_type = "UNKNOWN"

                if data == "UPLOAD":
                    self._handle_upload(conn, addr)
                    operation_type = "SERVER_UPLOAD_RESP"
                elif data == "DOWNLOAD":
                    self._handle_download(conn, addr)
                    operation_type = "SERVER_DOWNLOAD_RESP"
                elif data.startswith("DELETE@"):
                    _, filename = data.split("@", 1)
                    self._handle_delete(conn, addr, filename)
                    operation_type = "SERVER_DELETE_RESP"
                elif data == "DIR":
                    self._handle_dir(conn, addr)
                    operation_type = "SERVER_DIR_RESP"
                elif data.startswith("SUBFOLDER@"):
                    parts = data.split("@")
                    if len(parts) == 3:
                        _, action, path = parts
                        self._handle_subfolder(conn, addr, action, path)
                        operation_type = "SERVER_SUBFOLDER_RESP"
                elif data == "LOGOUT":
                    print(f"[{addr}] Client logged out.")
                    break
                else:
                    print(f"[{addr}] Unknown command: {data}")
                    conn.send(f"ERROR: Unknown command '{data}'".encode(FORMAT))

                # Record the server-side processing time for the command
                if operation_type != "UNKNOWN":
                    self.server_analyzer.stop_record_time(start_time_op, bytes_transferred=0, operation=operation_type)

        except Exception as e:
            print(f"[{addr}] Error: {e}")
        finally:
            self.server_analyzer.stop_record_time(session_start_time, bytes_transferred=0,
                                                  operation="SERVER_SESSION_TOTAL")
            self._remove_client_from_pool(addr)
            conn.close()
            print(f"[{addr}] Disconnected.")


# --- Main execution block for testing the server as a standalone application ---
#if __name__ == "__main__":
    """server_app = FileServer()
    server_app.start()

    try:
        # Keep the main thread alive to allow server threads to run
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass  # Fall through to the finally block to stop the server
    finally:
        server_app.stop()"""