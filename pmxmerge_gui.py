import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

import pmxmerge_core

def run_merge(base_path: str, patch_path: str, out_path: str, replace_bones: bool = False, merge_phys: bool = False, merge_disp: bool = False):
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

    ret, msg = pmxmerge_core.merge_pmx_files(
            base_path,
            patch_path,
            out_path,
            replace_bones=replace_bones,
            merge_phys=merge_phys,
            merge_disp=merge_disp
        )

    if not ret:
        messagebox.showerror("Error", f"PMX merge failed: {msg}")
    else:
        messagebox.showinfo("Success", f"PMX files merged successfully: {out_path}")


def create_path_input(master, label_text, row, var, on_update=None):
    label = tk.Label(master, text=label_text)
    label.grid(row=row, column=0, sticky="e")
    entry = tk.Entry(master, textvariable=var, width=80)
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

def browse_file(var):
    path = filedialog.askopenfilename(filetypes=[("PMX files", "*.pmx")])
    if path:
        var.set(path)


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
        label = tk.Label(tw, text=self.text, justify="left",
                         background="#ffffe0", relief="solid", borderwidth=1,
                         font=("tahoma", "9", "normal"))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


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


def main():
    root = TkinterDnD.Tk()
    root.title("PMX Merge Tool")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill="both", expand=True)

    base_var = tk.StringVar()
    patch_var = tk.StringVar()
    out_var = tk.StringVar()

    replace_bones_var = tk.BooleanVar()
    merge_phys_var = tk.BooleanVar()
    merge_disp_var = tk.BooleanVar()

    # ダミーの実行ボタンを先に作成（update用に）
    run_button = tk.Button(frame)

    # D&D後にも状態更新されるよう、lambdaでバインド
    update_cb = lambda: update_button_state(base_var, patch_var, out_var, tb_base, tb_patch, tb_out, run_button)

    tb_base = create_path_input(frame, "Base PMX:", 0, base_var, update_cb)
    ToolTip(tb_base, "Base PMX file to merge into. Must be specified.")
    tb_patch = create_path_input(frame, "Patch PMX:", 1, patch_var, update_cb)
    ToolTip(tb_patch, "Patch PMX file to merge. Must be specified.")
    tb_out = create_path_input(frame, "Output PMX:", 2, out_var, update_cb)
    ToolTip(tb_out, "Output PMX file path (Optional. If not specified, will overwrite the base PMX file).")

    # Create a label frame for options
    option_frame = tk.LabelFrame(frame, text="Options", padx=10, pady=10)
    option_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky="we")

    # Create checkboxes for options
    cb_replace = tk.Checkbutton(option_frame, text="Replace Bone Settings", variable=replace_bones_var)
    cb_replace.grid(row=0, column=0, sticky="w", padx=5, pady=1)
    ToolTip(cb_replace, "Replace bone settings with the patch model's bone settings (Keep base model's bone settings if unchecked).")

    cb_merge_physics = tk.Checkbutton(option_frame, text="Merge Physics", variable=merge_phys_var)
    cb_merge_physics.grid(row=0, column=1, sticky="w", padx=5, pady=2)
    ToolTip(cb_merge_physics, "Merge physics features (Rigid Bodies and Joints) from the patch model into the base model.")

    cb_merge_displaysettings = tk.Checkbutton(option_frame, text="Merge Display Settings", variable=merge_disp_var)
    cb_merge_displaysettings.grid(row=0, column=2, sticky="w", padx=5, pady=2)
    ToolTip(cb_merge_displaysettings, "Merge display settings from the patch model into the base model.")

    run_button.config(
        text="▶ Merge PMX",
        font=("Arial", 14, "bold"),
        command=lambda: run_merge(base_var.get(), patch_var.get(), out_var.get(), replace_bones_var.get(), merge_phys_var.get(), merge_disp_var.get()),
        state="disabled"
    )
    run_button.grid(row=4, column=1)
    ToolTip(run_button, "Click to merge the specified PMX files.")

    # traceでも同じ update を使う
    base_var.trace_add("write", lambda *args: update_cb())
    patch_var.trace_add("write", lambda *args: update_cb())
    out_var.trace_add("write", lambda *args: update_cb())

    update_button_state(base_var, patch_var, out_var, tb_base, tb_patch, tb_out, run_button)

    root.mainloop()

if __name__ == "__main__":
    main()
