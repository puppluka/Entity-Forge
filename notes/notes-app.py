#!/usr/bin/env python3

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

class Notepad:
    def __init__(self, root):
        """
        Initialize the Notepad application.
        Args:
            root (tk.Tk): The main window of the application.
        """
        self.root = root
        self.root.title("Untitled - Imhotep")
        
        # --- Variables ---
        self.current_file_path = None # To store the path of the currently open file

        # --- Text Area ---
        # Using scrolledtext for automatic scrollbars
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, undo=True)
        self.text_area.pack(expand=True, fill='both')
        self.text_area.focus_set() # Set focus to the text area

        # --- Menu Bar ---
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # --- File Menu ---
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0) # tearoff=0 removes the dashed line
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        self.file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        self.file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        self.file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_as_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.exit_application)

        # --- Edit Menu ---
        self.edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.text_area.edit_undo)
        self.edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.text_area.edit_redo)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=self.cut_text)
        self.edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self.copy_text)
        self.edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=self.paste_text)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self.select_all_text)
        self.edit_menu.add_command(label="Clear All", command=self.clear_all_text)


        # --- Help Menu ---
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="About Imhotep", command=self.show_about)

        # --- Keyboard Shortcuts ---
        self.root.bind_all("<Control-n>", lambda event: self.new_file())
        self.root.bind_all("<Control-o>", lambda event: self.open_file())
        self.root.bind_all("<Control-s>", lambda event: self.save_file())
        self.root.bind_all("<Control-Shift-S>", lambda event: self.save_as_file()) # Note: Shift needs to be explicit
        # Ctrl+X, C, V, A, Z, Y are often handled by the ScrolledText widget itself,
        # but we can bind them explicitly if needed or for consistency.
        # self.root.bind_all("<Control-x>", lambda event: self.cut_text()) # Already handled by widget
        # self.root.bind_all("<Control-c>", lambda event: self.copy_text()) # Already handled by widget
        # self.root.bind_all("<Control-v>", lambda event: self.paste_text()) # Already handled by widget
        # self.root.bind_all("<Control-a>", lambda event: self.select_all_text()) # Already handled by widget

        # --- Protocol for window close button ---
        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)
        
        # --- Status Bar (Optional) ---
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_area.bind("<<Modified>>", self.on_text_change) # Track modifications

    def on_text_change(self, event=None):
        """Updates the window title if the text has been modified."""
        if self.text_area.edit_modified():
            title = self.root.title()
            if not title.startswith("*"):
                self.root.title("*" + title)
        # Reset the modified flag after checking so it can track new modifications
        # self.text_area.edit_modified(False) # Be careful with this, might interfere with undo/redo

    def update_title(self, filepath=None):
        """Updates the window title with the current file name."""
        if filepath:
            filename = filepath.split('/')[-1] # Get filename from path
            self.root.title(f"{filename} - Imhotep")
        else:
            self.root.title("Untitled - Imhotep")
        self.text_area.edit_modified(False) # Mark as unmodified after save/open/new

    def new_file(self):
        """Clears the text area for a new file."""
        if self.text_area.edit_modified():
            if not messagebox.askyesno("Save changes?", "Do you want to save changes before creating a new file?"):
                self.text_area.delete(1.0, tk.END)
                self.current_file_path = None
                self.update_title()
                self.status_bar.config(text="New file created.")
                return
            else:
                if not self.save_file(): # If save is cancelled, don't proceed with new file
                    return

        self.text_area.delete(1.0, tk.END)
        self.current_file_path = None
        self.update_title()
        self.status_bar.config(text="New file created.")


    def open_file(self):
        """Opens a file and loads its content into the text area."""
        if self.text_area.edit_modified():
            if not messagebox.askyesno("Save changes?", "Do you want to save changes before opening a new file?"):
                pass # Continue without saving
            else:
                if not self.save_file(): # If save is cancelled, don't proceed
                    return

        filepath = filedialog.askopenfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, "r", encoding='utf-8') as file:
                    content = file.read()
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, content)
                self.current_file_path = filepath
                self.update_title(filepath)
                self.status_bar.config(text=f"Opened: {filepath}")
            except Exception as e:
                messagebox.showerror("Error Opening File", f"Could not open file: {e}")
                self.status_bar.config(text=f"Error opening file: {filepath}")


    def save_file(self):
        """Saves the current content to the current file path, or asks for a path if new."""
        if self.current_file_path:
            try:
                content = self.text_area.get(1.0, tk.END)
                # Tkinter text widget adds a newline at the end, remove if it's the only content or unwanted
                if content.endswith('\n') and content.count('\n') == content.count(1.0, tk.END + "-1c"):
                     content = content.rstrip('\n')

                with open(self.current_file_path, "w", encoding='utf-8') as file:
                    file.write(content)
                self.update_title(self.current_file_path)
                self.status_bar.config(text=f"Saved: {self.current_file_path}")
                return True # Indicate save was successful
            except Exception as e:
                messagebox.showerror("Error Saving File", f"Could not save file: {e}")
                self.status_bar.config(text=f"Error saving file: {self.current_file_path}")
                return False # Indicate save failed
        else:
            return self.save_as_file() # If no current path, use save_as logic

    def save_as_file(self):
        """Saves the current content to a new file path chosen by the user."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("Python Files", "*.py"), ("All Files", "*.*")],
            initialfile="Untitled.txt" # Suggest a default filename
        )
        if filepath:
            try:
                content = self.text_area.get(1.0, tk.END)
                # Tkinter text widget might add an extra newline at the very end.
                # Only remove it if it's the *very last* character and seems unintentional.
                if content.endswith('\n') and len(content) > 1: # Check if it's not just a single newline
                    # A more robust check might be needed depending on desired behavior for files ending with newlines
                    pass # For now, let's keep it simple and save as is.
                         # Or: content = content.rstrip('\n') if you always want to strip trailing newlines.

                with open(filepath, "w", encoding='utf-8') as file:
                    file.write(content)
                self.current_file_path = filepath
                self.update_title(filepath)
                self.status_bar.config(text=f"Saved as: {filepath}")
                return True # Indicate save was successful
            except Exception as e:
                messagebox.showerror("Error Saving File", f"Could not save file: {e}")
                self.status_bar.config(text=f"Error saving file as: {filepath}")
                return False # Indicate save failed
        return False # User cancelled save dialog

    def exit_application(self):
        """Exits the application, prompting to save if there are unsaved changes."""
        if self.text_area.edit_modified(): # Check if text area has been modified
            response = messagebox.askyesnocancel("Quit", "Do you want to save changes before quitting?")
            if response is True: # Yes
                if not self.save_file():
                    return # Don't quit if save was cancelled
            elif response is None: # Cancel
                return # Don't quit
        self.root.destroy()

    # --- Edit Menu Functions ---
    def cut_text(self):
        """Cuts the selected text."""
        # The ScrolledText widget handles Ctrl+X, but this provides a menu option.
        # It uses the clipboard_clear and clipboard_append methods of the widget.
        try:
            if self.text_area.tag_ranges(tk.SEL): # Check if text is selected
                self.text_area.event_generate("<<Cut>>")
                self.status_bar.config(text="Text cut.")
                self.on_text_change() # Update modified status
        except tk.TclError:
            self.status_bar.config(text="Nothing selected to cut.")


    def copy_text(self):
        """Copies the selected text."""
        try:
            if self.text_area.tag_ranges(tk.SEL):
                self.text_area.event_generate("<<Copy>>")
                self.status_bar.config(text="Text copied.")
        except tk.TclError:
            self.status_bar.config(text="Nothing selected to copy.")

    def paste_text(self):
        """Pastes text from the clipboard."""
        try:
            self.text_area.event_generate("<<Paste>>")
            self.status_bar.config(text="Text pasted.")
            self.on_text_change() # Update modified status
        except tk.TclError:
            # This might happen if clipboard is empty or contains non-text data
            self.status_bar.config(text="Clipboard is empty or contains unsupported data.")


    def select_all_text(self):
        """Selects all text in the text area."""
        self.text_area.tag_add(tk.SEL, "1.0", tk.END)
        self.text_area.mark_set(tk.INSERT, "1.0") # Move cursor to beginning
        self.text_area.see(tk.INSERT) # Scroll to cursor
        self.status_bar.config(text="All text selected.")
        return "break" # Prevents default binding from firing as well, if any

    def clear_all_text(self):
        """Clears all text in the text area after confirmation."""
        if messagebox.askyesno("Clear All", "Are you sure you want to clear all text? This cannot be undone easily if not saved."):
            self.text_area.delete(1.0, tk.END)
            self.status_bar.config(text="All text cleared.")
            self.on_text_change() # Update modified status


    # --- Help Menu Functions ---
    def show_about(self):
        """Shows the about dialog."""
        messagebox.showinfo(
            "About Imhotep",
            "Imhotep Notes Application\nVersion 1.0\n\nWith Love, by Pup Luka."
        )

if __name__ == "__main__":
    main_window = tk.Tk()
    app = Notepad(main_window)
    main_window.geometry("800x600") # Set a default size
    main_window.mainloop()
