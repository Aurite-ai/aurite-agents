"""Generate the files for the documentation."""

import mkdocs_gen_files

# List of files to copy from the project root to the docs directory
root_files = [
    "CHANGELOG.md",
    "SECURITY.md",
]

for file_path in root_files:
    with open(file_path, "r") as f:
        content = f.read()
    mkdocs_gen_files.set_edit_path(file_path, file_path)
    with mkdocs_gen_files.open(file_path, "w") as f:
        f.write(content)
