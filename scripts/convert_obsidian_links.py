import os
import re


def convert_obsidian_links(directory):
    """
    Recursively finds all Markdown files in a directory and converts
    Obsidian-style [[file|text]] links to standard [text](file) links.
    """
    obsidian_link_regex = re.compile(r"\[\[([^|\]]+)\|([^\]]+)\]\]")

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)

                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Perform the replacement
                new_content = obsidian_link_regex.sub(r"[\2](\1)", content)

                if new_content != content:
                    print(f"Updating links in: {filepath}")
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)


if __name__ == "__main__":
    docs_directory = "docs"
    print(f"Starting conversion of Obsidian links in '{docs_directory}' directory...")
    convert_obsidian_links(docs_directory)
    print("Conversion complete.")
