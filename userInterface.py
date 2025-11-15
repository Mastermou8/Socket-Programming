import tkinter as tk
from tkinter import filedialog, ttk


class userInterface_server:
    def __init__(self, window):
        self.window = window
        self.window.title("FloridaPoly Server Storage")
        self.window.geometry("450x200")  # Adjust size for better fit

        # Initialize Tkinter variables
        self.file_name_var = tk.StringVar(value="No file selected...")

        # NOTE: In a complete application, you would pass a Server/Client
        # handler object here (e.g., self.handler = handler) to call
        # the real upload/download logic.

        self._setup_ui()

    def _setup_ui(self):
        # Configure grid for the main window
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=0)  # File Name Frame
        self.window.grid_rowconfigure(1, weight=1)  # Buttons Frame

        self._create_file_name_frame()
        self._create_buttons_frame()

    def _create_file_name_frame(self):
        window = self.window
        # Create a LabelFrame for the file name
        file_name_frame = ttk.LabelFrame(window, text="Selected File")
        # Use sticky="ew" to make it span the width
        file_name_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Configure grid for the label frame to make the label fill it
        file_name_frame.grid_columnconfigure(0, weight=1)

        # Add a label inside the frame to display the file name
        file_name_label = tk.Label(file_name_frame,
                                   textvariable=self.file_name_var,
                                   wraplength=400,
                                   anchor="w",
                                   justify="left",
                                   bg="white",  # Add background for visibility
                                   relief="sunken")  # Add relief for visual effect
        file_name_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

    def _create_buttons_frame(self):
        # Frame to hold the main operation buttons
        buttons_frame = ttk.Frame(self.window)
        buttons_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # Configure grid for the buttons frame (2 columns for buttons)
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        # 1. Select File Button (for Upload)
        select_button = ttk.Button(buttons_frame, text="Select File (Upload)", command=self._select_file)
        select_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # 2. Upload Button
        upload_button = ttk.Button(buttons_frame, text="Upload to Server", command=self._upload_file)
        upload_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 3. Download Button
        download_button = ttk.Button(buttons_frame, text="Download File", command=self._download_file)
        # Span the download button across both columns
        download_button.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

    # --- Handler Methods ---

    def _select_file(self):
        """Open a file dialog and update the file_name_var with the selected path."""
        # Open file dialog to choose a file for upload
        filepath = filedialog.askopenfilename(
            title="Select File for Upload",
            # Optional: restrict file types
            filetypes=[("All files", "*.*"), ("Text files", "*.txt")]
        )
        if filepath:
            self.file_name_var.set(filepath)
            print(f"Selected file: {filepath}")
        else:
            self.file_name_var.set("No file selected...")

    def _upload_file(self):
        """Placeholder for initiating file upload."""
        filepath = self.file_name_var.get()
        if filepath and filepath != "No file selected...":
            print(f"--- Initiating Upload for: {filepath} ---")
            # In a real app, call the client.py upload logic here
            # e.g., self.handler.send_file(filepath)
            tk.messagebox.showinfo("Upload", f"Simulating upload of: {filepath}")
        else:
            tk.messagebox.showwarning("Upload Error", "Please select a file first.")

    def _download_file(self):
        """Placeholder for initiating file download."""
        # In a real app, you would prompt for the filename to download
        # or list files in a separate widget.
        download_filename = tk.simpledialog.askstring("Download File", "Enter filename to download from server:")

        if download_filename:
            print(f"--- Initiating Download for: {download_filename} ---")
            # In a real app, call the client.py download logic here
            # e.g., self.handler.receive_file(download_filename)
            tk.messagebox.showinfo("Download", f"Simulating download of: {download_filename}")
        else:
            tk.messagebox.showwarning("Download Cancelled", "Download was cancelled.")


# --- Main execution block for testing the GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    app = userInterface_server(root)
    root.mainloop()