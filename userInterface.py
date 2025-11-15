import tkinter as tk
from tkinter import filedialog, ttk, simpledialog, messagebox
import threading
import socket  # Required for client connection constants
import time  # Required for a simple client delay

# Import your refactored server class
from server import FileServer as FS


# --- Placeholder Client Class (Based on client.py structure) ---
# NOTE: This is a placeholder. In a real application, you would put the
# full logic from your client.py file into this class structure.
class FileClient:
    def __init__(self, ip="192.168.130.121", port=4450):
        self.ip = ip
        self.port = port
        self.addr = (ip, port)
        self.socket = None
        self.is_connected = False
        print(f"[Client] Initialized with target server: {ip}:{port}")

    def connect(self):
        """Simulate connecting and authenticating."""
        try:
            # Simulate actual socket connection and authentication
            # In a real scenario, this is where the full client.py logic is called.
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # self.socket.connect(self.addr) # Actual connection
            # self.authenticate(self.socket) # Actual auth

            time.sleep(0.5)  # Simulate connection delay
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[Client] Connection failed: {e}")
            return False

    def disconnect(self):
        """Simulate disconnecting and closing."""
        if self.is_connected:
            # self.socket.send("LOGOUT".encode("utf-8")) # Actual logout
            # self.socket.close() # Actual socket close
            self.is_connected = False
        print("[Client] Disconnected.")

    def send_file(self, filepath):
        """Simulate sending a file."""
        if not self.is_connected:
            return "ERROR: Not connected to server."
        # Call the full send_file logic here
        return f"SUCCESS: Uploaded {filepath} (Simulated)"

    def receive_file(self, filename):
        """Simulate receiving a file."""
        if not self.is_connected:
            return "ERROR: Not connected to server."
        # Call the full receive_file logic here
        return f"SUCCESS: Downloaded {filename} (Simulated)"


class FileTransferGUI:
    def __init__(self, window):
        self.window = window
        self.window.title("FloridaPoly File Transfer")
        self.window.geometry("500x250")

        # Application State
        self.role = None  # "SERVER" or "CLIENT"
        self.handler = None  # Holds either the FS (FileServer) or FileClient instance
        self.server_thread = None  # For running the server in the background

        # Tkinter Variables
        self.file_name_var = tk.StringVar(value="No file selected...")
        self.status_var = tk.StringVar(value="Select a role to begin.")

        self._setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        # Configure grid for the main window
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(self.window)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Start with role selection
        self._create_role_selection_frame()

    # --- Frame Management ---

    def _clear_frame(self):
        """Removes all widgets from the main frame."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def _create_role_selection_frame(self):
        """Initial screen for selecting Server or Client role."""
        self._clear_frame()
        self.window.geometry("300x150")

        frame = ttk.Frame(self.main_frame)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure((0, 1), weight=1)

        ttk.Label(frame, text="Select your role:", font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2,
                                                                                    pady=10)

        ttk.Button(frame, text="Start Server", command=self._start_server).grid(row=1, column=0, padx=5, pady=5,
                                                                                sticky="ew")
        ttk.Button(frame, text="Start Client", command=self._start_client).grid(row=1, column=1, padx=5, pady=5,
                                                                                sticky="ew")

        ttk.Label(self.window, textvariable=self.status_var, relief="sunken", anchor="w").grid(row=1, column=0,
                                                                                               sticky="ew")

    def _create_server_info_frame(self):
        """UI after starting as Server."""
        self._clear_frame()
        self.window.geometry("400x150")
        self.window.title(f"File Server - Running on {self.handler.ip}:{self.handler.port}")
        self.status_var.set(f"SERVER RUNNING: {self.handler.ip}:{self.handler.port}")

        frame = ttk.Frame(self.main_frame)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        ttk.Label(frame, text="SERVER IS ACTIVE", font=('Arial', 14, 'bold'), foreground="green").grid(row=0, column=0,
                                                                                                       pady=10)
        ttk.Label(frame, text=f"Listening on: {self.handler.ip}:{self.handler.port}").grid(row=1, column=0, pady=5)
        ttk.Button(frame, text="Stop Server", command=self._stop_handler).grid(row=2, column=0, pady=10)

    def _create_client_operations_frame(self):
        """UI after starting as Client (Your original UI)."""
        self._clear_frame()
        self.window.geometry("450x200")
        self.window.title("File Client Operations")
        self.status_var.set("CLIENT CONNECTED: Ready for file operations.")

        # Main grid setup for the client view
        self.main_frame.grid_rowconfigure(0, weight=0)  # File Name Frame
        self.main_frame.grid_rowconfigure(1, weight=1)  # Buttons Frame

        # 1. File Name Frame (Row 0)
        file_name_frame = ttk.LabelFrame(self.main_frame, text="Selected File Path")
        file_name_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        file_name_frame.grid_columnconfigure(0, weight=1)

        file_name_label = tk.Label(file_name_frame,
                                   textvariable=self.file_name_var,
                                   wraplength=400,
                                   anchor="w",
                                   justify="left",
                                   bg="white",
                                   relief="sunken")
        file_name_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # 2. Buttons Frame (Row 1)
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        buttons_frame.grid_columnconfigure((0, 1), weight=1)

        # Buttons
        ttk.Button(buttons_frame, text="Select File (Upload)", command=self._select_file).grid(row=0, column=0, padx=5,
                                                                                               pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Upload to Server", command=self._upload_file).grid(row=0, column=1, padx=5,
                                                                                           pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Download File", command=self._download_file).grid(row=1, column=0, padx=5,
                                                                                          pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Disconnect/Logout", command=self._stop_handler).grid(row=1, column=1, padx=5,
                                                                                             pady=5, sticky="ew")

    # --- Role Handler Methods ---

    def _start_server(self):
        """Initializes and starts the FileServer in a background thread."""
        try:
            self.handler = FS()

            # Start the server in a new thread to avoid freezing the GUI
            self.server_thread = threading.Thread(target=self.handler.start, name="ServerThread", daemon=True)
            self.server_thread.start()

            self.role = "SERVER"
            self._create_server_info_frame()
            messagebox.showinfo("Server Started",
                                f"File Server started successfully on {self.handler.ip}:{self.handler.port}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.handler = None

    def _start_client(self):
        """Initializes and attempts to connect the FileClient."""
        ip = simpledialog.askstring("Client Setup", "Enter Server IP:", initialvalue="192.168.130.121")
        port = simpledialog.askinteger("Client Setup", "Enter Server Port:", initialvalue=4450, minvalue=1024,
                                       maxvalue=65535)

        if ip and port:
            self.handler = FileClient(ip, port)

            if self.handler.connect():
                self.role = "CLIENT"
                self._create_client_operations_frame()
                messagebox.showinfo("Client Connected",
                                    f"Successfully connected to {ip}:{port}. Please log in on the console/backend.")
            else:
                messagebox.showerror("Connection Failed",
                                     "Could not connect to the server. Check IP/Port and if the server is running.")
                self.handler = None
        else:
            self.handler = None

    def _stop_handler(self):
        """Stops the currently active handler (Server or Client)."""
        if self.handler:
            if self.role == "SERVER":
                self.handler.stop()
                if self.server_thread and self.server_thread.is_alive():
                    # Wait briefly for the thread to stop, though FS.stop() should handle it.
                    self.server_thread.join(1)
                messagebox.showinfo("Server Stopped", "The File Server has been stopped.")
            elif self.role == "CLIENT":
                self.handler.disconnect()
                messagebox.showinfo("Client Disconnected", "Disconnected from the server.")

        self.role = None
        self.handler = None
        self._create_role_selection_frame()

    # --- Client Operation Methods ---

    def _select_file(self):
        """Open a file dialog and update the file_name_var with the selected path."""
        filepath = filedialog.askopenfilename(
            title="Select File for Upload",
            filetypes=[("All files", "*.*"), ("Text files", "*.txt")]
        )
        if filepath:
            self.file_name_var.set(filepath)
            print(f"Selected file: {filepath}")
        else:
            self.file_name_var.set("No file selected...")

    def _upload_file(self):
        """Call the handler's send_file method."""
        if self.role != "CLIENT" or not self.handler:
            messagebox.showwarning("Error", "Must be connected as a Client to upload.")
            return

        filepath = self.file_name_var.get()
        if filepath and filepath != "No file selected...":
            # NOTE: Upload should also run in a thread for large files in a real app
            result = self.handler.send_file(filepath)
            if "SUCCESS" in result:
                messagebox.showinfo("Upload Complete", result)
            else:
                messagebox.showerror("Upload Failed", result)
        else:
            messagebox.showwarning("Upload Error", "Please select a file first.")

    def _download_file(self):
        """Call the handler's receive_file method."""
        if self.role != "CLIENT" or not self.handler:
            messagebox.showwarning("Error", "Must be connected as a Client to download.")
            return

        download_filename = simpledialog.askstring("Download File", "Enter filename to download from server:")

        if download_filename:
            # NOTE: Download should also run in a thread in a real app
            result = self.handler.receive_file(download_filename)
            if "SUCCESS" in result:
                messagebox.showinfo("Download Complete", result)
            else:
                messagebox.showerror("Download Failed", result)
        else:
            messagebox.showwarning("Download Cancelled", "Download was cancelled.")

    def _on_closing(self):
        """Handles closing the window, ensuring the server is stopped."""
        if self.role == "SERVER":
            self._stop_handler()
        self.window.destroy()


# --- Main execution block for testing the GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FileTransferGUI(root)
    root.mainloop()