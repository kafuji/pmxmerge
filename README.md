# PMXMerge

Version: 1.1.0

## About

**PMXMerge** is a tool for merging two PMX (Polygon Model eXtended) models.

It is specifically designed for use cases where parts of a model have been exported separately (e.g., from Blender via `mmd_tools`) and need to be merged back into the original model while preserving certain settings like bone settings, material settings, morphs, and physics properties.

You can also use it to make an chimera model by merging multiple PMX files together (e.g., merging a base model with props, clothes, and hair models).

## Features

* Merges bones, materials (and their vertices), morphs, rigid bodies, and joints.
* Vertex morphs, UV morphs, material morphs, and group morphs are merged correctly.
* New items are appended to the end of the respective lists while preserving sort order of existing items.
* Preserves existing bone/material/morph/physics/display group settings if specified.

## Example Usage

### GUI version

Run pmxmerge_gui.exe or `python pmxmerge_gui.py` to launch the graphical user interface (GUI) for PMXMerge.

1. Specify the base and patch PMX files by drag&drop or using the file selection dialog.
2. Optionally, specify the output PMX file path (default is `result.pmx` in the same directory as the base PMX file).
3. Select which items to append or update:
   * **Append**: Choose features to append from the patch PMX file.
   * **Update/Replace**: Choose features to update in the base PMX file with those from the patch PMX file.
4. Click the "Merge PMX" button to perform the merge operation.

* New Bones and Materials will always be appended.
* Existing mesh data (Vertices, Faces) will always be replaced with the patch's mesh data.
* Vertex/UV Morphs will always be appended(new ones)/merged(existing ones).
  * If existing morph with different type is found, it will be replaced with the patch's morph.

### Python version

Example command to merge a base PMX file with a patch PMX file and output the result to a new PMX file:

```bash
python pmxmerge_cui.py --base base.pmx --patch patch.pmx --no_append DISPLAY --no_update BONE_SETTING MORPHS DISPLAY
```

Note: You need all .py files come with this distribution in the same directory as pmxmerge_cui.py to run this script.

### Arguments

| Argument          | Description                                             |
| ----------------- | ------------------------------------------------------- |
| `--help`, `-h` | Show this help message and exit                          |
| `--base`, `-b`    | Path to the base PMX file to merge into (required)     |
| `--patch`, `-p`   | Path to the patch PMX file (required)                   |
| `--out`, `-o`     | Output PMX file path (Default: result.pmx). Relative to the base PMX file's directory. |
| `--no_append`, `-a` | Comma-separated list of items to not append (any of `MORPHS PHYSICS DISPLAY`) |
| `--no_update`, `-u` | Comma-separated list of items to not update (any of `BONE_LOC BONE_SETTING MAT_SETTING MORPHS PHYSICS DISPLAY`) |
| `--version`, `-v` | Show the version of PMXMerge and exit                   |

* All features will be appended/updated by default.

## Notes

* Duplicate/Empty element names (bones, materials, morphs, rigid bodies and joints) in each of base and patch models are **not allowed**. Please fix them before merging.
* Orphan vertices (vertices not referenced by any face) will be removed from the output PMX file.
* Only supports PMX version 2.0.

## Disclaimer

This tool is provided "as is" without any warranty of any kind, either expressed or implied. Use it at your own risk. The author is not responsible for any damages or losses resulting from the use of this tool.

## License

GPL-3.0-or-later
© 2025 Kafuji Sato

## Changelog

* 2025/06/04: V1.1.2
  * Fixed: Bone/Vertex/UV morph was broken if the patch model has different type, same name morph with the base model.
    * In this case, the script will now replace the morph instead of merging it.
  * Slightly changed handling of textures in pypmx.py for more convenient usage.
  * Changed Bone update options: Removed BONE, added following:
    * BONE_LOC (Location and Display)
    * BONE_SETTING (Parent, Transform Order, Add Transform, IK, etc).
  * Changed executable build tool from Pyinstaller to Nuitka.
  * Added build.ps1 for building the executable with Nuitka.

* 2025/06/03: V1.1.1
  * Fixed issue where textures were lost in output PMX file.
  * Renamed `pmx.py` to `pypmx.py` to avoid confusion with the original PMX library.
  * Added savetest.py for debugging purposes to load/save PMX files without errors.
  * Stable release with no known issues.

* 2025/06/02: V1.1.0
  * Completely rewritten core logic to be more modular and maintainable.
  * Added support for merging display groups.
  * Options revamped to allow more control over what gets appended or updated.
  * Fixed issue where material morphs were not handled correctly.

* 2025/05/30: V1.0.0
  * Initial release with basic merging functionality.
