import argparse
from typing import Dict, Tuple

import pmxmerge

VERSION = "1.1.0"  # Version of the PMX Merge Tool

# Default options for merging PMX models
options_default: Dict[str, Tuple[str, ...]] = {
    "append": ('MORPH', 'PHYSICS', 'DISPLAY' ), # Specify which features in the patch model to append to the base model. Bones and materials are always appended.
    "update": ('BONE', 'MAT_SETTING', 'MORPH', 'PHYSICS', 'DISPLAY'), # Specify which features in the base model to update with the patch model
}

if __name__ == "__main__":
    # Usage: python pmxmerge.py --base <base.pmx> --patch <patch.pmx> --out <output.pmx>
    # Alias: python pmxmerge.py -b <base.pmx> -p <patch.pmx> -o <output.pmx>
    # Optional arguments:
    # --no_append <feature> : Do not append the specified feature from the patch model to the base model.
    # --no_update <feature> : Do not update the specified feature in the base model with the patch model.

    parser = argparse.ArgumentParser(description="Merge PMX models by patching geometry and morphs.")
    parser.add_argument("--base", "-b", type=str, default="",
                        help="Base PMX file path to merge into. Must be specified.")
    
    parser.add_argument("--patch", "-p", type=str, default="",
                        help="Patch PMX file path to merge. Must be specified.")
    parser.add_argument("--out", "-o", type=str, default="result.pmx",
                        help="Output PMX file path (Default: 'result.pmx'). Relative to the base PMX file's directory.")

    parser.add_argument("--no_append", "-na", type=str, nargs='*', default=None,
                        help="Features to not append from the patch model to the base model. Any of: " + ", ".join(options_default["append"]))

    parser.add_argument("--no_update", "-nu", type=str, nargs='*', default=None,
                        help="Features to not update in the base model with the patch model. Any of: " + ", ".join(options_default["update"]))

    parser.add_argument("--version", action='version', version=f'PMX Merge Tool {VERSION}',)

    args = parser.parse_args()

    # Validate input arguments
    if args.no_append is None:
        args.no_append = []

    if args.no_update is None:
        args.no_update = []

    path_base = args.base
    path_patch = args.patch
    path_out = args.out

    if not path_base or not path_patch:
        print("Error: Both base and patch PMX files must be specified.")
        exit()

    if path_base == path_patch:
        print("Error: Base and patch files cannot be the same.")
        exit()

    if not path_out:
        path_out = path_base

    # Build options for merging, the function expects positive lists, so we need to invert the logic
    append = options_default["append"]
    if args.no_append:
        append = [feature for feature in options_default["append"] if feature not in args.no_append]
    update = options_default["update"]
    if args.no_update:
        update = [feature for feature in options_default["update"] if feature not in args.no_update]

    # if both append and update are empty, exit
    if not append and not update:
        print("Info: No features to append or update. Exiting without merging.")
        exit()

    ret, msg = pmxmerge.merge_pmx_files(path_base, path_patch, path_out, append=append, update=update)
    if not ret:
        print(f"Error: {msg}")
        exit()
    else:
        print(f"PMX files merged successfully. Output saved to: {path_out}")

# End of pmxmerge.py
