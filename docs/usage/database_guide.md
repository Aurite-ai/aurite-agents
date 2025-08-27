# Database Integration Guide

The Aurite framework provides an optional database backend for managing component configurations and session history. This guide explains how to set up and use this feature with support for both SQLite (default) and PostgreSQL databases.

## Overview

By default, Aurite uses a file-based system for managing configurations (agents, LLMs, etc.). When database mode is enabled, you can choose between:

- **SQLite** (default): Zero-configuration, file-based database perfect for local development and single-user deployments
- **PostgreSQL**: Full-featured database for production environments, multi-user setups, and distributed deployments

When database mode is enabled, the `ConfigManager` loads all component configurations from the database into memory on startup. All subsequent CRUD (Create, Read, Update, Delete) operations are then performed against the database, ensuring that the in-memory index is kept in sync.

## Enabling Database Mode

To enable the database backend, set the following environment variable in your .env file:

```bash
AURITE_ENABLE_DB=true
```

When this variable is set to `true`, the framework will connect to the database specified by the configuration variables below. If it is `false` or not set, the framework will fall back to the default file-based system.

## Database Type Selection

Choose your database type with the `AURITE_DB_TYPE` environment variable:

```bash
# For SQLite (default, zero-configuration)
AURITE_DB_TYPE=sqlite

# For PostgreSQL (production-ready, multi-user)
AURITE_DB_TYPE=postgresql
```

## SQLite Configuration

SQLite is the default database type and requires minimal configuration:

| Variable         | Description                      | Default                |
| ---------------- | -------------------------------- | ---------------------- |
| `AURITE_DB_PATH` | Path to the SQLite database file | `.aurite_db/aurite.db` |

Example `.env` configuration for SQLite:

```bash
AURITE_ENABLE_DB=true
AURITE_DB_TYPE=sqlite
AURITE_DB_PATH=.aurite_db/aurite.db  # Optional, this is the default
```

### SQLite Advantages

- **Zero configuration**: Works out of the box
- **Portable**: Database is a single file
- **No external dependencies**: No separate database server needed
- **Perfect for development**: Quick setup and teardown
- **Lightweight**: Minimal resource usage

### SQLite Limitations

- Single-user write access (multiple readers OK)
- Limited concurrent connections
- Not suitable for distributed deployments

## PostgreSQL Configuration

PostgreSQL provides a robust, production-ready database solution:

| Variable             | Description                                             | Default          |
| -------------------- | ------------------------------------------------------- | ---------------- |
| `AURITE_DB_HOST`     | The hostname or IP address of your PostgreSQL server    | `localhost`      |
| `AURITE_DB_PORT`     | The port your PostgreSQL server is running on           | `5432`           |
| `AURITE_DB_USER`     | The username for connecting to the database             | (required)       |
| `AURITE_DB_PASSWORD` | The password for the database user                      | (required)       |
| `AURITE_DB_NAME`     | The name of the database to use for storing Aurite data | `aurite_storage` |

Example `.env` configuration for PostgreSQL:

```bash
AURITE_ENABLE_DB=true
AURITE_DB_TYPE=postgresql
AURITE_DB_HOST=localhost
AURITE_DB_PORT=5432
AURITE_DB_USER=postgres_user
AURITE_DB_PASSWORD=postgres_password
AURITE_DB_NAME=aurite_storage
```

### PostgreSQL Advantages

- **Multi-user support**: Handles concurrent access efficiently
- **Scalability**: Suitable for large-scale deployments
- **Advanced features**: Full SQL support, transactions, replication
- **Production-ready**: Battle-tested for enterprise use
- **Distributed deployments**: Can be accessed from multiple servers

### PostgreSQL Requirements

- PostgreSQL server (version 12 or higher recommended)
- Database user with CREATE TABLE permissions
- Network access to the database server

### Local PostgreSQL Setup

If PostgreSQL is not installed on your system, you can install it (on Linux, Mac, and WSL) using:

```bash
sudo apt-get update && sudo apt-get install -y postgresql postgresql-contrib
```

To create a database user and database for Aurite, run:

```bash
sudo -u postgres psql -c "CREATE USER postgres_user WITH PASSWORD 'postgres_password';"
sudo -u postgres psql -c "CREATE DATABASE aurite_storage OWNER postgres_user;"
```

You can ignore this error:

```
could not change directory to "/path/to/aurite-agents": Permission denied
```

This will create a user named `postgres_user` with the password `postgres_password`, and a database named `aurite_storage` owned by that user.

## Exporting Configurations to the Database

If you have existing file-based configurations that you want to load into the database, use the `aurite export` command:

```bash
aurite export
```

This command will:

1. Read all your component configurations from the local file system
2. Connect to the database (SQLite or PostgreSQL based on your configuration)
3. Create the necessary tables if they don't exist
4. Upload all your component configurations to the database

## Database Migration

Aurite provides a built-in migration tool to move data between SQLite and PostgreSQL databases. This is useful when:

- Transitioning from development (SQLite) to production (PostgreSQL)
- Moving from production back to local development
- Backing up data to a different database type

### Interactive Migration

The simplest way to migrate is using the interactive mode:

```bash
# Interactive migration wizard
aurite migrate

# Migrate from current database to the opposite type
aurite migrate --from-env
```

### Command-Line Migration

For automation and scripting, you can specify parameters directly:

```bash
# Migrate from SQLite to PostgreSQL
aurite migrate \
  --source-type sqlite \
  --source-path .aurite_db/aurite.db \
  --target-type postgresql

# The command will use environment variables for PostgreSQL connection
# or prompt for missing information
```

### Migration Examples

#### Example 1: Development to Production

Moving from local SQLite development to PostgreSQL production:

```bash
# Set up your PostgreSQL connection in .env
AURITE_DB_HOST=production.server.com
AURITE_DB_USER=prod_user
AURITE_DB_PASSWORD=secure_password
AURITE_DB_NAME=aurite_production

# Run migration
aurite migrate --from-env
```

#### Example 2: Production Backup to SQLite

Creating a local backup of production data:

```bash
# Assuming PostgreSQL is configured in environment
aurite migrate \
  --source-type postgresql \
  --target-type sqlite \
  --target-path backups/aurite_backup_$(date +%Y%m%d).db
```

#### Example 3: Switching Database Types

If you need to switch your active database type:

1. Migrate the data:

```bash
aurite migrate --from-env
```

2. Update your `.env` file with the new database configuration

3. Restart your Aurite services

### Migration Verification

The migration tool automatically verifies that all records were successfully transferred by comparing record counts between source and target databases. You can disable this with `--no-verify` if needed.

## Docker Deployment

When using Docker, the PostgreSQL service is optional. Here's how to configure each database type:

### Using SQLite with Docker

```yaml
# docker-compose.yml
services:
  aurite:
    image: aurite:latest
    environment:
      - AURITE_ENABLE_DB=true
      - AURITE_DB_TYPE=sqlite
      - AURITE_DB_PATH=/data/aurite.db
    volumes:
      - ./data:/data # Persist SQLite database
```

### Using PostgreSQL with Docker

```yaml
# docker-compose.yml
services:
  aurite:
    image: aurite:latest
    environment:
      - AURITE_ENABLE_DB=true
      - AURITE_DB_TYPE=postgresql
      - AURITE_DB_HOST=postgres
      - AURITE_DB_PORT=5432
      - AURITE_DB_USER=postgres_user
      - AURITE_DB_PASSWORD=postgres_password
      - AURITE_DB_NAME=aurite_storage
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres_user
      - POSTGRES_PASSWORD=postgres_password
      - POSTGRES_DB=aurite_storage
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Performance Considerations

### SQLite Performance Tips

- Keep the database file on a fast local disk (avoid network drives)
- Use WAL mode (automatically enabled by Aurite)
- Regular VACUUM operations for long-running deployments
- Consider migration to PostgreSQL if you need concurrent writes

### PostgreSQL Performance Tips

- Ensure adequate shared_buffers and work_mem settings
- Use connection pooling for high-traffic deployments
- Regular VACUUM and ANALYZE operations
- Consider read replicas for scaling read operations

## Troubleshooting

### Common SQLite Issues

**Error: Database is locked**

- Solution: Ensure only one process is writing to the database
- Consider upgrading to PostgreSQL for multi-user access

**Error: No such table**

- Solution: Run `aurite export` to create tables and populate initial data

### Common PostgreSQL Issues

**Error: Connection refused**

- Check that PostgreSQL is running and accessible
- Verify firewall rules allow connection on the specified port
- Ensure AURITE_DB_HOST is correct (use 'postgres' in Docker)

**Error: Authentication failed**

- Verify AURITE_DB_USER and AURITE_DB_PASSWORD are correct
- Check PostgreSQL pg_hba.conf for authentication settings

**Error: Database does not exist**

- Create the database manually or ensure the user has CREATE DATABASE permissions

## Best Practices

1. **Development**: Use SQLite for simplicity and portability
2. **Production**: Use PostgreSQL for reliability and scalability
3. **Backups**: Regular backups regardless of database type
4. **Migration**: Test migrations in a staging environment first
5. **Monitoring**: Monitor database size and performance metrics
6. **Security**: Use strong passwords and restrict database access

## Configuration Reference

### Force Refresh

Control whether the database configurations are reloaded for every operation:

```bash
# Reload from database on every operation (slower but always current)
AURITE_CONFIG_FORCE_REFRESH=true

# Cache configurations in memory (faster, default)
AURITE_CONFIG_FORCE_REFRESH=false
```

Set to `true` if you're making manual database changes and need immediate updates in Aurite.
