# fgd_gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import re
import traceback

# Import the core logic modules
from fgd_parser import FGDParser
from fgd_model import (
    FGDFile, EntityClass, KeyvalueProperty, ChoicesProperty, FlagsProperty,
    IO, ChoiceItem, FlagItem, IncludeDirective, Property, FGDElement, MapSize,
    Version, AutoVisGroup, MaterialExclusion
)
from fgd_serializer import FGDSerializer
from about import AboutWindow
# --- NEW: Import the theme module ---
import theme

class FGDApplication(tk.Tk):
    """Main Tkinter application class for the FGD Editor GUI."""
    def __init__(self):
        super().__init__()
        self.title("Entity Forge - FGD Editor")
        self.geometry("1200x800")

        # --- NEW: Initialize the style object early ---
        self.style = ttk.Style(self)

        self.fgd_file: FGDFile | None = None
        self.current_fgd_path: str | None = None
        self.selected_element: FGDElement | None = None
        self.properties_frame_inner_id = None

        self.parser = FGDParser()
        self.serializer = FGDSerializer()

        # --- NEW: Initialize the theme before creating widgets ---
        theme.setup_theme(self)

        self._create_widgets()
        self._setup_menu()

        # --- NEW: Apply theme to menus after they are created ---
        theme.switch_theme(self, dark_mode=True)

    def _create_widgets(self):
        self.main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill="both", expand=True)

        self.elements_frame = ttk.Frame(self.main_pane, width=300, relief=tk.RIDGE, borderwidth=2)
        self.main_pane.add(self.elements_frame, weight=1)

        ttk.Label(self.elements_frame, text="FGD Elements:").pack(padx=5, pady=5, anchor="w")

        list_frame = ttk.Frame(self.elements_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self.elements_list = ttk.Treeview(list_frame, columns=("Type",), show="tree headings")
        self.elements_list.heading("#0", text="Name", anchor="w")
        self.elements_list.column("#0", width=200, minwidth=150, stretch=tk.YES)
        self.elements_list.heading("Type", text="Type", anchor="w")
        self.elements_list.column("Type", width=100, minwidth=80, stretch=tk.YES)

        self.elements_list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.elements_list.yview)
        self.elements_list.configure(yscrollcommand=self.elements_list_scrollbar.set)

        self.elements_list_scrollbar.pack(side="right", fill="y")
        self.elements_list.pack(side="left", fill="both", expand=True)
        self.elements_list.bind("<<TreeviewSelect>>", self._on_element_select)

        button_frame = ttk.Frame(self.elements_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        new_button = ttk.Button(button_frame, text="New Class", command=self._add_new_element)
        new_button.pack(side="left", fill="x", expand=True, padx=(0, 2))

        delete_button = ttk.Button(button_frame, text="Delete Selected", command=self._delete_selected_element)
        delete_button.pack(side="right", fill="x", expand=True, padx=(2, 0))

        self.properties_frame = ttk.Frame(self.main_pane, relief=tk.RIDGE, borderwidth=2)
        self.main_pane.add(self.properties_frame, weight=3)
        self._create_properties_and_io_frame()

    def _create_properties_and_io_frame(self):
        self.properties_canvas = tk.Canvas(self.properties_frame, bd=0, highlightthickness=0)
        self.properties_scrollbar = ttk.Scrollbar(self.properties_frame, orient="vertical", command=self.properties_canvas.yview)
        self.properties_canvas.configure(yscrollcommand=self.properties_scrollbar.set)

        self.properties_canvas.pack(side="left", fill="both", expand=True)
        self.properties_scrollbar.pack(side="right", fill="y")

        self.properties_frame_inner = ttk.Frame(self.properties_canvas)
        self.properties_frame_inner_id = self.properties_canvas.create_window((0, 0), window=self.properties_frame_inner, anchor="nw")

        self.properties_frame_inner.bind("<Configure>", lambda e: self.properties_canvas.configure(scrollregion=self.properties_canvas.bbox("all")))
        self.properties_canvas.bind('<Configure>', lambda e: self.properties_canvas.itemconfig(self.properties_frame_inner_id, width=e.width))

    def _setup_menu(self):
        self.menubar = tk.Menu(self, tearoff=0)
        self.config(menu=self.menubar)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self._new_fgd_file)
        file_menu.add_separator()
        file_menu.add_command(label="Open", command=self._open_fgd_file)
        file_menu.add_command(label="Save", command=self._save_fgd_file)
        file_menu.add_command(label="Save As...", command=self._save_fgd_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        # --- NEW: Theme menu and commands ---
        theme_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Dark", command=lambda: self._switch_theme(dark_mode=True))
        theme_menu.add_command(label="Light", command=lambda: self._switch_theme(dark_mode=False))

        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_window)

    def _new_fgd_file(self):
        self.fgd_file = FGDFile()
        self.current_fgd_path = None
        self.title("FGD Editor - New File*")
        self._update_elements_list()
        self._clear_properties_frame()
        messagebox.showinfo("New File", "Created a new, empty FGD file.")

    def _add_new_element(self):
        if not self.fgd_file:
            messagebox.showwarning("No FGD Loaded", "Please open or create a new FGD file first.")
            return

        name = simpledialog.askstring("New Class", "Enter the new class name:")
        if not name:
            return
        if name in self.fgd_file.class_map:
            messagebox.showerror("Error", f"A class named '{name}' already exists.")
            return

        class_type = simpledialog.askstring("New Class", "Enter class type (e.g., PointClass, SolidClass):", initialvalue="PointClass")
        if not class_type:
            return

        new_element = EntityClass(class_type=class_type, name=name, description="A new entity class.")
        self.fgd_file.add_element(new_element)
        self._update_elements_list()

    def _delete_selected_element(self):
        selected_ids = self.elements_list.selection()
        if not selected_ids:
            messagebox.showwarning("No Selection", "Please select an element to delete.")
            return

        selected_name = self.elements_list.item(selected_ids[0], "text")

        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{selected_name}'?"):
            return

        element_to_delete = next((el for el in self.fgd_file.elements if hasattr(el, 'name') and el.name == selected_name), None)
        
        if element_to_delete:
            self.fgd_file.elements.remove(element_to_delete)
            if isinstance(element_to_delete, EntityClass):
                if element_to_delete.name in self.fgd_file.class_map:
                    del self.fgd_file.class_map[element_to_delete.name]
                if element_to_delete.class_type == "BaseClass" and element_to_delete.name in self.fgd_file.base_classes:
                    del self.fgd_file.base_classes[element_to_delete.name]

            self._update_elements_list()
            self._clear_properties_frame()

    def _open_fgd_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("FGD Files", "*.fgd"), ("All Files", "*.*")])
        if filepath:
            try:
                self.parser = FGDParser()
                self.fgd_file = self.parser.parse_fgd_file(filepath)
                self.current_fgd_path = filepath
                self.title(f"FGD Editor - {os.path.basename(filepath)}")
                self._update_elements_list()
                self._clear_properties_frame()
                messagebox.showinfo("Load Successful", f"'{os.path.basename(filepath)}' loaded.")
            except Exception as e:
                traceback.print_exc() # Print full traceback to terminal
                messagebox.showerror("Load Error", f"Failed to load FGD file: {e}")
                self.fgd_file = None
                self.current_fgd_path = None
                self.title("FGD Editor")
                self._update_elements_list()
                self._clear_properties_frame()

    def _save_fgd_file(self):
        if not self.current_fgd_path:
            self._save_fgd_file_as()
            return
        self._perform_save(self.current_fgd_path)

    def _save_fgd_file_as(self):
        if not self.fgd_file:
            messagebox.showwarning("No Data", "No FGD data to save.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".fgd", filetypes=[("FGD Files", "*.fgd")])
        if filepath:
            self._perform_save(filepath)

    def _perform_save(self, filepath):
        if not self.fgd_file:
            messagebox.showwarning("No Data", "No FGD data to save.")
            return
        try:
            # Ensure any focused widget updates its bound variable before saving
            focused_widget = self.focus_get()
            if focused_widget:
                focused_widget.event_generate("<FocusOut>")
                self.update_idletasks()

            serialized_content = self.serializer.serialize_fgd(self.fgd_file)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(serialized_content)
            self.current_fgd_path = filepath
            self.title(f"FGD Editor - {os.path.basename(filepath)}")
            messagebox.showinfo("Save Successful", f"File saved to {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save file: {e}")

    def _update_elements_list(self):
        for iid in self.elements_list.get_children():
            self.elements_list.delete(iid)
        if self.fgd_file:
            for element in self.fgd_file.elements:
                try:
                    iid = str(element.name)
                    self.elements_list.insert("", "end", iid=iid, text=str(element.name), values=(element.class_type,))
                except tk.TclError as e:
                    print(f"Error adding element to Treeview: {e}")
                    print(f"Duplicate element name: '{element.name}', type: '{element.class_type}'")
                    messagebox.showerror("GUI Error", f"Failed to display FGD elements. Duplicate element name found: '{element.name}'. Check terminal for details.")
                    return

    def _on_element_select(self, event):
        selected_ids = self.elements_list.selection()
        if selected_ids:
            selected_name = self.elements_list.item(selected_ids[0], "text")
            if self.fgd_file:
                element = next((el for el in self.fgd_file.elements if el.name == selected_name), None)
                self._display_element_details(element)
        else:
            self._clear_properties_frame()

    def _clear_properties_frame(self):
        for widget in self.properties_frame_inner.winfo_children():
            widget.destroy()
        # --- NEW: Ensure canvas is correctly colored after clearing ---
        canvas_bg = self.style.lookup("TFrame", "background")
        self.properties_canvas.config(bg=canvas_bg)

    # --- NEW: Helper function to safely get theme colors ---
    def _get_style_color(self, style_name, option, fallback):
        """Safely looks up a style color, providing a fallback for errors or empty values."""
        try:
            color = self.style.lookup(style_name, option)
            # Return fallback if the lookup returns an empty string, which is invalid for tk widgets.
            return color if color else fallback
        except tk.TclError:
            # Return fallback if the style option doesn't exist (e.g., 'insertcolor' in some themes).
            return fallback

    def _display_element_details(self, element: FGDElement | None):
        self._clear_properties_frame()
        self.selected_element = element
        if not element: return

        # --- MODIFIED: Get text widget colors from the theme using the safe helper ---
        # Fallbacks are provided for themes that may return empty strings or lack options.
        text_fg = self._get_style_color("TEntry", "foreground", "black")
        text_bg = self._get_style_color("TEntry", "fieldbackground", "white")
        # The insert color should default to the foreground color.
        text_insert_color = self._get_style_color("TEntry", "insertcolor", text_fg)

        if isinstance(element, IncludeDirective):
            ttk.Label(self.properties_frame_inner, text="Include Path:", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            path_entry = ttk.Entry(self.properties_frame_inner)
            path_entry.insert(0, element.file_path)
            path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            path_entry.bind("<FocusOut>", lambda e, el=element: setattr(el, 'file_path', e.widget.get()))

        elif isinstance(element, MapSize):
            ttk.Label(self.properties_frame_inner, text="Map Bounds (min, max):", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(self.properties_frame_inner, text=f"{element.min_coord}, {element.max_coord}").grid(row=0, column=1, padx=5, pady=5, sticky="w")

        elif isinstance(element, Version):
            ttk.Label(self.properties_frame_inner, text="FGD Version:", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ttk.Label(self.properties_frame_inner, text=str(element.version_number)).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        elif isinstance(element, (MaterialExclusion, AutoVisGroup)):
             ttk.Label(self.properties_frame_inner, text=element.name, font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
             ttk.Label(self.properties_frame_inner, text=element.description).grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
             ttk.Label(self.properties_frame_inner, text="(Editing not yet supported in GUI)").grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        elif isinstance(element, EntityClass):
            row = 0
            ttk.Label(self.properties_frame_inner, text="Class Name:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
            name_entry = ttk.Entry(self.properties_frame_inner)
            name_entry.insert(0, element.name)
            name_entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
            name_entry.bind("<FocusOut>", lambda e: self._update_element_name(element, name_entry.get()))
            row += 1

            ttk.Label(self.properties_frame_inner, text="Class Type:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
            types = ["PointClass", "SolidClass", "NPCClass", "KeyframeClass", "MoveClass", "FilterClass", "ExtendClass", "BaseClass"]
            type_combo = ttk.Combobox(self.properties_frame_inner, values=types, state="readonly")
            type_combo.set(element.class_type)
            type_combo.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
            type_combo.bind("<<ComboboxSelected>>", lambda e: self._update_class_type(element, type_combo.get()))
            row += 1

            # --- MODIFIED: Apply theme colors to tk.Text widgets ---
            ttk.Label(self.properties_frame_inner, text="Description:").grid(row=row, column=0, padx=5, pady=2, sticky="nw")
            desc_text = tk.Text(self.properties_frame_inner, height=3, wrap="word",
                                bg=text_bg, fg=text_fg, insertbackground=text_insert_color,
                                relief="flat", borderwidth=1, highlightthickness=0)
            desc_text.insert("1.0", element.description)
            desc_text.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
            desc_text.bind("<FocusOut>", lambda e: self._update_element_description(element, desc_text.get("1.0", "end-1c")))
            row += 1

            ttk.Label(self.properties_frame_inner, text="Base Classes:").grid(row=row, column=0, padx=5, pady=2, sticky="nw")
            base_text = tk.Text(self.properties_frame_inner, height=2, wrap="word",
                                bg=text_bg, fg=text_fg, insertbackground=text_insert_color,
                                relief="flat", borderwidth=1, highlightthickness=0)
            base_text.insert("1.0", ", ".join(element.base_classes))
            base_text.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
            base_text.bind("<FocusOut>", lambda e: self._update_base_classes(element, base_text.get("1.0", "end-1c")))
            row += 1

            helpers_frame = ttk.LabelFrame(self.properties_frame_inner, text="Editor Helpers")
            helpers_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5); row += 1

            helper_row = 0
            for key, val in element.helpers.items():
                ttk.Label(helpers_frame, text=f"{key}:").grid(row=helper_row, column=0, padx=5, pady=2, sticky="w")
                entry = ttk.Entry(helpers_frame)
                entry.insert(0, val)
                entry.grid(row=helper_row, column=1, padx=5, pady=2, sticky="ew")
                entry.bind("<FocusOut>", lambda e, k=key: element.helpers.update({k: e.widget.get()}))
                helper_row += 1
            helpers_frame.grid_columnconfigure(1, weight=1)

            def create_section(title, items, ui_creator, add_cmd, r):
                ttk.Separator(self.properties_frame_inner).grid(row=r, column=0, columnspan=2, sticky="ew", pady=(10,2)); r+=1

                title_frame = ttk.Frame(self.properties_frame_inner)
                title_frame.grid(row=r, column=0, columnspan=2, sticky="ew", padx=5)
                ttk.Label(title_frame, text=title, font="-weight bold").pack(side="left")
                ttk.Button(title_frame, text=f"Add {title.split(':')[0]}", command=add_cmd).pack(side="right")
                r+=1

                for item in items:
                    frame = ttk.Frame(self.properties_frame_inner)
                    frame.grid(row=r, column=0, columnspan=2, padx=10, pady=2, sticky="ew")
                    ui_creator(frame, element, item)
                    r+=1
                return r

            row = create_section("Keyvalues:", element.properties, self._create_property_ui, self._add_property_dialog, row)
            row = create_section("Inputs:", element.inputs, lambda f, el, i: self._create_io_ui(f, el, i, "input"), self._add_input_dialog, row)
            row = create_section("Outputs:", element.outputs, lambda f, el, i: self._create_io_ui(f, el, i, "output"), self._add_output_dialog, row)

        self.properties_frame_inner.grid_columnconfigure(1, weight=1)
        self.properties_frame_inner.update_idletasks()
        self.properties_canvas.configure(scrollregion=self.properties_canvas.bbox("all"))

    def _add_input_dialog(self): self._add_io_dialog("input")
    def _add_output_dialog(self): self._add_io_dialog("output")

    def show_about_window(self):
        AboutWindow(self, self.style, title="About Entity Forge", help_file="help.txt")

    def _add_io_dialog(self, io_type):
        if not isinstance(self.selected_element, EntityClass): return
        name = simpledialog.askstring(f"Add {io_type.capitalize()}", f"Enter {io_type.capitalize()} Name:")
        if name:
            arg_type = simpledialog.askstring("Argument Type", "Enter Argument Type (e.g., void, string):", initialvalue="void")
            if arg_type is not None:
                new_io = IO(io_type, name, arg_type, "")
                self.selected_element.add_io(new_io)
                self._display_element_details(self.selected_element)

    def _remove_io(self, io_obj: IO):
        if not isinstance(self.selected_element, EntityClass): return
        if messagebox.askyesno("Confirm Removal", f"Remove {io_obj.io_type} '{io_obj.name}'?"):
            (self.selected_element.inputs if io_obj.io_type == "input" else self.selected_element.outputs).remove(io_obj)
            self._display_element_details(self.selected_element)

    def _add_property_dialog(self):
        if not isinstance(self.selected_element, EntityClass): return
        name = simpledialog.askstring("Add Property", "Enter Property Name (e.g., targetname):")
        if name:
            prop_type = simpledialog.askstring("Add Property", "Enter Property Type (e.g., string, integer, choices, flags):", initialvalue="string")
            if prop_type:
                base_type = prop_type.split(',')[0].strip().lower()
                new_prop = None
                if base_type == 'choices': new_prop = ChoicesProperty(name, prop_type)
                elif base_type == 'flags': new_prop = FlagsProperty(name, prop_type)
                else: new_prop = KeyvalueProperty(name, prop_type)
                self.selected_element.properties.append(new_prop)
                self._display_element_details(self.selected_element)

    def _remove_property(self, prop: Property):
        if not isinstance(self.selected_element, EntityClass): return
        if messagebox.askyesno("Confirm Removal", f"Remove property '{prop.name}'?"):
            self.selected_element.properties.remove(prop)
            self._display_element_details(self.selected_element)

    def _add_choice(self, prop: ChoicesProperty):
        value = simpledialog.askstring("Add Choice", "Enter Choice Value:")
        if value:
            display = simpledialog.askstring("Add Choice", "Enter Display Name:", initialvalue=value.replace("_", " ").title())
            if display is not None:
                prop.choices.append(ChoiceItem(value, display, ""))
                self._display_element_details(self.selected_element)

    def _remove_choice(self, prop: ChoicesProperty, choice: ChoiceItem):
        if messagebox.askyesno("Confirm Removal", f"Remove choice '{choice.display_name}'?"):
            prop.choices.remove(choice)
            self._display_element_details(self.selected_element)

    def _add_flag(self, prop: FlagsProperty):
        value_str = simpledialog.askstring("Add Flag", "Enter Flag Value (integer):")
        if value_str and value_str.isdigit():
            display = simpledialog.askstring("Add Flag", "Enter Display Name:")
            if display is not None:
                ticked = messagebox.askyesno("Default State", "Should this flag be ticked by default?")
                prop.flags.append(FlagItem(int(value_str), display, "", ticked))
                self._display_element_details(self.selected_element)

    def _remove_flag(self, prop: FlagsProperty, flag: FlagItem):
        if messagebox.askyesno("Confirm Removal", f"Remove flag '{flag.display_name}'?"):
            prop.flags.remove(flag)
            self._display_element_details(self.selected_element)

    def _create_io_ui(self, parent, element, io_obj, io_type):
        ttk.Entry(parent, width=15).insert(0, io_obj.name).pack(side="left", padx=2)
        ttk.Entry(parent, width=10).insert(0, io_obj.arg_type).pack(side="left", padx=2)
        ttk.Entry(parent).insert(0, io_obj.description).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(parent, text="X", width=2, command=lambda: self._remove_io(io_obj)).pack(side="right", padx=2)

    def _create_property_ui(self, parent, element, prop):
        prop_frame = ttk.LabelFrame(parent, text=f"{prop.name} ({prop.prop_type})")
        prop_frame.pack(fill="x", expand=True, pady=2)

        # --- MODIFIED: Get text widget colors from the theme using the safe helper ---
        # Fallbacks are provided for themes that may return empty strings or lack options.
        text_fg = self._get_style_color("TEntry", "foreground", "black")
        text_bg = self._get_style_color("TEntry", "fieldbackground", "white")
        # The insert color should default to the foreground color.
        text_insert_color = self._get_style_color("TEntry", "insertcolor", text_fg)

        top_frame = ttk.Frame(prop_frame)
        top_frame.pack(fill="x", expand=True, padx=5, pady=5)
        ttk.Label(top_frame, text="Display Name:").pack(side="left")
        dn_entry = ttk.Entry(top_frame)
        dn_entry.insert(0, prop.display_name)
        dn_entry.pack(side="left", fill="x", expand=True, padx=5)
        dn_entry.bind("<FocusOut>", lambda e: setattr(prop, 'display_name', e.widget.get()))

        ttk.Label(top_frame, text="Default:").pack(side="left")
        dv_entry = ttk.Entry(top_frame, width=10)
        dv_entry.insert(0, prop.default_value)
        dv_entry.pack(side="left", padx=5)
        dv_entry.bind("<FocusOut>", lambda e: setattr(prop, 'default_value', e.widget.get()))

        readonly_var = tk.BooleanVar(value=prop.readonly)
        ttk.Checkbutton(top_frame, text="Readonly", variable=readonly_var, command=lambda: setattr(prop, 'readonly', readonly_var.get())).pack(side="left", padx=2)
        report_var = tk.BooleanVar(value=prop.report)
        ttk.Checkbutton(top_frame, text="Report", variable=report_var, command=lambda: setattr(prop, 'report', report_var.get())).pack(side="left", padx=2)

        ttk.Button(top_frame, text="Remove", command=lambda: self._remove_property(prop)).pack(side="right")

        # --- MODIFIED: Apply theme colors to this tk.Text widget ---
        desc_text = tk.Text(prop_frame, height=2, wrap="word", width=40,
                            bg=text_bg, fg=text_fg, insertbackground=text_insert_color,
                            relief="flat", borderwidth=1, highlightthickness=0)
        desc_text.insert("1.0", prop.description)
        desc_text.pack(fill="x", expand=True, padx=5, pady=(0,5))
        desc_text.bind("<FocusOut>", lambda e: setattr(prop, 'description', e.widget.get("1.0", "end-1c")))

        if isinstance(prop, ChoicesProperty):
            self._create_choices_ui(prop_frame, prop)
        elif isinstance(prop, FlagsProperty):
            self._create_flags_ui(prop_frame, prop)

    def _create_choices_ui(self, parent, prop: ChoicesProperty):
        choices_frame = ttk.Frame(parent)
        choices_frame.pack(fill="x", expand=True, padx=5, pady=5)
        ttk.Label(choices_frame, text="Choices:", font="-weight bold").grid(row=0, column=0, sticky="w")
        ttk.Button(choices_frame, text="Add Choice", command=lambda: self._add_choice(prop)).grid(row=0, column=1, sticky="e")
        choices_frame.grid_columnconfigure(1, weight=1)

        for i, choice in enumerate(prop.choices):
            f = ttk.Frame(choices_frame)
            f.grid(row=i+1, column=0, columnspan=2, sticky="ew", pady=2)
            ttk.Label(f, text="Val:").pack(side="left")
            v_entry = ttk.Entry(f, width=10); v_entry.insert(0, choice.value); v_entry.pack(side="left", padx=(0,5))
            v_entry.bind("<FocusOut>", lambda e, c=choice: setattr(c, 'value', e.widget.get()))
            ttk.Label(f, text="Name:").pack(side="left")
            n_entry = ttk.Entry(f); n_entry.insert(0, choice.display_name); n_entry.pack(side="left", fill="x", expand=True)
            n_entry.bind("<FocusOut>", lambda e, c=choice: setattr(c, 'display_name', e.widget.get()))

            ttk.Label(f, text="Desc:").pack(side="left", padx=(5,0))
            d_entry = ttk.Entry(f); d_entry.insert(0, choice.description); d_entry.pack(side="left", fill="x", expand=True)
            d_entry.bind("<FocusOut>", lambda e, c=choice: setattr(c, 'description', e.widget.get()))

            ttk.Button(f, text="X", width=2, command=lambda c=choice: self._remove_choice(prop, c)).pack(side="right", padx=2)

    def _create_flags_ui(self, parent, prop: FlagsProperty):
        flags_frame = ttk.Frame(parent)
        flags_frame.pack(fill="x", expand=True, padx=5, pady=5)
        ttk.Label(flags_frame, text="Flags:", font="-weight bold").grid(row=0, column=0, sticky="w")
        ttk.Button(flags_frame, text="Add Flag", command=lambda: self._add_flag(prop)).grid(row=0, column=1, sticky="e")
        flags_frame.grid_columnconfigure(1, weight=1)

        for i, flag in enumerate(prop.flags):
            f = ttk.Frame(flags_frame)
            f.grid(row=i+1, column=0, columnspan=2, sticky="ew", pady=2)
            ttk.Label(f, text="Val:").pack(side="left")
            v_entry = ttk.Entry(f, width=8); v_entry.insert(0, str(flag.value)); v_entry.pack(side="left", padx=(0,5))
            v_entry.bind("<FocusOut>", lambda e, fl=flag: setattr(fl, 'value', int(e.widget.get() or 0)))
            ttk.Label(f, text="Name:").pack(side="left")
            n_entry = ttk.Entry(f); n_entry.insert(0, flag.display_name); n_entry.pack(side="left", fill="x", expand=True)
            n_entry.bind("<FocusOut>", lambda e, fl=flag: setattr(fl, 'display_name', e.widget.get()))

            ticked_var = tk.BooleanVar(value=flag.default_ticked)
            ttk.Checkbutton(f, text="On?", variable=ticked_var, command=lambda fl=flag, v=ticked_var: setattr(fl, 'default_ticked', v.get())).pack(side="left", padx=5)

            ttk.Label(f, text="Desc:").pack(side="left", padx=(5,0))
            d_entry = ttk.Entry(f); d_entry.insert(0, flag.description); d_entry.pack(side="left", fill="x", expand=True)
            d_entry.bind("<FocusOut>", lambda e, fl=flag: setattr(fl, 'description', e.widget.get()))

            ttk.Button(f, text="X", width=2, command=lambda fl=flag: self._remove_flag(prop, fl)).pack(side="right", padx=2)

    def _update_element_name(self, element: EntityClass, new_name: str):
        if not new_name or element.name == new_name: return
        old_name = element.name
        if self.fgd_file.class_map.get(new_name):
            messagebox.showerror("Error", f"Class name '{new_name}' already exists.")
            # Revert the entry text
            self._display_element_details(element)
            return

        del self.fgd_file.class_map[old_name]
        if old_name in self.fgd_file.base_classes:
            del self.fgd_file.base_classes[old_name]

        element.name = new_name
        self.fgd_file.class_map[new_name] = element
        if element.class_type == "BaseClass":
            self.fgd_file.base_classes[new_name] = element
        self._update_elements_list()
        # Reselect the item with its new name
        self.elements_list.selection_set(new_name)

    def _update_class_type(self, element: EntityClass, new_type: str):
        if element.class_type == new_type: return
        if element.class_type == "BaseClass" and element.name in self.fgd_file.base_classes:
            del self.fgd_file.base_classes[element.name]
        element.class_type = new_type
        if new_type == "BaseClass":
            self.fgd_file.base_classes[element.name] = element
        self._update_elements_list()

    def _update_element_description(self, element: EntityClass, new_desc: str):
        element.description = new_desc

    def _update_base_classes(self, element: EntityClass, new_bases_str: str):
        element.base_classes = [b.strip() for b in new_bases_str.split(',') if b.strip()]

    # --- NEW: Function to handle theme switching and UI refresh ---
    def _switch_theme(self, dark_mode: bool):
        """Applies the selected theme and refreshes the properties view."""
        theme.switch_theme(self, dark_mode)
        # Re-display details to ensure all widgets get the new theme colors
        self._display_element_details(self.selected_element)