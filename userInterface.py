import tkinter as tk
from tkinter import filedialog, ttk, simpledialog, messagebox
import threading
import time

# --- 1. IMPORT THE REAL CLIENT AND CONSTANTS ---
# We import the real FileClient, the default IP/PORT constants, and the FileServer (FS).
from client import FileClient, IP, PORT
from server import FileServer as FS 


# NOTE: The stub FileClient class has been removed and replaced by the actual FileClient imported from client.py.

class FileTransferGUI:
    def __init__(self, window):
        self.window = window
        self.window.title("FloridaPoly File Transfer")
        self.window.geometry("500x250")

        # Application State
        self.role = None  # "SERVER" or "CLIENT"
        self.handler = None # Will hold either FileServer or FileClient instance
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
        self.window.geometry("750x450") # Adjusted size for more buttons
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
                 wraplength=600,
                 anchor="w",
                 justify="left",
                 bg="white",
                 relief="sunken").grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # 2. Buttons Frame (Row 1)
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        buttons_frame.grid_columnconfigure((0, 1, 2, 3), weight=1) # Four columns for buttons

        # Row 0: Upload/Download
        ttk.Button(buttons_frame, text="Select File (Upload)", command=self._select_file).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Upload to Server", command=self._upload_file).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Download File", command=self._download_file).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Delete File", command=self._delete_file).grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Row 1: Utility/Management
        ttk.Button(buttons_frame, text="List Directory (DIR)", command=self._list_directory).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Create Folder", command=lambda: self._subfolder_op("CREATE")).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Delete Folder", command=lambda: self._subfolder_op("DELETE")).grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        ttk.Button(buttons_frame, text="Disconnect/Logout", command=self._stop_handler).grid(row=1, column=3, padx=5, pady=5, sticky="ew")

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
        # --- FIX: Use the imported module-level constants IP and PORT ---
        default_ip = IP
        default_port = PORT
        # ----------------------------------------------------------------

        ip = simpledialog.askstring("Client Setup", "Enter Server IP:", initialvalue=default_ip)
        port = simpledialog.askinteger("Client Setup", "Enter Server Port:", initialvalue=default_port, minvalue=1024,
                                       maxvalue=65535)

        if ip and port:
            # Instantiate the real FileClient
            self.handler = FileClient(ip, port, log_callback=self._log_message)
            self.role = "CLIENT"
            self._create_client_operations_frame()  # Set up UI first

            if self.handler.connect():
                # Prompt for credentials after successful connection
                username = simpledialog.askstring("Authentication", "Enter Username:")
                password = simpledialog.askstring("Authentication", "Enter Password:", show='*')
                
                # Handle the case where the user cancels the auth dialogs
                if not username or not password:
                    self.status_var.set("CLIENT CONNECTED, AUTH CANCELLED")
                    messagebox.showwarning("Authentication Cancelled", "Authentication cancelled by user. Disconnecting.")
                    self._stop_handler()
                    return

                # Authenticate and handle the server's response
                auth_result = self.handler.authenticate(username, password)
                
                if auth_result == "AUTH_SUCCESS":
                    self.status_var.set(f"CLIENT CONNECTED & AUTHENTICATED: User {username}")
                    messagebox.showinfo("Authentication", "Authentication successful!")
                else:
                    self.status_var.set("CLIENT CONNECTED, AUTH FAILED")
                    messagebox.showerror("Authentication Failed", "Invalid credentials or server error. Disconnecting.")
                    self._stop_handler()  # Disconnect if authentication fails
            else:
                self.status_var.set("CONNECTION FAILED")
                messagebox.showerror("Connection Failed", "Could not connect to the server.")
                self._stop_handler()
        else:
            self.handler = None

    # --- Operation Methods ---

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
            
            # --- Handle Overwrite Prompt ---
            # NOTE: The full logic for handling the EXSITS check and prompting for overwrite is complex for a simple thread.
            # We simplify this by letting the user decide if they want to allow overwrite before the transfer starts.
            overwrite = "no"
            if messagebox.askyesno("Overwrite Policy", "Allow file overwrite on the server if it exists?"):
                overwrite = "yes"
            # -------------------------------
            
            # Run file transfer in a thread to keep GUI responsive
            threading.Thread(target=self._run_upload_in_thread, args=(filepath, overwrite)).start()
        else:
            messagebox.showwarning("Upload Error", "Please select a file first.")

    def _run_upload_in_thread(self, filepath, overwrite):
        """Helper to run the upload process and update the GUI afterwards."""
        # The real FileClient.send_file expects the overwrite argument
        result = self.handler.send_file(filepath, overwrite=overwrite)
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
        
    def _delete_file(self):
        """Prompt for filename and call the handler's delete method."""
        if self.role != "CLIENT" or not self.handler or not self.handler.is_authenticated:
            messagebox.showwarning("Error", "Must be connected and authenticated as a Client to delete.")
            return

        filename = simpledialog.askstring("Delete File", "Enter the exact filename (e.g., TS001.txt) to delete:")
        
        if filename and messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{filename}' on the server?"):
            # handle_delete only requires the filename
            threading.Thread(target=self._run_utility_op_in_thread, args=(self.handler.handle_delete, filename, "Delete")).start()
        elif filename:
            messagebox.showinfo("Delete Cancelled", f"Deletion of '{filename}' was cancelled.")

    def _list_directory(self):
        """Call the handler's directory listing method and display results."""
        if self.role != "CLIENT" or not self.handler or not self.handler.is_authenticated:
            messagebox.showwarning("Error", "Must be connected and authenticated as a Client to list directory.")
            return

        # handle_dir takes no arguments, pass None as a placeholder arg
        threading.Thread(target=self._run_utility_op_in_thread, args=(self.handler.handle_dir, None, "DIR")).start()

    def _subfolder_op(self, action):
        """Prompt for folder path and call the handler's subfolder operation method."""
        if self.role != "CLIENT" or not self.handler or not self.handler.is_authenticated:
            messagebox.showwarning("Error", "Must be connected and authenticated as a Client to manage folders.")
            return

        op_name = "Create Folder" if action == "CREATE" else "Delete Folder"
        prompt = "Enter the relative path of the folder to " + action.lower() + " (e.g., Photos/Vacation):"
        path = simpledialog.askstring(op_name, prompt)

        if path:
            if action == "DELETE" and not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the folder '{path}'? It must be empty."):
                return # Cancelled delete

            # handle_subfolder requires action and path
            threading.Thread(target=self._run_utility_op_in_thread, args=(self.handler.handle_subfolder, action, path, op_name)).start()

    def _run_utility_op_in_thread(self, func, *args):
        """Generic helper to run utility operations (Delete, DIR, Folder) and handle the result."""
        
        # The operation name is the last argument passed for messaging
        operation_name = args[-1] if args and isinstance(args[-1], str) else "Operation"
        
        # Execute the function based on its signature
        try:
            if func.__name__ == 'handle_delete':
                 result = func(args[0]) # filename
            elif func.__name__ == 'handle_dir':
                result = func()
            elif func.__name__ == 'handle_subfolder':
                result = func(args[0], args[1]) # action, path
            else:
                result = "ERROR: Invalid utility operation function."
        except Exception as e:
             result = f"ERROR: Threaded operation failed: {e}"


        # Safely update GUI after operation finishes
        self.window.after(0, lambda: self._handle_operation_result(result, operation_name))

    def _handle_operation_result(self, result, operation):
        """Shows the final messagebox based on the operation result."""
        # For DIR command, result is the listing string
        if operation == "DIR":
            messagebox.showinfo(f"Directory Listing", result)
        # For other commands, check for SUCCESS/ERROR prefix
        elif result.startswith("SUCCESS") or result.startswith("File uploaded") or result.startswith("File deleted") or result.startswith("Folder"):
            messagebox.showinfo(f"{operation} Complete", result)
        elif result.startswith("CANCELLED"):
            messagebox.showinfo(f"{operation} Cancelled", result)
        else:
            messagebox.showerror(f"{operation} Failed", result)

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
