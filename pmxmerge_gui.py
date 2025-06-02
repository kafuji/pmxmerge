import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import json

VERSION = "1.1.0"
SETTINGS_FILE = "pmxmerge_settings.json"

def save_settings(settings: dict):
    """Save settings to JSON file."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save settings: {e}")


def load_settings() -> dict:
    """Load settings from JSON file if it exists."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load settings: {e}")
    return {}


import pmxmerge
def run_merge(base_path: str, patch_path: str, out_path: str = "", **kwargs):
    """
    Merges two PMX files by patching geometry and morphs.
    """

    if not base_path or not patch_path:
        messagebox.showerror("Error", "Both Base and Patch PMX files must be specified.")
        return
    if base_path == patch_path:
        messagebox.showerror("Error", "Base and Patch PMX files cannot be the same.")
        return
    if not out_path:
        out_path = base_path

    if not out_path.endswith('.pmx'):
        messagebox.showerror("Error", "Output PMX file must have a .pmx extension.")
        return

    if not os.path.isfile(base_path) or not os.path.isfile(patch_path):
        messagebox.showerror("Error", "Base or patch PMX file does not exist.")
        return

    # Build merge and update options
    append = {
        "MORPH": kwargs.get("append_morphs", True),
        "PHYSICS": kwargs.get("append_physics", True),
        "DISPLAY": kwargs.get("append_display", True),
    }
    update = {
        "BONE": kwargs.get("update_bones", True),
        "MAT_SETTINGS": kwargs.get("update_mat_settings", True),
        "MORPH": kwargs.get("update_morphs", True),
        "PHYSICS": kwargs.get("update_physics", True),
        "DISPLAY": kwargs.get("update_display", True),
    }

    # Remove False options to avoid unnecessary processing
    append = {k: v for k, v in append.items() if v}
    update = {k: v for k, v in update.items() if v}

    # Debugging output
    ret, msg = pmxmerge.merge_pmx_files(
            base_path,
            patch_path,
            out_path,
            append=append,
            update=update,
        )

    if not ret:
        messagebox.showerror("Error", f"PMX merge failed: {msg}")
    else:
        messagebox.showinfo("Success", f"PMX files merged successfully: {out_path}")


# ToolTip class for displaying tooltips on widgets
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = y = 0
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
                tw, text=self.text, justify="left",
                background="#ffffe0", relief="solid", borderwidth=1,
                font=("tahoma", "9", "normal"))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# Function to update the button state based on input validity
def update_button_state(base_var, patch_var, out_var, tb_base, tb_patch, tb_out, run_button):
    base_valid = base_var.get().endswith(".pmx") and os.path.isfile(base_var.get())
    patch_valid = patch_var.get().endswith(".pmx") and os.path.isfile(patch_var.get())
    out_valid = not out_var.get() or out_var.get().endswith(".pmx")

    tb_base.config(bg="white" if base_valid else "#ffe0e0")
    tb_patch.config(bg="white" if patch_valid else "#ffe0e0")
    tb_out.config(bg="white" if not out_var.get() or out_var.get().endswith(".pmx") else "#ffe0e0")

    if base_valid and patch_valid and out_valid:
        run_button.config(state="normal", bg="green", fg="white")
    else:
        run_button.config(state="disabled", bg="SystemButtonFace", fg="black")


# Main function to create the GUI
def main():
    # Create the main window
    root = TkinterDnD.Tk()
    root.title(f"PMX Merge Tool {VERSION}")
    root.resizable(False, False)

    settings = load_settings()

    base_var = tk.StringVar(value=settings.get("base_pmx", ""))
    patch_var = tk.StringVar(value=settings.get("patch_pmx", ""))
    out_var = tk.StringVar(value=settings.get("output_pmx", "result.pmx"))

    # Merge and Update Options
    append_morphs_var = tk.BooleanVar(value=settings.get("append_morphs", True))
    append_physics_var = tk.BooleanVar(value=settings.get("append_physics", True))
    append_display_var = tk.BooleanVar(value=settings.get("append_display", False))

    update_bones_var = tk.BooleanVar(value=settings.get("update_bones", True))
    update_mat_settings_var = tk.BooleanVar(value=settings.get("update_mat_settings", True))
    update_morphs_var = tk.BooleanVar(value=settings.get("update_morphs", True))
    update_physics_var = tk.BooleanVar(value=settings.get("update_physics", True))
    update_display_var = tk.BooleanVar(value=settings.get("update_display", False))

    # Main frame for input fields
    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack(fill="both", expand=True)

    # Create input fields for Base, Patch, and Output PMX files
    run_button = tk.Button(frame)

    # Update callback to enable/disable the run button based on input validity
    update_cb = lambda: update_button_state(base_var, patch_var, out_var, tb_base, tb_patch, tb_out, run_button)

    def browse_file(var):
        path = filedialog.askopenfilename(filetypes=[("PMX files", "*.pmx")])
        if path:
            var.set(path)

    def create_path_input(master, label_text, row, var, on_update=None):
        label = tk.Label(master, text=label_text)
        label.grid(row=row, column=0, sticky="e")
        entry = tk.Entry(master, textvariable=var, width=100)
        entry.grid(row=row, column=1, padx=8, pady=5)
        browse_btn = tk.Button(master, text="Browse...", command=lambda: browse_file(var))
        browse_btn.grid(row=row, column=2)

        entry.drop_target_register(DND_FILES)
        def handle_drop(e):
            var.set(e.data.strip('{}').split()[0])
            if on_update:
                on_update()
        entry.dnd_bind('<<Drop>>', handle_drop)

        return entry

    tb_base = create_path_input(frame, "Base PMX:", 0, base_var, update_cb)
    ToolTip(tb_base, "Base PMX file to merge into. Must be specified.")
    tb_patch = create_path_input(frame, "Patch PMX:", 1, patch_var, update_cb)
    ToolTip(tb_patch, "Patch PMX file to merge. Must be specified.")

    label = tk.Label(frame, text="* Please ensure both models don't have duplicate/empty names.", font=("Arial", 9, "italic"), fg="red")
    label.grid(row=2, column=1, columnspan=2, pady=2, sticky="w")

    tb_out = create_path_input(frame, "Output PMX:", 3, out_var, update_cb)
    ToolTip(tb_out, "Output PMX file path (Optional. If not specified, will overwrite the base PMX file).")

    label = tk.Label(frame, text="* Relative to Base PMX file's directory.", font=("Arial", 9, "italic"), fg="gray")
    label.grid(row=4, column=1, columnspan=2, pady=2, sticky="w")


    ##########################################################
    # Checkboxes for merge and update options

    # Create a function to create checkboxes with tooltips
    def create_checkbox(master, text, var, col, tooltip_text=None):
        cb = tk.Checkbutton(master, text=text, variable=var)
        cb.grid(row=0, column=col, sticky="w", padx=5, pady=2)
        if tooltip_text:
            ToolTip(cb, tooltip_text)
        return cb

    # Append Options
    append_options_frame = tk.LabelFrame(frame, text="Append New", padx=10, pady=10)
    append_options_frame.grid(row=5, column=0, columnspan=5, pady=4, sticky="we")
    OPTIONS_APPEND = [
        ("Morphs", append_morphs_var, "Append new morphs from the patch model."),
        ("Physics", append_physics_var, "Append new physics from the patch model."),
        ("Display Groups", append_display_var, "Append new display groups and their entries from the patch model."),
    ]
    for i, (text, var, tooltip) in enumerate(OPTIONS_APPEND):
        create_checkbox(append_options_frame, text, var, i, tooltip)

    # Label: Bones and Materials are always appended
    label = tk.Label(append_options_frame, text="* New Bones and Materials (and their mesh data) will always be appended.", font=("Arial", 9, "italic"), fg="green")
    label.grid(row=1, column=0, columnspan=5, pady=2, sticky="w")
    # Label: Existing Material's mesh data is always replaced with patch models
    label = tk.Label(append_options_frame, text="* Existing mesh data and corresponding Vertex/UV Morphs will always be merged.", font=("Arial", 9, "italic"), fg="green")
    label.grid(row=2, column=0, columnspan=5, pady=2, sticky="w")

    # Update Options
    update_option_frame = tk.LabelFrame(frame, text="Update/Replace Existing", padx=10, pady=10)
    update_option_frame.grid(row=6, column=0, columnspan=5, pady=2, sticky="we")
    OPTIONS_UPDATE = [
        ("Bone Settings", update_bones_var, "Update existing bone settings by using patch model's bones."),
        ("Material Settings", update_mat_settings_var, "Update existing material settings (textures, colors, etc.) by using patch model's materials."),
        ("Morphs", update_morphs_var, "Update existing morph settings by using patch model's morphs."),
        ("Physics", update_physics_var, "Update existing physics features (Rigid Bodies and Joints) by using patch model's physics."),
        ("Display Groups", update_display_var, "Replace existing display groups by using patch model's display groups."),
    ]
    for i, (text, var, tooltip) in enumerate(OPTIONS_UPDATE):
        create_checkbox(update_option_frame, text, var, i, tooltip)

    # Create the run button
    run_button.config(
        text="▶ Merge PMX",
        font=("Arial", 16, "bold"),
        command=lambda: run_merge(
            base_var.get(),
            patch_var.get(),
            out_var.get(),
            append_morphs=append_morphs_var.get(),
            append_physics=append_physics_var.get(),
            append_display=append_display_var.get(),

            update_bones=update_bones_var.get(),
            update_mat_settings=update_mat_settings_var.get(),
            update_morphs=update_morphs_var.get(),
            update_physics=update_physics_var.get(),
            update_display=update_display_var.get()
        ),

    )
    run_button.grid(row=7, column=0, columnspan=3, pady=10, sticky="ew")
    ToolTip(run_button, "Click to merge the specified PMX files.")

    # Bind the update callback to the StringVars
    base_var.trace_add("write", lambda *args: update_cb())
    patch_var.trace_add("write", lambda *args: update_cb())
    out_var.trace_add("write", lambda *args: update_cb())

    update_button_state(base_var, patch_var, out_var, tb_base, tb_patch, tb_out, run_button)

    # On close event to save settings
    def on_close():
        current_settings = {
            "base_pmx": base_var.get(),
            "patch_pmx": patch_var.get(),
            "output_pmx": out_var.get(),
            "append_morphs": append_morphs_var.get(),
            "append_physics": append_physics_var.get(),
            "append_display": append_display_var.get(),
            "update_bones": update_bones_var.get(),
            "update_mat_settings": update_mat_settings_var.get(),
            "update_morphs": update_morphs_var.get(),
            "update_physics": update_physics_var.get(),
            "update_display": update_display_var.get(),
        }
        save_settings(current_settings)
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()

if __name__ == "__main__":
    main()

# End of pmxappend_gui.py
