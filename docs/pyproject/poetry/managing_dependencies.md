Managing dependencies

Poetry supports specifying main dependencies in the project.dependencies section of your pyproject.toml according to PEP 621. For legacy reasons and to define additional information that are only used by Poetry the tool.poetry.dependencies sections can be used.

See Dependency specification for more information.
Dependency groups

Poetry provides a way to organize your dependencies by groups.

The dependencies declared in project.dependencies respectively tool.poetry.dependencies are part of an implicit main group. Those dependencies are required by your project during runtime.

Beside the main dependencies, you might have dependencies that are only needed to test your project or to build the documentation.

To declare a new dependency group, use a tool.poetry.group.<group> section where <group> is the name of your dependency group (for instance, test):

[tool.poetry.group.test.dependencies]
pytest = "^6.0.0"
pytest-mock = "*"

All dependencies must be compatible with each other across groups since they will be resolved regardless of whether they are required for installation or not (see Installing group dependencies).

Think of dependency groups as labels associated with your dependencies: they don’t have any bearings on whether their dependencies will be resolved and installed by default, they are simply a way to organize the dependencies logically.

Dependency groups, other than the implicit main group, must only contain dependencies you need in your development process. Installing them is only possible by using Poetry.

To declare a set of dependencies, which add additional functionality to the project during runtime, use extras instead. Extras can be installed by the end user using pip.
Optional groups

A dependency group can be declared as optional. This makes sense when you have a group of dependencies that are only required in a particular environment or for a specific purpose.

[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs = "*"

Optional groups can be installed in addition to the default dependencies by using the --with option of the install command.

poetry install --with docs

Optional group dependencies will still be resolved alongside other dependencies, so special care should be taken to ensure they are compatible with each other.
Adding a dependency to a group

The add command is the preferred way to add dependencies to a group. This is done by using the --group (-G) option.

poetry add pytest --group test

If the group does not already exist, it will be created automatically.
Installing group dependencies

By default, dependencies across all non-optional groups will be installed when executing poetry install.
The default set of dependencies for a project includes the implicit main group as well as all groups that are not explicitly marked as an optional group.

You can exclude one or more groups with the --without option:

poetry install --without test,docs

You can also opt in optional groups by using the --with option:

poetry install --with docs

When used together, --without takes precedence over --with. For example, the following command will only install the dependencies specified in the optional test group.

poetry install --with test,docs --without docs

Finally, in some case you might want to install only specific groups of dependencies without installing the default set of dependencies. For that purpose, you can use the --only option.

poetry install --only docs

If you only want to install the project’s runtime dependencies, you can do so with the --only main notation:

poetry install --only main

If you want to install the project root, and no other dependencies, you can use the --only-root option.

poetry install --only-root

Removing dependencies from a group

The remove command supports a --group option to remove packages from a specific group:

poetry remove mkdocs --group docs

Synchronizing dependencies

Poetry supports what’s called dependency synchronization. Dependency synchronization ensures that the locked dependencies in the poetry.lock file are the only ones present in the environment, removing anything that’s not necessary.

This is done by using the sync command:

poetry sync

The sync command can be combined with any dependency groups related options to synchronize the environment with specific groups. Note that extras are separate. Any extras not selected for install are always removed.

poetry sync --without dev
poetry sync --with docs
poetry sync --only dev

Layering optional groups

When using the install command without the --sync option, you can install any subset of optional groups without removing those that are already installed. This is very useful, for example, in multi-stage Docker builds, where you run poetry install multiple times in different build stages.