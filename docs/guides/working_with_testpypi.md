# How to Work with TestPyPI

This guide provides a quick walkthrough on how to configure your environment to upload Python packages to TestPyPI and how to perform the upload.

## 1. Prerequisites

*   You have an account on [TestPyPI](https://test.pypi.org/).
*   You have generated an API token for your account.
*   You have `build` and `twine` installed (`pip install build twine`).

## 2. Configure Your `.pypirc` File

To streamline the upload process and avoid entering your credentials every time, you can configure a `.pypirc` file in your home directory.

1.  **Create or Edit the File:**
    Open (or create) the file `~/.pypirc`. The `~` refers to your home directory.

2.  **Add Repository Configurations:**
    Add the following content to the file. This configures aliases for both `testpypi` and the main `pypi` repository.

    ```ini
    [testpypi]
    repository = https://test.pypi.org/legacy/
    username = __token__
    password = pypi-YOUR_TESTPYPI_API_TOKEN

    [pypi]
    repository = https://upload.pypi.org/legacy/
    username = __token__
    password = pypi-YOUR_PYPI_API_TOKEN
    ```

3.  **Save the File:**
    *   The username must be the literal string `__token__`. Do not change it.
    *   Replace `pypi-YOUR_TESTPYPI_API_TOKEN` with your token from TestPyPI.
    *   Replace `pypi-YOUR_PYPI_API_TOKEN` with your token from the main PyPI repository.
    *   **Note on Formatting:** The section headers (`[testpypi]`, `[pypi]`) should not have any leading spaces. The indentation of the `repository`, `username`, and `password` lines is optional and used for readability.

## 3. Build Your Package

Before uploading, you need to build the distribution files (a source archive and a wheel).

1.  **Navigate to Project Root:**
    Open your terminal and navigate to the root directory of your Python project (the one containing `pyproject.toml` or `setup.py`).

2.  **Run the Build Command:**
    Execute the following command. This will create a `dist/` directory containing your package files.

    ```bash
    python -m build
    ```

## 4. Upload to a Repository

With your package built and your `.pypirc` file configured, you can now upload the distribution files to the desired repository.

### Uploading to TestPyPI

Use the `testpypi` repository alias to upload a test version. This is highly recommended before publishing to the main repository.

```bash
twine upload --repository testpypi dist/*
```

### Uploading to PyPI (Production)

Once you have verified your package on TestPyPI, you can upload it to the main PyPI repository for public release.

```bash
twine upload dist/*
```

**Note:** If you only have the `pypi` section in your `.pypirc` file, `twine upload` will use it by default. If you have multiple sections, you can explicitly specify the repository with `twine upload --repository pypi dist/*`.

## 5. Installing a Package from TestPyPI

After uploading your package to TestPyPI, you can install it to a virtual environment to ensure it works correctly.

### Basic Installation

To install a package exclusively from TestPyPI, use the `--index-url` flag.

```bash
pip install --index-url https://test.pypi.org/simple/ your-package-name
```

### Installation with Dependencies on PyPI

If your package has dependencies that are on the main PyPI repository, you must also provide an `--extra-index-url` to the standard PyPI index. This tells `pip` to look on TestPyPI first, and then check PyPI for any packages it can't find.

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple your-package-name
```

Replace `your-package-name` with the name of the package you want to install.
