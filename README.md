# blender-addon-dev-template-loader

A tiny helper that fetches the Blender add-on development template from the
[unclepomedev/blender-addon-dev-template](https://github.com/unclepomedev/blender-addon-dev-template)
repository and initializes the current working directory with your add-on name.

## Usage

Assuming you have uv installed, run the following commands (recommended in an empty directory):

```bash
uvx --from "git+https://github.com/unclepomedev/blender-addon-dev-template-loader" blender-init "$dirname"
```

Replace `my-awesome-addon` with the name of your add-on.

Notes:
- The template files are created directly in the current directory.
- If any files or directories that would be created already exist, the command aborts without overwriting.
