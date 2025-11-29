import argparse
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

TEMPLATE_REPO = "unclepomedev/blender-addon-dev-template"
ZIP_URL = f"https://codeload.github.com/{TEMPLATE_REPO}/zip/refs/heads/main"
PLACEHOLDER_TOKEN = "addon_hello_world"
MAINTAINER_PLACEHOLDER = "MAINTAINER_STRING"
EXCLUDE_FILES = {
    "README.md",
}


def _download_template_zip(dest_path: Path) -> None:
    """Download the template repository zip to dest_path.
    Uses only the main branch archive URL. Raises RuntimeError on failure.
    """
    try:
        with urllib.request.urlopen(ZIP_URL) as resp:
            data = resp.read()
        dest_path.write_bytes(data)
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to download template from {TEMPLATE_REPO}: {e}") from e


def _is_binary_bytes(sample: bytes) -> bool:
    """Heuristic to detect binary blobs.

    - If NUL byte present, treat as binary.
    - If text decoding (utf-8) fails on small sample, treat as binary.
    """
    if b"\x00" in sample:
        return True
    try:
        sample.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def _iter_single_top_level_dir(root: Path):
    """Return the single top-level directory inside root (as produced by GitHub zips).

    Raises if structure is unexpected.
    """
    entries = [p for p in root.iterdir() if p.is_dir()]
    if len(entries) != 1:
        raise RuntimeError("Unexpected zip content: expected a single top-level directory")
    return entries[0]


def _process_tree_replace(src_root: Path, dst_root: Path, replacement: str, maintainer: str | None = None) -> None:
    """Copy the tree from src_root to dst_root, replacing PLACEHOLDER_TOKEN.

    - Replace occurrences of PLACEHOLDER_TOKEN in directory and file names.
    - Replace occurrences of PLACEHOLDER_TOKEN in text file contents (UTF-8). Binary files are copied as-is.
    - If maintainer is provided, replace occurrences of MAINTAINER_PLACEHOLDER in text file contents.
    - Perform bottom-up renames by constructing the destination path with replacements applied to each part.
    """
    for src_path in sorted(src_root.rglob("*")):
        rel_path_obj = src_path.relative_to(src_root)
        if str(rel_path_obj) in EXCLUDE_FILES:
            continue

        rel_parts = [part.replace(PLACEHOLDER_TOKEN, replacement) for part in rel_path_obj.parts]
        dst_path = dst_root.joinpath(*rel_parts)

        if src_path.is_dir():
            dst_path.mkdir(parents=True, exist_ok=True)
            continue

        dst_path.parent.mkdir(parents=True, exist_ok=True)

        raw = src_path.read_bytes()
        if _is_binary_bytes(raw[:4096]):
            dst_path.write_bytes(raw)
        else:
            # Try to decode as UTF-8. If it fails, treat as binary.
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                dst_path.write_bytes(raw)
            else:
                replaced = text.replace(PLACEHOLDER_TOKEN, replacement)
                if maintainer:
                    replaced = replaced.replace(MAINTAINER_PLACEHOLDER, maintainer)
                dst_path.write_text(replaced, encoding="utf-8")

        try:
            shutil.copymode(src_path, dst_path)
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI.

    This will:
    1) Download the Blender add-on development template repository as a zip.
    2) Extract it to a temporary directory.
    3) Replace occurrences of `addon_hello_world` in names and text contents with the provided add-on name.
    4) Write the processed template files into the current working directory (not into a subdirectory).
    """
    parser = argparse.ArgumentParser(
        prog="blender-init",
        description=(
            "Fetch the Blender add-on development template and initialize it with your add-on name "
            f"(source: https://github.com/{TEMPLATE_REPO})."
        ),
    )
    parser.add_argument(
        "addon_name",
        help=f"Your add-on name. All occurrences of '{PLACEHOLDER_TOKEN}' will be replaced with this value.",
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing files if they exist."
    )
    parser.add_argument(
        "-m", "--maintainer",
        help=f"Maintainer name. Replaces '{MAINTAINER_PLACEHOLDER}'.",
    )
    args = parser.parse_args(argv)

    addon_name: str = args.addon_name
    force_overwrite: bool = args.force
    maintainer: str | None = args.maintainer
    dest_root = Path.cwd()

    with tempfile.TemporaryDirectory(prefix="bl_addon_tpl_") as tmpdir:
        tmpdir_p = Path(tmpdir)
        zip_path = tmpdir_p / "template.zip"

        print("Downloading template...", flush=True)
        try:
            _download_template_zip(zip_path)
        except Exception as e:
            print(f"Failed to download template: {e}", file=sys.stderr)
            return 3

        extract_root = tmpdir_p / "unzipped"
        extract_root.mkdir(parents=True, exist_ok=True)
        print("Extracting template...", flush=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_root)

        try:
            src_root = _iter_single_top_level_dir(extract_root)
        except Exception as e:
            print(f"Unexpected template layout: {e}", file=sys.stderr)
            return 4

        processed_root = tmpdir_p / "processed"
        print("Applying replacements...", flush=True)
        _process_tree_replace(src_root, processed_root, addon_name, maintainer=maintainer)

        processed_items = list(processed_root.rglob("*"))
        if not processed_items:
            print("Error: No files processed.", file=sys.stderr)
            return 6

        # Pre-flight collision check: ensure we won't overwrite existing files/dirs
        print("Checking for conflicts in the current directory...", flush=True)
        conflicts: list[Path] = []
        for src_path in processed_items:
            rel = src_path.relative_to(processed_root)
            dest_path = dest_root / rel
            if dest_path.exists():
                conflicts.append(rel)

        if conflicts and not force_overwrite:
            print("Error: the following paths already exist in the current directory and would be overwritten:",
                  file=sys.stderr)
            for p in sorted(conflicts):
                print(f"  {p}", file=sys.stderr)
            print("Aborting. Please run in an empty directory or remove the conflicting files.", file=sys.stderr)
            return 5

        for dir_path in sorted([p for p in processed_root.rglob("*") if p.is_dir()]):
            (dest_root / dir_path.relative_to(processed_root)).mkdir(parents=True, exist_ok=True)

        for file_path in sorted([p for p in processed_root.rglob("*") if p.is_file()]):
            dst = dest_root / file_path.relative_to(processed_root)
            if force_overwrite and dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                elif dst.is_file():
                    dst.unlink()
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dst)

        readme_path = dest_root / "README.md"
        if not readme_path.exists() or force_overwrite:
            print("Generating fresh README.md...", flush=True)
            readme_content = f"# {addon_name}\n\nDescription of {addon_name}."
            readme_path.write_text(readme_content, encoding="utf-8")

    print("Done.")
    print("Your add-on template has been written into the current directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
