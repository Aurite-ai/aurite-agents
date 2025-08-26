# Database Integration Guide

The Aurite framework provides an optional database backend for managing component configurations and session history. This guide explains how to set up and use this feature.

## Overview

By default, Aurite uses a file-based system for managing configurations (agents, LLMs, etc.). While this is convenient for local development, a database backend is recommended for production environments, multi-user setups, and when running Aurite as a persistent, headless service.

When database mode is enabled, the `ConfigManager` loads all component configurations from the database into memory on startup. All subsequent CRUD (Create, Read, Update, Delete) operations are then performed against the database, ensuring that the in-memory index is kept in sync.

## Enabling Database Mode

To enable the database backend, set the following environment variable in your .env file:

```bash
AURITE_ENABLE_DB=true
```

When this variable is set to `true`, the framework will connect to the database specified by the configuration variables below. If it is `false` or not set, the framework will fall back to the default file-based system.

## Database Configuration

The following environment variables are used to configure the database connection. These should be set in your `.env` file or as environment variables in your deployment environment.

| Variable             | Description                                              | Default    |
| -------------------- | -------------------------------------------------------- | ---------- |
| `AURITE_DB_HOST`     | The hostname or IP address of your PostgreSQL server.    | `postgres` |
| `AURITE_DB_PORT`     | The port your PostgreSQL server is running on.           | `5432`     |
| `AURITE_DB_USER`     | The username for connecting to the database.             |            |
| `AURITE_DB_PASSWORD` | The password for the database user.                      |            |
| `AURITE_DB_NAME`     | The name of the database to use for storing Aurite data. |            |

## Exporting Configurations to the Database

Before you can use the database backend, you need to populate it with your existing file-based configurations. This is done using the `aurite export` command.

This command will:

1.  Read all your component configurations from the local file system.
2.  Connect to the database using the configured credentials.
3.  Create the necessary tables if they don't exist.
4.  Upload all your component configurations to the database.

To run the export, execute the following command in your terminal:

```bash
aurite export
```

This command should be run whenever you make changes to your local configuration files and want to update the database.

## CRUD Operations

When `AURITE_ENABLE_DB` is set to `true`, all CRUD operations performed through the API or directly via the `ConfigManager` will automatically use the database as the backend. This means that any new components you create, update, or delete will be persisted in the database, not the file system.

## Force Refresh

Ensure

```bash
AURITE_CONFIG_FORCE_REFRESH=true
```

is set to `false` to avoid loading the database configurations for every operation (or set this to true if you want to update the database manually and have the changes immediately update Aurite).
