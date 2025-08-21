# about.py

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

class AboutWindow(tk.Toplevel):
    """
    A standalone Tkinter Toplevel window to display a help/about message.

    This class reads content from a specified text file and displays it
    in a non-editable Text widget with an OK button. It supports
    loading the file from the script's directory or from the sys._MEIPASS
    directory, making it suitable for PyInstaller one-file executables.
    """
    def __init__(self, master, style: ttk.Style, title="About", help_file="help.txt"):
        """
        Initializes the AboutWindow.

        Args:
            master (tk.Tk or tk.Toplevel): The parent window.
            style (ttk.Style): The ttk Style object from the main application to use for theming.
            title (str): The title of the about window.
            help_file (str): The name of the text file to display.
        """
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)

        # --- NEW: Store style and apply background color ---
        self.style = style
        background_color = self.style.lookup(".", "background")
        self.configure(background=background_color)

        # Get the path to the help file, checking for a PyInstaller bundle
        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            
        self.help_file_path = os.path.join(base_dir, help_file)

        self.create_widgets()
        self.load_text_content()

        # Center the window over the master window
        # self.transient(master)
        # self.grab_set()
        # self.wait_window(self)
        
        self.center_on_screen()

    def create_widgets(self):
        """Builds the widgets for the about window."""
        # Frame for the Text widget and scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        # Look up colors from the current theme and provide fallback values
        text_bg = self.style.lookup("TEntry", "fieldbackground") or "#ffffff" # Fallback to white
        text_fg = self.style.lookup("TEntry", "foreground") or "#000000"     # Fallback to black
        insert_color = self.style.lookup("TEntry", "insertcolor") or "#000000" # Fallback to black

        # Use a non-editable Text widget
        self.text_widget = tk.Text(
            text_frame, 
            width=80, 
            height=25, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            background=text_bg,
            foreground=text_fg,
            insertbackground=insert_color, # This now has a guaranteed valid color
            relief="flat",
            borderwidth=1
        )
        scrollbar = ttk.Scrollbar(text_frame, command=self.text_widget.yview)
        self.text_widget['yscrollcommand'] = scrollbar.set
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        # OK button
        ok_button = ttk.Button(self, text="OK", command=self.destroy)
        ok_button.pack(pady=(0, 10))

    def center_on_screen(self):
        """Centers the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f'+{x}+{y}')

    def load_text_content(self):
        """Loads and displays the content of the help file."""
        try:
            with open(self.help_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Enable the widget to insert text, then disable it again
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, content)
            self.text_widget.config(state=tk.DISABLED)
            
        except FileNotFoundError:
            messagebox.showerror("Error", f"Help file not found at: {self.help_file_path}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load help file: {e}")
            self.destroy()
"""
if __name__ == '__main__':
    # This block is for testing the AboutWindow as a standalone program.
    # It will not run when imported into another script.
    
    # You must have a 'help.txt' file in the same directory to test this.
    root = tk.Tk()
    root.title("Main Application")
    root.geometry("200x100")

    # --- NEW: Import theme and setup for testing ---
    try:
        import theme
        style = ttk.Style(root)
        theme.setup_theme(root) # Setup the dark theme
        # To test light theme, comment out the line above and uncomment the line below
        # style.theme_use('clam')
    except ImportError:
        print("theme.py not found, running with default theme.")
        style = ttk.Style(root)

    
    def open_about():
        # --- MODIFIED: Pass the style object ---
        about_window = AboutWindow(root, style, help_file="help.txt")
        about_window.center_on_screen()

    about_button = ttk.Button(root, text="Open About Window", command=open_about)
    about_button.pack(pady=20)
    
    root.mainloop()
"""