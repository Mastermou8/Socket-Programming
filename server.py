import socket
import os
import hashlib
import threading

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

# Track files being processed
files_in_use = set()
files_lock = threading.Lock()


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


def handle_upload(conn, addr):
    """Handle file upload from client"""
    try:
        conn.send("READY".encode(FORMAT))

        # Receive file metadata
        data = conn.recv(SIZE).decode(FORMAT)
        filename, filesize = data.split("@")
        filesize = int(filesize)

        filepath = os.path.join(SERVER_DATA_PATH, filename)

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

        print(f"[{addr}] File '{filename}' uploaded successfully.")
        conn.send(f"File '{filename}' uploaded successfully.".encode(FORMAT))
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
        # List all files and subdirectories
        items = []
        for root, dirs, files in os.walk(SERVER_DATA_PATH):
            level = root.replace(SERVER_DATA_PATH, '').count(os.sep)
            indent = ' ' * 2 * level
            rel_path = os.path.relpath(root, SERVER_DATA_PATH)
            if rel_path == '.':
                items.append(f"[{SERVER_DATA_PATH}]")
            else:
                items.append(f"{indent}[{os.path.basename(root)}/]")

            sub_indent = ' ' * 2 * (level + 1)
            for file in files:
                items.append(f"{sub_indent}{file}")

        if not items:
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