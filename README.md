# PMXMerge

**PMXMerge** is a tool for merging two PMX (Polygon Model eXtended) models.

It is specifically designed for use cases where parts of a model have been exported separately (e.g., from Blender via `mmd_tools`) and need to be merged back into the original model while preserving data such as bones, morphs, and materials.

You can also use it to make an chimera model by merging multiple PMX files together (e.g., merging a base model with props, clothes, and hair models).

## Features

* Merges bones, materials (and their vertices), morphs, rigid bodies, and joints.
* Vertex morphs, material morphs, and group morphs are merged correctly.
* New items are appended to the end of the respective lists while preserviing sort order of existing items.
* Preserves existing bone settings unless explicitly replaced.
* Merging of Rigid Bodies and Joints is optional and can be skipped if not needed.

## Example Usage

### GUI version

Run pmxmerge_gui.exe or `python pmxmerge_gui.py` to launch the graphical user interface (GUI) for PMXMerge.
You can use the GUI to easily merge PMX files without needing to use the command line. The GUI provides a user-friendly interface for selecting files and performing the merge operation. 

You can specify the base PMX file, the patch PMX file, and the output PMX file in the GUI. Drag and drop the files into the GUI or use the file selection dialog to choose the files. Then click the "Merge" button to perform the merge operation. See the console output for any errors or warnings during the merge process.

### Python version

Example command to merge a base PMX file with a patch PMX file and output the result to a new PMX file:

```bash
python pmxmerge_cui.py --base base.pmx --patch patch.pmx --out result.pmx
```

Note: You need pmxmerge_core.py and pmx.py int the same directory as pmxmerge_cui.py to run this command.

### Arguments


| Argument          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `--base`, `-b`    | Path to the base PMX file to merge into (required)      |
| `--patch`, `-p`   | Path to the patch PMX file (required)                   |
| `--out`, `-o`     | Output PMX file path (overwrite base PMX file if not specified!)   |
| `--replace_bones` | Option to replace existing bone settings. Without it, existing bone settings will be preserved. |
| `--merge_physics` | Option to merge rigid bodies and joints. If not specified, they will be skipped. |

These options are available as checkboxes in the GUI.

```bash
python pmxmerge_cui.py --base base.pmx --patch patch.pmx --out result.pmx --replace_bones --merge_physics
```

## Notes

* Duplicate element names (bones, materials, morphs, rigid bodies and joints) in the both base and patch models are **not allowed**. Please fix them before merging.
* Merging Display slot settings are not supported yet.
* Only supports PMX version 2.0.

## Disclaimer

This tool is provided "as is" without any warranty of any kind, either expressed or implied. Use it at your own risk. The author is not responsible for any damages or losses resulting from the use of this tool.

## License

GPL-3.0-or-later
© 2025 Kafuji Sato
