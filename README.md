# PMXMerge

Version: 1.1.0

## About

**PMXMerge** is a tool for merging two PMX (Polygon Model eXtended) models.

It is specifically designed for use cases where parts of a model have been exported separately (e.g., from Blender via `mmd_tools`) and need to be merged back into the original model while preserving certain settings like bone settings, material settings, morphs, and physics properties.
It can be used to merge a base PMX model with a patch PMX model, where the patch model contains additional parts or modifications that need to be integrated into the base model.

You can also use it to make an chimera model by merging multiple PMX files together (e.g., merging a base model with props, clothes, and hair models).

## Features

* Merges bones, materials (and their vertices), morphs, rigid bodies, and joints.
* Vertex morphs, material morphs, and group morphs are merged correctly.
* New items are appended to the end of the respective lists while preserving sort order of existing items.
* Preserves existing bone/material/morph/physics/display group settings unless explicitly replaced.

## Example Usage

### GUI version

Run pmxmerge_gui.exe or `python pmxmerge_gui.py` to launch the graphical user interface (GUI) for PMXMerge.

To specify the base and patch PMX files, just drag and drop the files into the GUI or use the file selection dialog to choose the files.
You can choose which features to append or replace by check boxes in the GUI.

Then click the "Merge" button to perform the merge operation. See the console output for any errors or warnings during the merge process.

### Python version

Example command to merge a base PMX file with a patch PMX file and output the result to a new PMX file:

```bash
python pmxmerge_cui.py --base base.pmx --patch patch.pmx --out result.pmx --no_append DISPLAY --no_update MORPHS DISPLAY
```

Note: You need pmxmerge.py and pmx.py in the same directory as pmxmerge_cui.py to run this script.

### Arguments

| Argument          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `--help`, `-h` | Show this help message and exit                          |
| `--base`, `-b`    | Path to the base PMX file to merge into (required)     |
| `--patch`, `-p`   | Path to the patch PMX file (required)                   |
| `--out`, `-o`     | Output PMX file path (Default: result.pmx). Relative to the base PMX file's directory. |
| `--no_append`, `-a` | Comma-separated list of items to not append (any of `MORPHS PHYSICS DISPLAY`) |
| `--no_update`, `-u` | Comma-separated list of items to not update (any of `BONE MAT_SETTING MORPHS PHYSICS DISPLAY`) |
| `--version`, `-v` | Show the version of PMXMerge and exit                   |

- Bones will always be appended. 
- Mesh data (Vertices, Faces, and Vertex/UV Morph) will always be appended and merged into existing materials and corresponding morphs.

## Notes

* Duplicate/Empty element names (bones, materials, morphs, rigid bodies and joints) in the both base and patch models are **not allowed**. Please fix them before merging.
* Only supports PMX version 2.0.

## Disclaimer

This tool is provided "as is" without any warranty of any kind, either expressed or implied. Use it at your own risk. The author is not responsible for any damages or losses resulting from the use of this tool.

## License

GPL-3.0-or-later
© 2025 Kafuji Sato
