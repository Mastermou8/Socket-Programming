import tkinter as tk
from tkinter import filedialog, ttk, simpledialog, messagebox
import threading
import socket  # Required for client connection constants
import time

from server import FileServer as FS


# --- Refactored FileClient Class (Stub for GUI) ---
# This class acts as the interface between the GUI and the actual client logic.
# It now supports logging and authentication as expected by the GUI flow.
class FileClient:
    def __init__(self, ip="192.168.130.121", port=4450, log_callback=None):
        self.ip = ip
        self.port = port
        self.addr = (ip, port)
        self.client_socket = None
        self.is_connected = False
        self.is_authenticated = False
        self.username = None
        self.log_callback = log_callback  # The function passed by the GUI

        self._log(f"Initialized with target server: {ip}:{port}")

    def _log(self, message):
        """Internal logging method."""
        if self.log_callback:
            self.log_callback(f"[CLIENT] {message}")
        else:
            print(f"[CLIENT] {message}")

    def connect(self):
        """Simulates/Attempts physical connection to the server."""
        try:
            # NOTE: In a real app, this would use self.client_socket.connect(self.addr)
            # For now, simulate a successful connection
            time.sleep(0.5)
            self.is_connected = True
            self._log("Connection successful.")
            return True
        except Exception as e:
            self._log(f"Connection failed: {e}")
            self.is_connected = False
            return False

    def authenticate(self, username, password):
        """Simulates/Attempts user authentication."""
        if not self.is_connected:
            self._log("Authentication failed: Not connected.")
            return False

        # NOTE: In a real app, this would send credentials and wait for AUTH_SUCCESS/AUTH_FAILED
        if username and password:
            self.is_authenticated = True
            self.username = username
            self._log(f"Authentication successful for user: {username}.")
            return True
        else:
            self._log("Authentication failed: Invalid credentials provided.")
            return False

    def disconnect(self):
        """Simulates logging out and closing the socket."""
        if self.is_connected:
            # self.client_socket.send("LOGOUT".encode("utf-8")) # Actual logout
            # self.client_socket.close() # Actual socket close
            self.is_authenticated = False
            self.is_connected = False
            self.username = None
        self._log("Disconnected.")

    def send_file(self, filepath):
        """Simulate sending a file."""
        if not self.is_authenticated:
            self._log("Upload failed: Not authenticated.")
            return "ERROR: Not authenticated."
        self._log(f"Simulating upload of: {filepath}")
        time.sleep(1)  # Simulate transfer time
        return f"SUCCESS: Uploaded {filepath} (Simulated)"

    def receive_file(self, filename):
        """Simulate receiving a file."""
        if not self.is_authenticated:
            self._log("Download failed: Not authenticated.")
            return "ERROR: Not authenticated."
        self._log(f"Simulating download of: {filename}")
        time.sleep(1)  # Simulate transfer time
        return f"SUCCESS: Downloaded {filename} (Simulated)"


class FileTransferGUI:
    def __init__(self, window):
        self.window = window
        self.window.title("FloridaPoly File Transfer")
        self.window.geometry("500x250")

        # Application State
        self.role = None  # "SERVER" or "CLIENT"
        self.handler = None
        self.server_thread = None

        # UI Component references for logging
        self.server_log_text = None
        self.client_log_text = None

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
        """UI after starting as Server, now including the log."""
        self._clear_frame()
        self.window.geometry("600x400")  # Increase size for log
        self.window.title(f"File Server - Running on {self.handler.ip}:{self.handler.port}")
        self.status_var.set(f"SERVER RUNNING: {self.handler.ip}:{self.handler.port}")

        # Configure the frame grid to accommodate the log
        self.main_frame.grid_rowconfigure(0, weight=0)  # Info row
        self.main_frame.grid_rowconfigure(1, weight=1)  # Log row
        self.main_frame.grid_rowconfigure(2, weight=0)  # Stop button row

        # 1. Info Label Frame (Top)
        info_frame = ttk.Frame(self.main_frame)
        info_frame.grid(row=0, column=0, pady=5, sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(info_frame, text="SERVER IS ACTIVE", font=('Arial', 14, 'bold'), foreground="green").pack(
            side=tk.LEFT, padx=10)
        ttk.Label(info_frame, text=f"Listening on: {self.handler.ip}:{self.handler.port}").pack(side=tk.LEFT, padx=20)

        # 2. Server Log Frame (Center, takes up most space)
        log_frame = ttk.LabelFrame(self.main_frame, text="Server Activity Log")
        log_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        # Text widget for logging
        self.server_log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, bg="black", fg="lime green",
                                       font=("Consolas", 9))
        self.server_log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Scrollbar
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.server_log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky='ns')
        self.server_log_text['yscrollcommand'] = log_scrollbar.set

        # 3. Stop Button (Bottom)
        ttk.Button(self.main_frame, text="Stop Server", command=self._stop_handler).grid(row=2, column=0, pady=10)

    def _create_client_operations_frame(self):
        """UI after starting as Client, now including the log."""
        self._clear_frame()
        self.window.geometry("600x400") # Match server size
        self.window.title(f"File Client Operations - Connected to {self.handler.ip}:{self.handler.port}")
        self.status_var.set("CLIENT CONNECTED: Ready for file operations.")

        # Main grid setup for the client view
        self.main_frame.grid_rowconfigure(0, weight=0)  # File Name Frame
        self.main_frame.grid_rowconfigure(1, weight=0)  # Buttons Frame
        self.main_frame.grid_rowconfigure(2, weight=1)  # Log Frame

        # 1. File Name Frame (Row 0)
        file_name_frame = ttk.LabelFrame(self.main_frame, text="Selected File Path")
        file_name_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        file_name_frame.grid_columnconfigure(0, weight=1)

        tk.Label(file_name_frame,
                 textvariable=self.file_name_var,
                 wraplength=400,
                 anchor="w",
                 justify="left",
                 bg="white",
                 relief="sunken").grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # 2. Buttons Frame (Row 1)
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        buttons_frame.grid_columnconfigure((0, 1), weight=1)

        ttk.Button(buttons_frame, text="Select File (Upload)", command=self._select_file).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Upload to Server", command=self._upload_file).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Download File", command=self._download_file).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Disconnect/Logout", command=self._stop_handler).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # 3. Client Log Frame (Row 2, takes up most space)
        log_frame = ttk.LabelFrame(self.main_frame, text="Client Activity Log")
        log_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        # Text widget for logging
        self.client_log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, bg="#F0F0F0", fg="#333333", font=("Arial", 9))
        self.client_log_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Scrollbar
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.client_log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky='ns')
        self.client_log_text['yscrollcommand'] = log_scrollbar.set

    # --- Role Handler Methods ---

    def _start_server(self):
        """Initializes and starts the FileServer in a background thread."""
        try:
            # Pass the centralized logging callback to the FileServer
            self.handler = FS(log_callback=self._log_message)

            self.role = "SERVER"
            self._create_server_info_frame()  # Set up UI before starting thread

            # Start the server in a new thread
            self.server_thread = threading.Thread(target=self.handler.start, name="ServerThread", daemon=True)
            self.server_thread.start()

            messagebox.showinfo("Server Started",
                                f"File Server started successfully on {self.handler.ip}:{self.handler.port}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
            self.handler = None

    def _start_client(self):
        """Initializes, connects, and authenticates the FileClient."""
        ip = simpledialog.askstring("Client Setup", "Enter Server IP:", initialvalue="192.168.130.121")
        port = simpledialog.askinteger("Client Setup", "Enter Server Port:", initialvalue=4450, minvalue=1024,
                                       maxvalue=65535)

        if ip and port:
            # Pass the centralized logging callback to the FileClient
            self.handler = FileClient(ip, port, log_callback=self._log_message)
            self.role = "CLIENT"
            self._create_client_operations_frame()  # Set up UI first

            if self.handler.connect():
                # Prompt for credentials after successful connection
                username = simpledialog.askstring("Authentication", "Enter Username:")
                password = simpledialog.askstring("Authentication", "Enter Password:", show='*')

                if self.handler.authenticate(username, password):
                    self.status_var.set(f"CLIENT CONNECTED & AUTHENTICATED: User {username}")
                    messagebox.showinfo("Authentication", "Authentication successful!")
                else:
                    self.status_var.set("CLIENT CONNECTED, AUTH FAILED")
                    messagebox.showerror("Authentication Failed", "Invalid credentials. Disconnecting.")
                    self._stop_handler()  # Disconnect if authentication fails
            else:
                self.status_var.set("CONNECTION FAILED")
                messagebox.showerror("Connection Failed", "Could not connect to the server.")
                self._stop_handler()
        else:
            self.handler = None

    # ... (_stop_handler, _select_file, _upload_file, _download_file, and _on_closing remain the same, but _log calls are now _log_message) ...

    def _stop_handler(self):
        """Stops the currently active handler (Server or Client)."""
        if self.handler:
            if self.role == "SERVER":
                self.handler.stop()
                if self.server_thread and self.server_thread.is_alive():
                    self.server_thread.join(1)
                messagebox.showinfo("Server Stopped", "The File Server has been stopped.")
            elif self.role == "CLIENT":
                self.handler.disconnect()
                messagebox.showinfo("Client Disconnected", "Disconnected from the server.")

        self.role = None
        self.handler = None
        self.server_log_text = None  # Clear references
        self.client_log_text = None  # Clear references
        self._create_role_selection_frame()

    def _select_file(self):
        """Open a file dialog and update the file_name_var with the selected path."""
        filepath = filedialog.askopenfilename(
            title="Select File for Upload",
            filetypes=[("All files", "*.*"), ("Text files", "*.txt")]
        )
        if filepath:
            self.file_name_var.set(filepath)
            self._log_message(f"Selected file: {filepath}")
        else:
            self.file_name_var.set("No file selected...")

    def _upload_file(self):
        """Call the handler's send_file method."""
        if self.role != "CLIENT" or not self.handler or not self.handler.is_authenticated:
            messagebox.showwarning("Error", "Must be connected and authenticated as a Client to upload.")
            return

        filepath = self.file_name_var.get()
        if filepath and filepath != "No file selected...":
            # Run file transfer in a thread to keep GUI responsive
            threading.Thread(target=self._run_upload_in_thread, args=(filepath,)).start()
        else:
            messagebox.showwarning("Upload Error", "Please select a file first.")

    def _run_upload_in_thread(self, filepath):
        """Helper to run the upload process and update the GUI afterwards."""
        result = self.handler.send_file(filepath)
        # Safely update GUI after operation finishes
        self.window.after(0, lambda: self._handle_operation_result(result, "Upload"))

    def _download_file(self):
        """Call the handler's receive_file method."""
        if self.role != "CLIENT" or not self.handler or not self.handler.is_authenticated:
            messagebox.showwarning("Error", "Must be connected and authenticated as a Client to download.")
            return

        download_filename = simpledialog.askstring("Download File", "Enter filename to download from server:")

        if download_filename:
            # Run file transfer in a thread to keep GUI responsive
            threading.Thread(target=self._run_download_in_thread, args=(download_filename,)).start()
        else:
            messagebox.showwarning("Download Cancelled", "Download was cancelled.")

    def _run_download_in_thread(self, filename):
        """Helper to run the download process and update the GUI afterwards."""
        result = self.handler.receive_file(filename)
        # Safely update GUI after operation finishes
        self.window.after(0, lambda: self._handle_operation_result(result, "Download"))

    def _handle_operation_result(self, result, operation):
        """Shows the final messagebox based on the operation result."""
        if "SUCCESS" in result:
            messagebox.showinfo(f"{operation} Complete", result)
        else:
            messagebox.showerror(f"{operation} Failed", result)

    def _log(self, message):
        """Internal logging method that calls the GUI callback or prints."""
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        full_message = f"{timestamp} {message}"

        if self.log_callback:
            # Send the message to the GUI's log widget
            self.log_callback(full_message)
        else:
            print(full_message)

    def _log_message(self, message):
        """Internal logger that routes the message to the correct log window."""
        # Use window.after to safely schedule the update on the main GUI thread
        self.window.after(0, lambda: self._append_to_log(message))

    def _append_to_log(self, message):
        """Appends the message to the active log Text widget."""
        log_widget = None

        if self.role == "SERVER" and self.server_log_text:
            log_widget = self.server_log_text
        elif self.role == "CLIENT" and self.client_log_text:
            log_widget = self.client_log_text

        if log_widget:
            log_widget.config(state=tk.NORMAL)
            log_widget.insert(tk.END, message + "\n")
            log_widget.see(tk.END)
            log_widget.config(state=tk.DISABLED)
        else:
            # Fallback for messages before a role is selected
            print(message)

    def _on_closing(self):
        """Handles closing the window, ensuring the server is stopped."""
        if self.role == "SERVER":
            self._stop_handler()
        elif self.role == "CLIENT":
            self._stop_handler()

        self.window.destroy()



# --- Main execution block for testing the GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FileTransferGUI(root)
    root.mainloop()