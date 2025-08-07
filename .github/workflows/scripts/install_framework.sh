#!/bin/bash
set -e

echo "=== Installing Aurite Framework ==="

# Upgrade pip
python -m pip install --upgrade pip

# Install the current source code being released (not published package)
echo "Installing framework from source..."
pip install -e .

echo "✅ Framework installation completed successfully"
