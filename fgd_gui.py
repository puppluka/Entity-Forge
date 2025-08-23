# fgd_gui.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import re
import traceback
import copy

# Import the core logic modules
from fgd_parser import FGDParser
from fgd_model import (
    FGDFile, EntityClass, KeyvalueProperty, ChoicesProperty, FlagsProperty,
    IO, ChoiceItem, FlagItem, IncludeDirective, Property, FGDElement, MapSize,
    Version, AutoVisGroup, MaterialExclusion
)
from fgd_serializer import FGDSerializer
from about import AboutWindow
import theme

# --- NEW: A comprehensive list of known editor helpers for the dropdown menu ---
# Compiled from the FGD Handbook PDF and the provided Quake 2 FGD file.
EDITOR_HELPERS = sorted([
    "axis", "beam", "catapult", "color", "cylinder", "decal", "direction",
    "flags", "fogcontroller", "frustum", "halfgridsnap", "iconsprite",
    "instance", "laser", "light", "lightcone", "lightprop", "line",
    "model", "obb", "origin", "overlay", "overlay_transition",
    "quadbounds", "ragdoll", "sequence", "sidelist", "size", "skin",
    "skycamera", "sphere", "spotlight", "sprite", "studio", "studioprop",
    "sun", "sweptplayerhull", "vecline", "wirebox", "worldtext", "worldtextvgui"
])


class InputDialog(simpledialog.Dialog):
    """A generic dialog for creating items with multiple fields, including comboboxes."""
    def __init__(self, parent, title, fields):
        self.fields = fields
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        self.widgets = {}
        for i, (key, label, type, initial, options) in enumerate(self.fields):
            ttk.Label(master, text=f"{label}:").grid(row=i, column=0, sticky="w", padx=5, pady=3)
            if type == 'combobox':
                widget = ttk.Combobox(master, values=options, state="readonly")
                if initial in options:
                    widget.set(initial)
                else:
                    widget.set(options[0])
                self.widgets[key] = widget
            else:  # entry
                widget = ttk.Entry(master)
                widget.insert(0, initial)
                self.widgets[key] = widget
            widget.grid(row=i, column=1, sticky="ew", padx=5, pady=3)
        master.grid_columnconfigure(1, weight=1)
        return self.widgets[self.fields[0][0]]

    def apply(self):
        self.result = {key: widget.get() for key, widget in self.widgets.items()}


class FGDApplication(tk.Tk):
    """Main Tkinter application class for the FGD Editor GUI."""
    def __init__(self):
        super().__init__()
        self.title("Entity Forge - FGD Editor")
        self.geometry("1200x800")

        self.style = ttk.Style(self)

        self.fgd_file: FGDFile | None = None
        self.current_fgd_path: str | None = None
        self.selected_element: FGDElement | None = None
        self.properties_frame_inner_id = None
        self.clipboard_element: FGDElement | None = None

        self.parser = FGDParser()
        self.serializer = FGDSerializer()

        theme.setup_theme(self)

        self._create_widgets()
        self._setup_menu()
        self._bind_hotkeys()

        theme.switch_theme(self, dark_mode=True)

    def _create_widgets(self):
        self.main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill="both", expand=True)

        self.elements_frame = ttk.Frame(self.main_pane, width=350, relief=tk.RIDGE, borderwidth=2)
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

        new_menubutton = ttk.Menubutton(button_frame, text="New...")
        new_menu = tk.Menu(new_menubutton, tearoff=0)
        new_menubutton["menu"] = new_menu

        new_menu.add_command(label="Entity Class", command=self._add_entity_class)
        new_menu.add_separator()
        new_menu.add_command(label="Include Directive", command=lambda: self._add_directive("include"))
        new_menu.add_command(label="Map Size", command=lambda: self._add_directive("mapsize"))
        new_menu.add_command(label="Version", command=lambda: self._add_directive("version"))
        new_menu.add_command(label="Material Exclusion", command=lambda: self._add_directive("materialexclusion"))
        new_menu.add_command(label="AutoVisGroup", command=lambda: self._add_directive("autovisgroup"))
        
        new_menubutton.pack(side="left", fill="x", expand=True, padx=(0, 1))

        duplicate_button = ttk.Button(button_frame, text="Duplicate", command=self._duplicate_selected_element)
        duplicate_button.pack(side="left", fill="x", expand=True, padx=1)

        delete_button = ttk.Button(button_frame, text="Delete", command=self._delete_selected_element)
        delete_button.pack(side="left", fill="x", expand=True, padx=(1, 0))
        
        reorder_frame = ttk.Frame(self.elements_frame)
        reorder_frame.pack(fill="x", padx=5, pady=(0,5))
        move_up_button = ttk.Button(reorder_frame, text="Move Up \u25B2", command=lambda: self._move_element("up"))
        move_up_button.pack(side="left", fill="x", expand=True, padx=(0, 2))
        move_down_button = ttk.Button(reorder_frame, text="Move Down \u25BC", command=lambda: self._move_element("down"))
        move_down_button.pack(side="right", fill="x", expand=True, padx=(2, 0))

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
        file_menu.add_command(label="New", command=self._new_fgd_file, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Open...", command=self._open_fgd_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self._save_fgd_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self._save_fgd_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit, accelerator="Ctrl+Q")

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Cut", command=self._handle_cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=self._handle_copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self._handle_paste, accelerator="Ctrl+V")
        edit_menu.add_command(label="Duplicate", command=self._duplicate_selected_element, accelerator="Ctrl+D")

        theme_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Dark", command=lambda: self._switch_theme(dark_mode=True))
        theme_menu.add_command(label="Light", command=lambda: self._switch_theme(dark_mode=False))

        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about_window)

    def _bind_hotkeys(self):
        self.bind_all("<Control-n>", lambda e: self._new_fgd_file())
        self.bind_all("<Control-o>", lambda e: self._open_fgd_file())
        self.bind_all("<Control-s>", lambda e: self._save_fgd_file())
        self.bind_all("<Control-Shift-S>", lambda e: self._save_fgd_file_as())
        self.bind_all("<Control-q>", lambda e: self.quit())
        self.bind_all("<Control-d>", lambda e: self._duplicate_selected_element())
        
        self.bind_all("<Control-x>", self._handle_cut)
        self.bind_all("<Control-c>", self._handle_copy)
        self.bind_all("<Control-v>", self._handle_paste)

    def _new_fgd_file(self):
        if self.fgd_file and messagebox.askyesno("Unsaved Changes", "You have an open file. Do you want to save it before creating a new one?"):
            self._save_fgd_file()
        
        self.fgd_file = FGDFile()
        self.current_fgd_path = None
        self.title("Entity Forge - New File")
        self._update_elements_list()
        self._clear_properties_frame()

    def _add_entity_class(self):
        if not self.fgd_file:
            messagebox.showwarning("No FGD Loaded", "Please open or create a new FGD file first.")
            return

        name = simpledialog.askstring("New Class", "Enter the new class name:")
        if not name: return
        
        clean_name = re.sub(r'\s+', '_', name)
        if clean_name in self.fgd_file.class_map:
            messagebox.showerror("Error", f"A class named '{clean_name}' already exists.")
            return

        new_element = EntityClass(class_type="PointClass", name=clean_name, description="A new entity class.")
        self.fgd_file.add_element(new_element)
        self._update_elements_list()
        self._select_element_in_tree(new_element.name)

    def _add_directive(self, directive_type: str):
        if not self.fgd_file:
            messagebox.showwarning("No FGD Loaded", "Please open or create a new FGD file first.")
            return

        new_element = None
        if directive_type == "include":
            path = simpledialog.askstring("New Include", "Enter file path:", initialvalue="common/base.fgd")
            if path: new_element = IncludeDirective(path)
        elif directive_type == "mapsize":
            coords = simpledialog.askstring("New Map Size", "Enter min, max coordinates:", initialvalue="-16384, 16384")
            if coords:
                try:
                    min_c, max_c = map(int, coords.replace(" ", "").split(','))
                    new_element = MapSize(min_c, max_c)
                except (ValueError, IndexError):
                    messagebox.showerror("Invalid Input", "Please enter two comma-separated integers.")
        elif directive_type == "version":
            ver = simpledialog.askinteger("New Version", "Enter version number:", initialvalue=1)
            if ver is not None: new_element = Version(ver)
        elif directive_type == "materialexclusion":
            new_element = MaterialExclusion([])
        elif directive_type == "autovisgroup":
            name = simpledialog.askstring("New AutoVisGroup", "Enter parent group name:", initialvalue="Parent Group")
            if name: new_element = AutoVisGroup(name, [])
        
        if new_element:
            self.fgd_file.add_element(new_element)
            self._update_elements_list()
            self._select_element_in_tree(new_element.name)

    def _delete_selected_element(self):
        selected_ids = self.elements_list.selection()
        if not selected_ids:
            return
        
        selected_id = selected_ids[0]
        selected_name = self.elements_list.item(selected_id, "text")

        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete '{selected_name}'?"):
            return
        
        element_to_delete = self.fgd_file.get_element_by_id(selected_id)

        if element_to_delete:
            self.fgd_file.remove_element(element_to_delete)
            self._update_elements_list()
            self._clear_properties_frame()

    def _open_fgd_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("FGD Files", "*.fgd"), ("All Files", "*.*")])
        if filepath:
            try:
                self.parser = FGDParser()
                self.fgd_file = self.parser.parse_fgd_file(filepath)
                self.current_fgd_path = filepath
                self.title(f"Entity Forge - {os.path.basename(filepath)}")
                self._update_elements_list()
                self._clear_properties_frame()
            except Exception as e:
                traceback.print_exc()
                messagebox.showerror("Load Error", f"Failed to load FGD file: {e}")
                self.fgd_file = None
                self.current_fgd_path = None
                self.title("Entity Forge")
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
            focused_widget = self.focus_get()
            if focused_widget:
                focused_widget.event_generate("<FocusOut>")
                self.update_idletasks()

            serialized_content = self.serializer.serialize_fgd(self.fgd_file)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(serialized_content)
            self.current_fgd_path = filepath
            self.title(f"Entity Forge - {os.path.basename(filepath)}")
            messagebox.showinfo("Save Successful", f"File saved to {os.path.basename(filepath)}")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Save Error", f"Failed to save file: {e}")

    def _update_elements_list(self):
        selection = self.elements_list.selection()
        
        self.fgd_file.element_id_map.clear()
        
        for iid in self.elements_list.get_children():
            self.elements_list.delete(iid)
            
        if self.fgd_file:
            for i, element in enumerate(self.fgd_file.elements):
                element_id = f"item_{i}"
                self.fgd_file.element_id_map[element_id] = element
                try:
                    self.elements_list.insert("", "end", iid=element_id, text=str(element.name), values=(element.class_type,))
                except tk.TclError as e:
                    print(f"Error adding element to Treeview: {e}. Element: {element.name}, Type: {element.class_type}")
                    messagebox.showerror("GUI Error", f"Failed to display an FGD element. Check terminal for details.")

        if selection:
            try:
                self.elements_list.selection_set(selection)
                self.elements_list.see(selection[0])
            except tk.TclError:
                pass 

    def _select_element_in_tree(self, element_name: str):
        for iid in self.elements_list.get_children():
            if self.elements_list.item(iid, "text") == element_name:
                self.elements_list.selection_set(iid)
                self.elements_list.focus(iid)
                self.elements_list.see(iid)
                return

    def _on_element_select(self, event):
        selected_ids = self.elements_list.selection()
        if selected_ids:
            element = self.fgd_file.get_element_by_id(selected_ids[0])
            self._display_element_details(element)
        else:
            self._clear_properties_frame()

    def _clear_properties_frame(self):
        for widget in self.properties_frame_inner.winfo_children():
            widget.destroy()
        canvas_bg = self.style.lookup("TFrame", "background")
        self.properties_canvas.config(bg=canvas_bg)

    def _get_style_color(self, style_name, option, fallback):
        try:
            color = self.style.lookup(style_name, option)
            return color if color else fallback
        except tk.TclError:
            return fallback

    def _display_element_details(self, element: FGDElement | None):
        self._clear_properties_frame()
        self.selected_element = element
        if not element: return

        text_fg = self._get_style_color("TEntry", "foreground", "black")
        text_bg = self._get_style_color("TEntry", "fieldbackground", "white")
        text_insert_color = self._get_style_color("TEntry", "insertcolor", text_fg)

        if isinstance(element, IncludeDirective):
            ttk.Label(self.properties_frame_inner, text="Include Path:", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            path_entry = ttk.Entry(self.properties_frame_inner)
            path_entry.insert(0, element.file_path)
            path_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            path_entry.bind("<FocusOut>", lambda e, el=element: self._update_include_path(el, e.widget.get()))

        elif isinstance(element, MapSize):
            ttk.Label(self.properties_frame_inner, text="Min Coordinate:", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            min_entry = ttk.Entry(self.properties_frame_inner, width=10)
            min_entry.insert(0, str(element.min_coord))
            min_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            min_entry.bind("<FocusOut>", lambda e, el=element: self._update_mapsize(el, 'min', e.widget))

            ttk.Label(self.properties_frame_inner, text="Max Coordinate:", font="-weight bold").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            max_entry = ttk.Entry(self.properties_frame_inner, width=10)
            max_entry.insert(0, str(element.max_coord))
            max_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
            max_entry.bind("<FocusOut>", lambda e, el=element: self._update_mapsize(el, 'max', e.widget))

        elif isinstance(element, Version):
            ttk.Label(self.properties_frame_inner, text="FGD Version:", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            ver_entry = ttk.Entry(self.properties_frame_inner, width=10)
            ver_entry.insert(0, str(element.version_number))
            ver_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            ver_entry.bind("<FocusOut>", lambda e, el=element: self._update_version(el, e.widget))
            
        elif isinstance(element, MaterialExclusion):
            ttk.Label(self.properties_frame_inner, text="Excluded Paths:", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="nw")
            desc_label = ttk.Label(self.properties_frame_inner, text="(One full material path per line)")
            desc_label.grid(row=1, column=0, columnspan=2, padx=5, pady=(0,5), sticky="w")
            
            ex_text = tk.Text(self.properties_frame_inner, height=10, wrap="word",
                              bg=text_bg, fg=text_fg, insertbackground=text_insert_color,
                              relief="flat", borderwidth=1, highlightthickness=0)
            ex_text.insert("1.0", "\n".join(element.excluded_paths))
            ex_text.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
            ex_text.bind("<FocusOut>", lambda e, el=element: self._update_material_exclusion(el, e.widget.get("1.0", "end-1c")))

        elif isinstance(element, AutoVisGroup):
            ttk.Label(self.properties_frame_inner, text="Parent Name:", font="-weight bold").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            parent_entry = ttk.Entry(self.properties_frame_inner)
            parent_entry.insert(0, element.parent_name)
            parent_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            parent_entry.bind("<FocusOut>", lambda e, el=element: self._update_autovisgroup_parent(el, e.widget.get()))

            ttk.Label(self.properties_frame_inner, text="Children:", font="-weight bold").grid(row=1, column=0, padx=5, pady=5, sticky="nw")
            desc_label = ttk.Label(self.properties_frame_inner, text="(One entity or subgroup name per line)")
            desc_label.grid(row=2, column=0, columnspan=2, padx=5, pady=(0,5), sticky="w")
            
            child_text = tk.Text(self.properties_frame_inner, height=10, wrap="word",
                                 bg=text_bg, fg=text_fg, insertbackground=text_insert_color,
                                 relief="flat", borderwidth=1, highlightthickness=0)
            
            child_text_content = []
            for child in element.children:
                if isinstance(child, str):
                    child_text_content.append(child)
                elif isinstance(child, AutoVisGroup):
                    child_text_content.append(f"[Sub-group: {child.parent_name}] (Not editable here)")
            
            child_text.insert("1.0", "\n".join(child_text_content))
            child_text.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
            child_text.bind("<FocusOut>", lambda e, el=element: self._update_autovisgroup_children(el, e.widget.get("1.0", "end-1c")))

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
            self._create_helpers_ui(helpers_frame, element)


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
        if isinstance(element, (MaterialExclusion, AutoVisGroup)):
             self.properties_frame_inner.grid_rowconfigure(2 if isinstance(element, MaterialExclusion) else 3, weight=1)

        self.properties_frame_inner.update_idletasks()
        self.properties_canvas.configure(scrollregion=self.properties_canvas.bbox("all"))

    def _add_input_dialog(self): self._add_io_dialog("input")
    def _add_output_dialog(self): self._add_io_dialog("output")

    def show_about_window(self):
        AboutWindow(self, self.style, title="About Entity Forge", help_file="help.txt")

    def _add_io_dialog(self, io_type):
        if not isinstance(self.selected_element, EntityClass): return

        io_arg_types = ['void', 'string', 'integer', 'float', 'bool', 'ehandle', 'color255', 'vector']
        fields = [
            ('name', 'Name', 'entry', f'OnNew{io_type.capitalize()}', None),
            ('arg_type', 'Argument Type', 'combobox', 'void', io_arg_types)
        ]
        dialog = InputDialog(self, f"Add {io_type.capitalize()}", fields)
        if dialog.result:
            new_io = IO(io_type, dialog.result['name'], dialog.result['arg_type'], "")
            self.selected_element.add_io(new_io)
            self._display_element_details(self.selected_element)

    def _remove_io(self, io_obj: IO):
        if not isinstance(self.selected_element, EntityClass): return
        if messagebox.askyesno("Confirm Removal", f"Remove {io_obj.io_type} '{io_obj.name}'?"):
            (self.selected_element.inputs if io_obj.io_type == "input" else self.selected_element.outputs).remove(io_obj)
            self._display_element_details(self.selected_element)

    def _add_property_dialog(self):
        if not isinstance(self.selected_element, EntityClass): return
        
        prop_types = [
            'string', 'integer', 'float', 'choices', 'flags', 'bool', 'angle', 'color255', 
            'decal', 'material', 'sound', 'sprite', 'studio', 'target_destination', 'target_source', 'vector'
        ]
        fields = [
            ('name', 'Name', 'entry', 'new_property', None),
            ('type', 'Property Type', 'combobox', 'string', prop_types)
        ]
        dialog = InputDialog(self, "Add Property", fields)
        if dialog.result:
            name, prop_type = dialog.result['name'], dialog.result['type']
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
        if value is not None:
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
        entry_name = ttk.Entry(parent, width=15); entry_name.insert(0, io_obj.name); entry_name.pack(side="left", padx=2)
        entry_name.bind("<FocusOut>", lambda e, o=io_obj: setattr(o, 'name', e.widget.get()))
        entry_type = ttk.Entry(parent, width=10); entry_type.insert(0, io_obj.arg_type); entry_type.pack(side="left", padx=2)
        entry_type.bind("<FocusOut>", lambda e, o=io_obj: setattr(o, 'arg_type', e.widget.get()))
        entry_desc = ttk.Entry(parent); entry_desc.insert(0, io_obj.description); entry_desc.pack(side="left", fill="x", expand=True, padx=2)
        entry_desc.bind("<FocusOut>", lambda e, o=io_obj: setattr(o, 'description', e.widget.get()))
        ttk.Button(parent, text="X", width=2, command=lambda: self._remove_io(io_obj)).pack(side="right", padx=2)

    def _create_property_ui(self, parent, element, prop):
        prop_frame = ttk.LabelFrame(parent, text=f"{prop.name} ({prop.prop_type})")
        prop_frame.pack(fill="x", expand=True, pady=2)

        text_fg = self._get_style_color("TEntry", "foreground", "black")
        text_bg = self._get_style_color("TEntry", "fieldbackground", "white")
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
    
    def _create_helpers_ui(self, parent, element):
        for widget in parent.winfo_children():
            widget.destroy()

        for i, (key, val) in enumerate(element.helpers.items()):
            ttk.Label(parent, text=f"{key}:").grid(row=i, column=0, padx=5, pady=2, sticky="w")
            entry = ttk.Entry(parent)
            entry.insert(0, val)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            entry.bind("<FocusOut>", lambda e, k=key: element.helpers.update({k: e.widget.get()}))
            
            remove_btn = ttk.Button(parent, text="X", width=2, command=lambda k=key: self._remove_helper(element, k))
            remove_btn.grid(row=i, column=2, padx=5, pady=2)
        
        add_btn = ttk.Button(parent, text="Add Helper", command=lambda: self._add_helper_dialog(element))
        add_btn.grid(row=len(element.helpers), column=0, columnspan=3, pady=5, sticky="ew", padx=5)
        
        parent.grid_columnconfigure(1, weight=1)

    # --- MODIFIED: Use InputDialog with combobox for helper names ---
    def _add_helper_dialog(self, element: EntityClass):
        fields = [
            ('name', 'Helper Name', 'combobox', 'color', EDITOR_HELPERS),
            ('args', 'Arguments', 'entry', '', None)
        ]
        dialog = InputDialog(self, "Add Editor Helper", fields)
        if dialog.result:
            name, args = dialog.result['name'], dialog.result['args']
            if name:
                element.helpers[name.lower()] = args
                self._display_element_details(element)

    def _remove_helper(self, element: EntityClass, key: str):
        if key in element.helpers:
            del element.helpers[key]
            self._display_element_details(element)

    def _update_include_path(self, element: IncludeDirective, new_path: str):
        element.file_path = new_path
        element.update_name()
        self._update_elements_list()

    def _update_mapsize(self, element: MapSize, part: str, widget: ttk.Entry):
        try:
            new_value = int(widget.get())
            if part == 'min':
                element.min_coord = new_value
            else:
                element.max_coord = new_value
            element.update_description()
        except ValueError:
            messagebox.showerror("Invalid Input", "Coordinate must be an integer.")
            original_value = element.min_coord if part == 'min' else element.max_coord
            widget.delete(0, tk.END)
            widget.insert(0, str(original_value))

    def _update_version(self, element: Version, widget: ttk.Entry):
        try:
            new_value = int(widget.get())
            element.version_number = new_value
            element.update_description()
        except ValueError:
            messagebox.showerror("Invalid Input", "Version must be an integer.")
            widget.delete(0, tk.END)
            widget.insert(0, str(element.version_number))

    def _update_material_exclusion(self, element: MaterialExclusion, text_content: str):
        element.excluded_paths = [line.strip() for line in text_content.split('\n') if line.strip()]
        element.update_description()

    def _update_autovisgroup_parent(self, element: AutoVisGroup, new_name: str):
        if new_name:
            element.parent_name = new_name
            element.update_name()
            self._update_elements_list()

    def _update_autovisgroup_children(self, element: AutoVisGroup, text_content: str):
        new_children = []
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        existing_subgroups = [child for child in element.children if isinstance(child, AutoVisGroup)]
        
        for line in lines:
            if line.startswith('[Sub-group:'): continue 
            new_children.append(line)
        
        element.children = new_children + existing_subgroups

    def _update_element_name(self, element: EntityClass, new_name: str):
        if not new_name or element.name == new_name: return
        old_name = element.name
        if self.fgd_file.class_map.get(new_name):
            messagebox.showerror("Error", f"Class name '{new_name}' already exists.")
            self._display_element_details(element) 
            return

        self.fgd_file.rename_class(old_name, new_name)
        element.name = new_name
        self._update_elements_list()
        
        new_id = self.fgd_file.get_id_by_element(element)
        if new_id: self.elements_list.selection_set(new_id)

    def _update_class_type(self, element: EntityClass, new_type: str):
        if element.class_type == new_type: return
        self.fgd_file.change_class_type(element.name, new_type)
        self._update_elements_list()

    def _update_element_description(self, element: EntityClass, new_desc: str):
        element.description = new_desc

    def _update_base_classes(self, element: EntityClass, new_bases_str: str):
        element.base_classes = [b.strip() for b in new_bases_str.split(',') if b.strip()]

    def _switch_theme(self, dark_mode: bool):
        theme.switch_theme(self, dark_mode)
        self._display_element_details(self.selected_element)
    
    def _move_element(self, direction: str):
        if not self.fgd_file or not self.elements_list.selection(): return
        
        selected_id = self.elements_list.selection()[0]
        element = self.fgd_file.get_element_by_id(selected_id)
        if not element: return

        try:
            current_index = self.fgd_file.elements.index(element)
            if direction == "up" and current_index > 0:
                self.fgd_file.elements.insert(current_index - 1, self.fgd_file.elements.pop(current_index))
            elif direction == "down" and current_index < len(self.fgd_file.elements) - 1:
                self.fgd_file.elements.insert(current_index + 1, self.fgd_file.elements.pop(current_index))
            else:
                return 
            
            self._update_elements_list()
            new_id = self.fgd_file.get_id_by_element(element)
            if new_id:
                self.elements_list.selection_set(new_id)
                self.elements_list.focus(new_id)
                self.elements_list.see(new_id)

        except ValueError:
            messagebox.showerror("Error", "Could not find the selected element to move it.")

    def _duplicate_selected_element(self, event=None):
        if not self.fgd_file or not self.elements_list.selection(): return
        
        selected_id = self.elements_list.selection()[0]
        original_element = self.fgd_file.get_element_by_id(selected_id)
        if not original_element: return
        
        new_element = original_element.duplicate()

        if isinstance(new_element, EntityClass):
            new_name = simpledialog.askstring("Duplicate Class", "Enter name for the new class:", initialvalue=f"{new_element.name}_copy")
            if not new_name: return
            if new_name in self.fgd_file.class_map:
                messagebox.showerror("Error", f"A class named '{new_name}' already exists.")
                return
            new_element.name = new_name
        
        original_index = self.fgd_file.elements.index(original_element)
        self.fgd_file.elements.insert(original_index + 1, new_element)
        self.fgd_file.add_element(new_element) 
        self.fgd_file.elements.pop() 

        self._update_elements_list()
        self._select_element_in_tree(new_element.name)

    def _handle_cut(self, event=None):
        widget = self.focus_get()
        if isinstance(widget, ttk.Treeview):
            self._copy_element()
            self._delete_selected_element()
        else:
            try: widget.event_generate("<<Cut>>")
            except tk.TclError: pass
        return "break"

    def _handle_copy(self, event=None):
        widget = self.focus_get()
        if isinstance(widget, ttk.Treeview):
            self._copy_element()
        else:
            try: widget.event_generate("<<Copy>>")
            except tk.TclError: pass
        return "break"

    def _handle_paste(self, event=None):
        widget = self.focus_get()
        if isinstance(widget, ttk.Treeview):
            self._paste_element()
        else:
            try: widget.event_generate("<<Paste>>")
            except tk.TclError: pass
        return "break"

    def _copy_element(self):
        if not self.elements_list.selection(): return
        selected_id = self.elements_list.selection()[0]
        element = self.fgd_file.get_element_by_id(selected_id)
        if element:
            self.clipboard_element = element.duplicate()

    def _paste_element(self):
        if not self.clipboard_element: return
        
        new_element = self.clipboard_element.duplicate()

        if isinstance(new_element, EntityClass):
            original_name = new_element.name
            counter = 1
            while new_element.name in self.fgd_file.class_map:
                new_element.name = f"{original_name}_paste{counter}"
                counter += 1

        insert_index = len(self.fgd_file.elements)
        if self.elements_list.selection():
            selected_id = self.elements_list.selection()[0]
            selected_element = self.fgd_file.get_element_by_id(selected_id)
            if selected_element:
                try:
                    insert_index = self.fgd_file.elements.index(selected_element) + 1
                except ValueError:
                    pass # Element not in list, append to end
        
        self.fgd_file.elements.insert(insert_index, new_element)
        if isinstance(new_element, EntityClass):
            self.fgd_file.class_map[new_element.name] = new_element
            if new_element.class_type == "BaseClass":
                self.fgd_file.base_classes[new_element.name] = new_element

        self._update_elements_list()
        self._select_element_in_tree(new_element.name)