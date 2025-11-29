# blender-addon-dev-template-loader

A tiny helper that fetches the Blender add-on development template from the
[unclepomedev/blender-addon-dev-template](https://github.com/unclepomedev/blender-addon-dev-template)
repository and initializes the current working directory with your add-on name.

## Usage

Assuming you have uv installed, run the following commands (recommended in an empty directory):

```bash
uvx --from "git+https://github.com/unclepomedev/blender-addon-dev-template-loader" blender-init my-awesome-addon
```

Replace `my-awesome-addon` with the name of your add-on.

### Options

- `-m "Name"` / `--maintainer "Name"`: Specify the maintainer name. This replaces `MAINTAINER_STRING` in `blender_manifest.toml`.
- `-f` / `--force`: Overwrite existing files if they exist.

Notes:
- The template files are created directly in the current directory.
- If any files or directories that would be created already exist, the command aborts without overwriting (unless `-f` is used).

For macOS users: for the "fastest" way to create a project, add the following function to your ~/.zshrc.

```zsh
function bini() {
    local dirname="$1"

    if [[ -z "$dirname" ]]; then
        echo "Usage: bini <dirname>"
        return 1
    fi

    echo "🚀 Creating Blender Addon project: $dirname"
    mkdir -p "$dirname" && cd "$dirname" || return 1
    uvx --from "git+https://github.com/unclepomedev/blender-addon-dev-template-loader" blender-init "$dirname"
    echo "📦 Installing dependencies..."
    uv sync
    source .venv/bin/activate
    echo "✨ Ready! You are in '$dirname' with virtualenv activated."
}
```
