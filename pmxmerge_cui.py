import argparse
from . import pmxmerge_core

if __name__ == "__main__":
    # Usage: python pmxmerge.py --base <base.pmx> --patch <patch.pmx> --out <output.pmx>
    # Alias: python pmxmerge.py -b <base.pmx> -p <patch.pmx> -o <output.pmx>
    # Optional arguments:
    # --replace_bones: Replace bone settings with the patch model's bone settings
    # --merge_physics: Merge physics features (Rigid Bodies and Joints) from the patch model into the base model
    # --merge_displaysettings: Merge display settings from the patch model into the base model

    parser = argparse.ArgumentParser(description="Merge PMX models by patching geometry and morphs.")
    parser.add_argument("--base", "-b", type=str, default="",
                        help="Base PMX file path to merge into. Must be specified.")
    
    parser.add_argument("--patch", "-p", type=str, default="",
                        help="Patch PMX file path to merge. Must be specified.")
    parser.add_argument("--out", "-o", type=str, default="",
                        help="Output PMX file path (overwrite the base PMX file if not specified).")

    parser.add_argument("--replace_bones", action="store_true",
                        help="Replace bone settings with the patch model's bone settings.")

    parser.add_argument("--merge_physics", action="store_true",
                        help="Merge physics features (Rigid Bodies and Joints) from the patch model into the base model.")
    
    parser.add_argument("--merge_displaysettings", action="store_true",
                        help="Merge display settings from the patch model into the base model.")

    args = parser.parse_args()
    path_base = args.base

    path_patch = args.patch
    path_out = args.out

    if not path_base or not path_patch:
        print("Error: Both --base and --patch arguments must be specified.")
        print("Usage: python pmxmerge.py --base <base.pmx> --patch <patch.pmx> --out <output.pmx>")
        exit()

    if path_base == path_patch:
        print("Error: Base and patch files cannot be the same.")
        exit()

    if not path_out:
        path_out = path_base

    ret, msg = pmxmerge_core.merge_pmx_files(path_base, path_patch, path_out,
                                              replace_bones=args.replace_bones,
                                              merge_phys=args.merge_physics,
                                              merge_disp=args.merge_displaysettings)
    if not ret:
        print(f"Error: {msg}")
        exit()
    else:
        print(f"PMX files merged successfully. Output saved to: {path_out}")

# End of pmxmerge.py
