import socket
import os
import hashlib
import threading
import mimetypes
from collections import defaultdict

IP = "192.168.131.8"
PORT = 4450
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_DATA_PATH = "server_data"

# Simple user database (username: hashed_password)
# Password for both users is "password123" (hashed)
USERS = {
    "admin": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",
    "user1": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
}

# Client connection pool
active_clients = {}
clients_lock = threading.Lock()

# Track files being processed
files_in_use = set()
files_lock = threading.Lock()

# File counter for logical naming (type -> counter)
file_counters = defaultdict(int)
counter_lock = threading.Lock()


def get_file_type_prefix(filename):
    """Determine file type prefix based on MIME type"""
    mime_type, _ = mimetypes.guess_type(filename)

    if mime_type:
        if mime_type.startswith('text/'):
            return 'TS'  # Text-Server
        elif mime_type.startswith('video/'):
            return 'VS'  # Video-Server
        elif mime_type.startswith('image/'):
            return 'IS'  # Image-Server
        elif mime_type.startswith('audio/'):
            return 'AS'  # Audio-Server
        elif mime_type.startswith('application/pdf'):
            return 'PS'  # PDF-Server
        elif mime_type.startswith('application/'):
            return 'DS'  # Document-Server

    return 'FS'  # File-Server (generic)


def generate_logical_filename(original_filename):
    """Generate logical filename with type prefix and counter"""
    # Get file extension
    _, ext = os.path.splitext(original_filename)

    # Get file type prefix
    prefix = get_file_type_prefix(original_filename)

    # Increment counter for this file type
    with counter_lock:
        file_counters[prefix] += 1
        counter = file_counters[prefix]

    # Generate logical name: TS001.txt, VS002.mp4, etc.
    logical_name = f"{prefix}{counter:03d}{ext}"

    return logical_name


def get_existing_file_count():
    """Count existing files by type to initialize counters"""
    if not os.path.exists(SERVER_DATA_PATH):
        return

    with counter_lock:
        for filename in os.listdir(SERVER_DATA_PATH):
            # Extract prefix from existing files (e.g., TS001.txt -> TS)
            if len(filename) >= 5:
                prefix = filename[:2]
                try:
                    num = int(filename[2:5])
                    if num > file_counters[prefix]:
                        file_counters[prefix] = num
                except ValueError:
                    pass


def authenticate_client(conn):
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


def add_client_to_pool(addr, username):
    """Add client to connection pool"""
    with clients_lock:
        active_clients[addr] = {
            'username': username,
            'connected_at': threading.current_thread().name
        }
        print(f"[CLIENT POOL] Added {username}@{addr}. Total clients: {len(active_clients)}")


def remove_client_from_pool(addr):
    """Remove client from connection pool"""
    with clients_lock:
        if addr in active_clients:
            username = active_clients[addr]['username']
            del active_clients[addr]
            print(f"[CLIENT POOL] Removed {username}@{addr}. Total clients: {len(active_clients)}")


def list_active_clients():
    """Return list of active clients"""
    with clients_lock:
        return list(active_clients.items())


def handle_upload(conn, addr):
    """Handle file upload from client"""
    try:
        conn.send("READY".encode(FORMAT))

        # Receive file metadata
        data = conn.recv(SIZE).decode(FORMAT)
        original_filename, filesize = data.split("@")
        filesize = int(filesize)

        # Generate logical filename
        logical_filename = generate_logical_filename(original_filename)
        filepath = os.path.join(SERVER_DATA_PATH, logical_filename)

        # Check if file exists
        if os.path.exists(filepath):
            conn.send("EXISTS".encode(FORMAT))

            # Wait for client decision
            overwrite = conn.recv(SIZE).decode(FORMAT)

            if overwrite.lower() != "yes":
                return

        conn.send("OK".encode(FORMAT))

        # Receive file data
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


def handle_download(conn, addr):
    """Handle file download request"""
    try:
        conn.send("READY".encode(FORMAT))

        # Receive filename
        filename = conn.recv(SIZE).decode(FORMAT)
        filepath = os.path.join(SERVER_DATA_PATH, filename)

        # Check if file exists
        if not os.path.exists(filepath):
            conn.send(f"ERROR: File '{filename}' not found.".encode(FORMAT))
            return

        # Check if file is being processed
        with files_lock:
            if filename in files_in_use:
                conn.send(f"ERROR: File '{filename}' is currently being processed.".encode(FORMAT))
                return
            files_in_use.add(filename)

        try:
            # Send file size
            filesize = os.path.getsize(filepath)
            conn.send(str(filesize).encode(FORMAT))

            # Wait for ready signal
            conn.recv(SIZE)

            # Send file data
            with open(filepath, "rb") as f:
                while True:
                    data = f.read(SIZE)
                    if not data:
                        break
                    conn.send(data)

            print(f"[{addr}] File '{filename}' downloaded.")
        finally:
            with files_lock:
                files_in_use.discard(filename)
    except Exception as e:
        print(f"[{addr}] Download error: {e}")
        with files_lock:
            files_in_use.discard(filename)


def handle_delete(conn, addr, filename):
    """Handle file deletion request"""
    try:
        filepath = os.path.join(SERVER_DATA_PATH, filename)

        # Check if file exists
        if not os.path.exists(filepath):
            conn.send(f"ERROR: File '{filename}' not found.".encode(FORMAT))
            return

        # Check if file is being processed
        with files_lock:
            if filename in files_in_use:
                conn.send(f"ERROR: File '{filename}' is currently being processed.".encode(FORMAT))
                return

        # Delete file
        os.remove(filepath)
        print(f"[{addr}] File '{filename}' deleted.")
        conn.send(f"File '{filename}' deleted successfully.".encode(FORMAT))
    except Exception as e:
        print(f"[{addr}] Delete error: {e}")
        conn.send(f"ERROR: Could not delete file - {e}".encode(FORMAT))


def handle_dir(conn, addr):
    """Handle directory listing request"""
    try:
        # List all files and subdirectories with file type info
        items = []
        items.append(f"{'Filename':<20} {'Type':<10} {'Size (bytes)':<15}")
        items.append("-" * 50)

        for root, dirs, files in os.walk(SERVER_DATA_PATH):
            level = root.replace(SERVER_DATA_PATH, '').count(os.sep)
            indent = ' ' * 2 * level
            rel_path = os.path.relpath(root, SERVER_DATA_PATH)

            if rel_path == '.':
                items.append(f"\n[{SERVER_DATA_PATH}]")
            else:
                items.append(f"{indent}[{os.path.basename(root)}/]")

            sub_indent = ' ' * 2 * (level + 1)
            for file in sorted(files):
                # Determine file type from logical naming
                file_type = file[:2] if len(file) >= 2 else "??"
                type_map = {
                    'TS': 'Text',
                    'VS': 'Video',
                    'IS': 'Image',
                    'AS': 'Audio',
                    'PS': 'PDF',
                    'DS': 'Document',
                    'FS': 'File'
                }
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


def handle_subfolder(conn, addr, action, path):
    """Handle subfolder creation/deletion"""
    try:
        full_path = os.path.join(SERVER_DATA_PATH, path)

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


def handle_client(conn, addr):
    """Handle client connection"""
    print(f"[NEW CONNECTION] {addr} connected.")

    try:
        # Send welcome message
        conn.send("OK@Welcome to the server".encode(FORMAT))

        # Authenticate client
        authenticated, username = authenticate_client(conn)

        if not authenticated:
            print(f"[{addr}] Authentication failed.")
            conn.close()
            return

        print(f"[{addr}] User '{username}' authenticated.")
    except Exception as e:
        print(f"[{addr}] Connection error during auth: {e}")
        conn.close()
        return

    try:
        while True:
            # Receive command
            data = conn.recv(SIZE).decode(FORMAT)

            if not data:
                break

            if data == "UPLOAD":
                handle_upload(conn, addr)

            elif data == "DOWNLOAD":
                handle_download(conn, addr)

            elif data.startswith("DELETE@"):
                _, filename = data.split("@", 1)
                handle_delete(conn, addr, filename)

            elif data == "DIR":
                handle_dir(conn, addr)

            elif data.startswith("SUBFOLDER@"):
                parts = data.split("@")
                if len(parts) == 3:
                    _, action, path = parts
                    handle_subfolder(conn, addr, action, path)

            elif data == "LOGOUT":
                print(f"[{addr}] Client logged out.")
                break

    except Exception as e:
        print(f"[{addr}] Error: {e}")
    finally:
        conn.close()
        print(f"[{addr}] Disconnected.")


def main():
    # Create server data directory if it doesn't exist
    if not os.path.exists(SERVER_DATA_PATH):
        os.makedirs(SERVER_DATA_PATH)

    print("[STARTING] Server is starting...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(ADDR)
    server.listen()
    print(f"[LISTENING] Server is listening on {IP}:{PORT}")
    print("Press Ctrl+C to stop the server\n")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("\n[STOPPING] Server is shutting down...")
    finally:
        server.close()


if __name__ == "__main__":
    main()