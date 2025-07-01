Repositories

Poetry supports the use of PyPI and private repositories for discovery of packages as well as for publishing your projects.

By default, Poetry is configured to use the PyPI repository, for package installation and publishing.

So, when you add dependencies to your project, Poetry will assume they are available on PyPI.

This represents most cases and will likely be enough for most users.
Private Repository Example
Installing from private package sources

By default, Poetry discovers and installs packages from PyPI. But, you want to install a dependency to your project for a simple API repository? Let’s do it.

First, configure the package source as a supplemental (or explicit) package source to your project.

poetry source add --priority=supplemental foo https://pypi.example.org/simple/

Then, assuming the repository requires authentication, configure credentials for it.

poetry config http-basic.foo <username> <password>

Depending on your system configuration, credentials might be saved in your command line history. Many shells do not save commands to history when they are prefixed by a space character. For more information, please refer to your shell’s documentation.

If you would like to provide the password interactively, you can simply omit <password> in your command. And Poetry will prompt you to enter the credential manually.

poetry config http-basic.foo <username>

Once this is done, you can add dependencies to your project from this source.

poetry add --source foo private-package

Publishing to a private repository

Great, now all that is left is to publish your package. Assuming you’d want to share it privately with your team, you can configure the Upload API endpoint for your publishable repository.

poetry config repositories.foo https://pypi.example.org/legacy/

If you need to use a different credential for your package source, then it is recommended to use a different name for your publishing repository.

poetry config repositories.foo-pub https://pypi.example.org/legacy/
poetry config http-basic.foo-pub <username> <password>

When configuring a repository using environment variables, note that correct suffixes need to be used.

export POETRY_REPOSITORIES_FOO_URL=https://pypi.example.org/legacy/
export POETRY_HTTP_BASIC_FOO_USERNAME=<username>
export POETRY_HTTP_BASIC_FOO_PASSWORD=<password>

Now, all that is left is to build and publish your project using the publish.

poetry publish --build --repository foo-pub

Package Sources

By default, if you have not configured any primary source, Poetry is configured to use the Python ecosystem’s canonical package index PyPI. You can alter this behavior and exclusively look up packages only from the configured package sources by adding at least one primary source.
Except for the implicitly configured source for PyPI named PyPI, package sources are local to a project and must be configured within the project’s pyproject.toml file. This is not the same configuration used when publishing a package.

Package sources are a Poetry-specific feature and not included in core metadata produced by the poetry-core build backend.

Consequently, when a Poetry project is e.g., installed using Pip (as a normal package or in editable mode), package sources will be ignored and the dependencies in question downloaded from PyPI by default.
Project Configuration

These package sources may be managed using the source command for your project.

poetry source add foo https://foo.bar/simple/

If your package source requires credentials or certificates, please refer to the relevant sections below.

This will generate the following configuration snippet in your pyproject.toml file.

[[tool.poetry.source]]
name = "foo"
url = "https://foo.bar/simple/"
priority = "primary"

If priority is undefined, the source is considered a primary source, which disables the implicit PyPI source and takes precedence over supplemental sources.

Package sources are considered in the following order:

    primary sources or implicit PyPI (if there are no primary sources),
    supplemental sources.

Explicit sources are considered only for packages that explicitly indicate their source.

Within each priority class, package sources are considered in order of appearance in pyproject.toml.
Primary Package Sources

All primary package sources are searched for each dependency without a source constraint. If you configure at least one primary source, the implicit PyPI source is disabled.

poetry source add --priority=primary foo https://foo.bar/simple/

Sources without a priority are considered primary sources, too.

poetry source add foo https://foo.bar/simple/

The implicit PyPI source is disabled automatically if at least one primary source is configured. If you want to use PyPI in addition to a primary source, configure it explicitly with a certain priority, e.g.

poetry source add --priority=primary PyPI

This way, the priority of PyPI can be set in a fine-granular way.

The equivalent specification in pyproject.toml is:

[[tool.poetry.source]]
name = "pypi"
priority = "primary"

Omit the url when specifying PyPI explicitly. Because PyPI is internally configured with Poetry, the PyPI repository cannot be configured with a given URL. Remember, you can always use poetry check to ensure the validity of the pyproject.toml file.
Supplemental Package Sources

Introduced in 1.5.0

Package sources configured as supplemental are only searched if no other (higher-priority) source yields a compatible package distribution. This is particularly convenient if the response time of the source is high and relatively few package distributions are to be fetched from this source.

You can configure a package source as a supplemental source with priority = "supplemental" in your package source configuration.

poetry source add --priority=supplemental foo https://foo.bar/simple/

There can be more than one supplemental package source.
Take into account that someone could publish a new package to a primary source which matches a package in your supplemental source. They could coincidentally or intentionally replace your dependency with something you did not expect.
Explicit Package Sources

Introduced in 1.5.0

If package sources are configured as explicit, these sources are only searched when a package configuration explicitly indicates that it should be found on this package source.

You can configure a package source as an explicit source with priority = "explicit" in your package source configuration.

poetry source add --priority=explicit foo https://foo.bar/simple/

There can be more than one explicit package source.

A real-world example where an explicit package source is useful, is for PyTorch GPU packages.

poetry source add --priority=explicit pytorch-gpu-src https://download.pytorch.org/whl/cu118
poetry add --source pytorch-gpu-src torch torchvision torchaudio

Package Source Constraint

All package sources (including possibly supplemental sources) will be searched during the package lookup process. These network requests will occur for all primary sources, regardless of if the package is found at one or more sources, and all supplemental sources until the package is found.

In order to limit the search for a specific package to a particular package repository, you can specify the source explicitly.

poetry add --source internal-pypi httpx

This results in the following configuration in pyproject.toml:

[tool.poetry.dependencies]
...
httpx = { version = "^0.22", source = "internal-pypi" }

[[tool.poetry.source]]
name = "internal-pypi"
url = ...
priority = ...

A repository that is configured to be the only source for retrieving a certain package can itself have any priority. In particular, it does not need to have priority "explicit". If a repository is configured to be the source of a package, it will be the only source that is considered for that package and the repository priority will have no effect on the resolution.

Package source keys are not inherited by their dependencies. In particular, if package-A is configured to be found in source = internal-pypi, and package-A depends on package-B that is also to be found on internal-pypi, then package-B needs to be configured as such in pyproject.toml. The easiest way to achieve this is to add package-B with a wildcard constraint:

poetry add --source internal-pypi package-B@*

This will ensure that package-B is searched only in the internal-pypi package source. The version constraints on package-B are derived from package-A (and other client packages), as usual.

If you want to avoid additional main dependencies, you can add package-B to a dedicated dependency group:

poetry add --group explicit --source internal-pypi package-B@*

Package source constraints are strongly suggested for all packages that are expected to be provided only by one specific source to avoid dependency confusion attacks.
Supported Package Sources
Python Package Index (PyPI)

Poetry interacts with PyPI via its JSON API. This is used to retrieve a requested package’s versions, metadata, files, etc.
If the package’s published metadata is invalid, Poetry will download the available bdist/sdist to inspect it locally to identify the relevant metadata.

If you want to explicitly select a package from PyPI you can use the --source option with the add command, like shown below.

poetry add --source pypi httpx@^0.22.0

This will generate the following configuration snippet in your pyproject.toml file.

httpx = {version = "^0.22.0", source = "pypi"}

The implicit PyPI source will be disabled and not used for any packages if at least one primary source is configured.
Simple API Repository

Poetry can fetch and install package dependencies from public or private custom repositories that implement the simple repository API as described in PEP 503.
When using sources that distribute large wheels without providing file checksum in file URLs, Poetry will download each candidate wheel at least once in order to generate the checksum. This can manifest as long dependency resolution times when adding packages from this source.

These package sources may be configured via the following command in your project.

poetry source add testpypi https://test.pypi.org/simple/

Note the trailing /simple/. This is important when configuring PEP 503 compliant package sources.

In addition to PEP 503, Poetry can also handle simple API repositories that implement PEP 658 (Introduced in 1.2.0). This is helpful in reducing dependency resolution time for packages from these sources as Poetry can avoid having to download each candidate distribution, in order to determine associated metadata.

Why does Poetry insist on downloading all candidate distributions for all platforms when metadata is not available?

The need for this stems from the fact that Poetry’s lock file is platform-agnostic. This means, in order to resolve dependencies for a project, Poetry needs metadata for all platform-specific distributions. And when this metadata is not readily available, downloading the distribution and inspecting it locally is the only remaining option.
Single Page Link Source

Introduced in 1.2.0

Some projects choose to release their binary distributions via a single page link source that partially follows the structure of a package page in PEP 503.

These package sources may be configured via the following command in your project.

poetry source add jax https://storage.googleapis.com/jax-releases/jax_releases.html

All caveats regarding slower resolution times described for simple API repositories do apply here as well.
Publishable Repositories

Poetry treats repositories to which you publish packages as user-specific and not project-specific configuration unlike package sources. Poetry, today, only supports the Legacy Upload API when publishing your project.

These are configured using the config command, under the repositories key.

poetry config repositories.testpypi https://test.pypi.org/legacy/

Legacy Upload API URLs are typically different to the same one provided by the repository for the simple API. You’ll note that in the example of Test PyPI, both the host (test.pypi.org) as well as the path (/legacy) are different to its simple API (https://test.pypi.org/simple).
Configuring Credentials

If you want to store your credentials for a specific repository, you can do so easily:

poetry config http-basic.foo <username> <password>

If you do not specify the password, you will be prompted to write it.

To publish to PyPI, you can set your credentials for the repository named pypi.

Note that it is recommended to use API tokens when uploading packages to PyPI. Once you have created a new token, you can tell Poetry to use it:

poetry config pypi-token.pypi <my-token>

If you have configured testpypi as a Publishable Repository, the token can be set using

poetry config pypi-token.testpypi <your-token>

If you still want to use your username and password, you can do so with the following call to config.

poetry config http-basic.pypi <username> <password>

You can also specify the username and password when using the publish command with the --username and --password options.

If a system keyring is available and supported, the password is stored to and retrieved from the keyring. In the above example, the credential will be stored using the name poetry-repository-pypi. If access to keyring fails or is unsupported, this will fall back to writing the password to the auth.toml file along with the username.

Keyring support is enabled using the keyring library. For more information on supported backends refer to the library documentation.

If you do not want to use the keyring, you can tell Poetry to disable it and store the credentials in plaintext config files:

poetry config keyring.enabled false

Poetry will fall back to Pip style use of keyring so that backends like Microsoft’s artifacts-keyring get a chance to retrieve valid credentials. It will need to be properly installed into Poetry’s virtualenv, preferably by installing a plugin.

Alternatively, you can use environment variables to provide the credentials:

export POETRY_PYPI_TOKEN_FOO=my-token
export POETRY_HTTP_BASIC_FOO_USERNAME=<username>
export POETRY_HTTP_BASIC_FOO_PASSWORD=<password>

where FOO is the name of the repository in uppercase (e.g. PYPI). See Using environment variables for more information on how to configure Poetry with environment variables.

If your password starts with a dash (e.g., randomly generated tokens in a CI environment), it will be parsed as a command line option instead of a password. You can prevent this by adding double dashes to prevent any following argument from being parsed as an option.

poetry config -- http-basic.pypi myUsername -myPasswordStartingWithDash

In some cases like that of Gemfury repositories, it might be required to set an empty password. This is supported by Poetry.

poetry config http-basic.foo <TOKEN> ""

Note: Empty usernames are discouraged. However, Poetry will honor them if a password is configured without it. This is unfortunately commonplace practice, while not best practice, for private indices that use tokens. When a password is stored into the system keyring with an empty username, Poetry will use a literal __poetry_source_empty_username__ as the username to circumvent keyring#687.
Certificates
Custom certificate authority and mutual TLS authentication

Poetry supports repositories that are secured by a custom certificate authority as well as those that require certificate-based client authentication. The following will configure the “foo” repository to validate the repository’s certificate using a custom certificate authority and use a client certificate (note that these config variables do not both need to be set):

poetry config certificates.foo.cert /path/to/ca.pem
poetry config certificates.foo.client-cert /path/to/client.pem

The value of certificates.<repository>.cert can be set to false if certificate verification is required to be skipped. This is useful for cases where a package source with self-signed certificates is used.

poetry config certificates.foo.cert false

Disabling certificate verification is not recommended as it does not conform to security best practices.
Caches

Poetry employs multiple caches for package sources in order to improve user experience and avoid duplicate network requests.

The first level cache is a Cache-Control header-based cache for almost all HTTP requests.

Further, every HTTP backed package source caches metadata associated with a package once it is fetched or generated. Additionally, downloaded files (package distributions) are also cached.
Debugging Issues

If you encounter issues with package sources, one of the simplest steps you might take to debug an issue is rerunning your command with the --no-cache flag.

poetry --no-cache add pycowsay

If this solves your issue, you can consider clearing your cache using the cache command.

Alternatively, you could also consider enabling very verbose logging -vvv along with the --no-cache to see network requests being made in the logs.