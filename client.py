import socket
import os
import hashlib
import getpass
from analysis import NetworkAnalysis

# Set a placeholder IP, it will be updated by user input
IP = "127.0.0.1" 
PORT = 4450
ADDR = (IP, PORT)
SIZE = 1024
FORMAT = "utf-8"
SERVER_DATA_PATH = "server_data"


def hash_password(password):
    """Hash password using SHA-256 for secure transmission"""
    return hashlib.sha256(password.encode()).hexdigest()


def send_file(client, filepath, analyzer):
    """Send file to server"""
    try:
        #gather file information
        filesize = os.path.getsize(filepath)
        filename = os.path.basename(filepath)

        # Start timing for upload
        start_time = analyzer.start_record_time()
        bytes_transferred = 0

        # Send file data
        client.send(f"{filename}@{filesize}".encode(FORMAT))

        # wait until server respons
        response = client.recv(SIZE).decode(FORMAT)

        if response == "EXISTS":
            #overwrite files
            overwrite = input("File already exists. Overwrite? (yes/no): ")
            client.send(overwrite.encode(FORMAT))
            #check if user said anything other than yes to cancel
            if overwrite.lower() != "yes":
                print("Upload cancelled.")
                return

            # Wait for final OK
            response = client.recv(SIZE).decode(FORMAT)
        #user confirmation
        if response == "OK":
            # Send data of the file
            with open(filepath, "rb") as f:
                while True:
                    data = f.read(SIZE)
                    if not data:
                        break
                    client.send(data)
                    bytes_transferred += len(data)

            # Receive confirmation
            msg = client.recv(SIZE).decode(FORMAT)
            print(msg)

            # Stop timing and record stats
            analyzer.stop_record_time(start_time, bytes_transferred, operation="UPLOAD")

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
    except Exception as e:
        print(f"Error uploading file: {e}")


def receive_file(client, filename, analyzer):
    """Download file from server"""
    try:
        # Start timing for download
        start_time = analyzer.start_record_time()

        # Send filename
        client.send(filename.encode(FORMAT))

        # Receive response
        response = client.recv(SIZE).decode(FORMAT)

        if response.startswith("ERROR"):
            print(response)
            # Record operation time (failed attempt)
            analyzer.stop_record_time(start_time, bytes_transferred=0, operation="DOWNLOAD_FAIL")
            return

        # Parse file size
        filesize = int(response)

        # Send ready signal
        client.send("READY".encode(FORMAT))

        # Receive file data
        bytes_transferred = 0
        with open(filename, "wb") as f:
            received = 0
            while received < filesize:
                data = client.recv(SIZE)
                if not data:
                    break
                f.write(data)
                received += len(data)
                bytes_transferred += len(data)

        print(f"File '{filename}' downloaded successfully.")

        # Stop timing and record stats
        analyzer.stop_record_time(start_time, bytes_transferred, operation="DOWNLOAD")

    except Exception as e:
        print(f"Error downloading file: {e}")


def authenticate(client, analyzer):
    """Handle client authentication with password hashing and timing"""
    try:
        # NEW: Start timing for system response time (Authentication)
        start_time = analyzer.start_record_time()

        # Receive authentication prompt
        msg = client.recv(SIZE).decode(FORMAT)
        print(msg)

        username = input("Username: ")
        # Use getpass.getpass() for hidden input
        password = getpass.getpass("Password: ") 

        # Hash password before sending
        hashed_password = hash_password(password)

        # Send credentials
        client.send(f"{username}@{hashed_password}".encode(FORMAT))

        # Receive authentication result
        response = client.recv(SIZE).decode(FORMAT)

        # NEW: Record operation time (System Response Time for AUTH)
        analyzer.stop_record_time(start_time, bytes_transferred=0, operation="AUTH")

        if response == "AUTH_SUCCESS":
            print("Authentication successful!")
            return True
        else:
            print("Authentication failed. Invalid credentials.")
            return False
    except Exception as e:
        print(f"Authentication error: {e}")
        return False


def handle_delete(client, filename, analyzer):
    """Handle delete command with timing"""
    start_time = analyzer.start_record_time()

    client.send(f"DELETE@{filename}".encode(FORMAT))

    # Receive response
    response = client.recv(SIZE).decode(FORMAT)
    print(response)

    # Record operation time (no significant bytes transferred)
    analyzer.stop_record_time(start_time, bytes_transferred=0, operation="DELETE")


def handle_dir(client, analyzer):
    """Handle directory listing with timing"""
    start_time = analyzer.start_record_time()

    client.send("DIR".encode(FORMAT))

    # Receive directory listing
    response = client.recv(SIZE).decode(FORMAT)
    print("\n" + response)

    # Record operation time
    analyzer.stop_record_time(start_time, bytes_transferred=len(response.encode(FORMAT)), operation="DIR")


def handle_subfolder(client, action, path, analyzer):
    """Handle subfolder operations with timing"""
    start_time = analyzer.start_record_time()

    client.send(f"SUBFOLDER@{action}@{path}".encode(FORMAT))

    # Receive response
    response = client.recv(SIZE).decode(FORMAT)
    print(response)

    # Record operation time
    analyzer.stop_record_time(start_time, bytes_transferred=0, operation=f"SUBFOLDER_{action}")


def main():
    global IP, ADDR

    # Get IP first and update ADDR
    server_ip = input("Enter Server IP (e.g., 192.168.130.121): ").strip()
    if server_ip:
        IP = server_ip
        ADDR = (IP, PORT)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(10)  # Set 10 second timeout
    network_analyzer = None

    try:
        print(f"Attempting to connect to {IP}:{PORT}...")
        client.connect(ADDR)
        print(f"Connected to server at {IP}:{PORT}")

        # Initialize network analyzer
        network_analyzer = NetworkAnalysis(role="Client", address=f"{IP}:{PORT}")

        # Receive welcome message from server (if any)
        try:
            welcome_msg = client.recv(SIZE).decode(FORMAT)
            if "@" in welcome_msg:
                cmd, msg = welcome_msg.split("@", 1)
                if cmd == "OK":
                    print(f"{msg}")
        except socket.timeout:
            print("Warning: No welcome message received from server")

        # Authenticate
        if not authenticate(client, network_analyzer): # PASS ANALYZER
            client.close()
            return

        while True:
            # Display menu
            print("\n--- File Operations Menu ---")
            print("UPLOAD [filepath] - Upload file to server")
            print("DOWNLOAD [filename] - Download file from server")
            print("DELETE [filename] - Delete file from server")
            print("DIR - List files and directories")
            print("SUBFOLDER CREATE [path] - Create subfolder")
            print("SUBFOLDER DELETE [path] - Delete subfolder")
            print("LOGOUT - Disconnect from server")

            data = input("\n> ").strip()

            if not data:
                continue

            parts = data.split(" ", 1)
            cmd = parts[0].upper()

            if cmd == "UPLOAD":
                if len(parts) < 2:
                    print("Usage: UPLOAD [filepath]")
                    continue

                filepath = parts[1].strip()
                client.send("UPLOAD".encode(FORMAT))

                # Wait for ready signal
                client.recv(SIZE)

                send_file(client, filepath, network_analyzer)

            elif cmd == "DOWNLOAD":
                if len(parts) < 2:
                    print("Usage: DOWNLOAD [filename]")
                    continue

                filename = parts[1].strip()
                client.send("DOWNLOAD".encode(FORMAT))

                # Wait for ready signal
                client.recv(SIZE)

                receive_file(client, filename, network_analyzer)

            elif cmd == "DELETE":
                if len(parts) < 2:
                    print("Usage: DELETE [filename]")
                    continue

                filename = parts[1].strip()
                handle_delete(client, filename, network_analyzer)

            elif cmd == "DIR":
                handle_dir(client, network_analyzer)

            elif cmd == "SUBFOLDER":
                if len(parts) < 2:
                    print("Usage: SUBFOLDER {CREATE|DELETE} [path]")
                    continue

                sub_parts = parts[1].split(" ", 1)
                if len(sub_parts) < 2:
                    print("Usage: SUBFOLDER {CREATE|DELETE} [path]")
                    continue

                action = sub_parts[0].upper()
                path = sub_parts[1].strip()

                if action not in ["CREATE", "DELETE"]:
                    print("Action must be CREATE or DELETE")
                    continue

                handle_subfolder(client, action, path, network_analyzer)

            elif cmd == "LOGOUT":
                client.send("LOGOUT".encode(FORMAT))
                print("Logging out...")
                break
            
            # Allow admin to use the shutdown command
            elif cmd == "SHUTDOWN":
                # The server handle_client checks if the user is 'admin'
                client.send("SHUTDOWN".encode(FORMAT))
                
                # Receive server response
                response = client.recv(SIZE).decode(FORMAT)
                if response.startswith("OK"):
                    print(response.split("@")[1])
                else:
                    print("Shutdown command failed or rejected by server.")
                break # Break loop after sending shutdown

            else:
                print(f"Unknown command: {cmd}")

    except ConnectionRefusedError:
        print(f"Error: Could not connect to server at {IP}:{PORT}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Disconnected from the server.")

        # Save statistics before closing (client stats are saved to network_stats.csv)
        if network_analyzer:
            network_analyzer.save_stats()

        client.close()


if __name__ == "__main__":
    main()
