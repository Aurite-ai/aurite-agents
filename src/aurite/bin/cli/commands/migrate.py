"""Database migration commands for the Aurite CLI."""

import os
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ....lib.storage.db.db_connection import get_database_url
from ....lib.storage.db.db_migration import DatabaseMigrator, build_database_url

console = Console()


def migrate_database(
    source_type: Optional[str] = None,
    target_type: Optional[str] = None,
    source_path: Optional[str] = None,
    target_path: Optional[str] = None,
    source_host: Optional[str] = None,
    source_port: Optional[int] = None,
    source_user: Optional[str] = None,
    source_password: Optional[str] = None,
    source_name: Optional[str] = None,
    target_host: Optional[str] = None,
    target_port: Optional[int] = None,
    target_user: Optional[str] = None,
    target_password: Optional[str] = None,
    target_name: Optional[str] = None,
    verify: bool = True,
    interactive: bool = True,
):
    """
    Migrate data between SQLite and PostgreSQL databases.

    This command allows you to migrate all component configurations and agent history
    from one database to another. This is useful when switching between development
    (SQLite) and production (PostgreSQL) environments.
    """

    # Interactive mode - prompt for missing parameters
    if interactive and not all([source_type, target_type]):
        console.print("\n[bold cyan]Database Migration Wizard[/bold cyan]")
        console.print("This tool will help you migrate data between databases.\n")

        # Source database configuration
        console.print("[bold]Source Database Configuration[/bold]")
        if not source_type:
            source_type = Prompt.ask("Source database type", choices=["sqlite", "postgresql"], default="sqlite")

        source_url = None
        if source_type == "sqlite":
            if not source_path:
                source_path = Prompt.ask("Source SQLite database path", default=".aurite_db/aurite.db")
            source_url = build_database_url("sqlite", path=source_path)
        else:
            # Use environment variables as defaults for PostgreSQL
            if not source_host:
                default_host = os.getenv("AURITE_DB_HOST", "localhost")
                source_host = Prompt.ask("Source PostgreSQL host", default=default_host)
            if not source_port:
                default_port = os.getenv("AURITE_DB_PORT", "5432")
                source_port = int(Prompt.ask("Source PostgreSQL port", default=default_port))
            if not source_user:
                default_user = os.getenv("AURITE_DB_USER")
                if default_user:
                    source_user = Prompt.ask("Source PostgreSQL user", default=default_user)
                else:
                    source_user = Prompt.ask("Source PostgreSQL user")
            if not source_password:
                # Check if password is in environment
                env_password = os.getenv("AURITE_DB_PASSWORD")
                if env_password:
                    use_env_password = Confirm.ask(
                        "Use password from environment variable AURITE_DB_PASSWORD?", default=True
                    )
                    if use_env_password:
                        source_password = env_password
                    else:
                        source_password = Prompt.ask("Source PostgreSQL password", password=True)
                else:
                    source_password = Prompt.ask("Source PostgreSQL password", password=True)
            if not source_name:
                default_name = os.getenv("AURITE_DB_NAME", "aurite_storage")
                source_name = Prompt.ask("Source PostgreSQL database name", default=default_name)

            source_url = build_database_url(
                "postgresql",
                host=source_host,
                port=source_port,
                user=source_user,
                password=source_password,
                name=source_name,
            )

        # Target database configuration
        console.print("\n[bold]Target Database Configuration[/bold]")
        if not target_type:
            target_type = Prompt.ask(
                "Target database type",
                choices=["sqlite", "postgresql"],
                default="postgresql" if source_type == "sqlite" else "sqlite",
            )

        target_url = None
        if target_type == "sqlite":
            if not target_path:
                default_path = ".aurite/aurite_migrated.db" if source_type == "sqlite" else ".aurite_db/aurite.db"
                target_path = Prompt.ask("Target SQLite database path", default=default_path)
            target_url = build_database_url("sqlite", path=target_path)
        else:
            # Use environment variables as defaults for PostgreSQL (if switching to PostgreSQL)
            if not target_host:
                default_host = os.getenv("AURITE_DB_HOST", "localhost") if source_type == "sqlite" else "localhost"
                target_host = Prompt.ask("Target PostgreSQL host", default=default_host)
            if not target_port:
                default_port = os.getenv("AURITE_DB_PORT", "5432") if source_type == "sqlite" else "5432"
                target_port = int(Prompt.ask("Target PostgreSQL port", default=default_port))
            if not target_user:
                default_user = os.getenv("AURITE_DB_USER") if source_type == "sqlite" else None
                if default_user:
                    target_user = Prompt.ask("Target PostgreSQL user", default=default_user)
                else:
                    target_user = Prompt.ask("Target PostgreSQL user")
            if not target_password:
                # Check if password is in environment (only use if switching from SQLite)
                env_password = os.getenv("AURITE_DB_PASSWORD") if source_type == "sqlite" else None
                if env_password:
                    use_env_password = Confirm.ask(
                        "Use password from environment variable AURITE_DB_PASSWORD?", default=True
                    )
                    if use_env_password:
                        target_password = env_password
                    else:
                        target_password = Prompt.ask("Target PostgreSQL password", password=True)
                else:
                    target_password = Prompt.ask("Target PostgreSQL password", password=True)
            if not target_name:
                default_name = (
                    os.getenv("AURITE_DB_NAME", "aurite_storage") if source_type == "sqlite" else "aurite_storage"
                )
                target_name = Prompt.ask("Target PostgreSQL database name", default=default_name)

            target_url = build_database_url(
                "postgresql",
                host=target_host,
                port=target_port,
                user=target_user,
                password=target_password,
                name=target_name,
            )
    else:
        # Non-interactive mode - build URLs from provided parameters or environment variables
        if source_type == "sqlite":
            default_path = os.getenv("AURITE_DB_PATH", ".aurite_db/aurite.db")
            source_url = build_database_url("sqlite", path=source_path or default_path)
        else:
            source_url = build_database_url(
                "postgresql",
                host=source_host or os.getenv("AURITE_DB_HOST", "localhost"),
                port=source_port or int(os.getenv("AURITE_DB_PORT", "5432")),
                user=source_user or os.getenv("AURITE_DB_USER"),
                password=source_password or os.getenv("AURITE_DB_PASSWORD"),
                name=source_name or os.getenv("AURITE_DB_NAME", "aurite_storage"),
            )

        if target_type == "sqlite":
            target_url = build_database_url("sqlite", path=target_path or ".aurite/aurite_migrated.db")
        else:
            target_url = build_database_url(
                "postgresql",
                host=target_host or os.getenv("AURITE_DB_HOST", "localhost"),
                port=target_port or int(os.getenv("AURITE_DB_PORT", "5432")),
                user=target_user or os.getenv("AURITE_DB_USER"),
                password=target_password or os.getenv("AURITE_DB_PASSWORD"),
                name=target_name or os.getenv("AURITE_DB_NAME", "aurite_storage"),
            )

    if not source_url or not target_url:
        console.print("[bold red]Error:[/bold red] Failed to build database URLs")
        raise typer.Exit(code=1)

    # Display migration summary
    console.print("\n[bold]Migration Summary[/bold]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan")
    table.add_column("Source", style="green")
    table.add_column("Target", style="yellow")

    table.add_row(
        "Database Type",
        source_type.upper() if source_type else "UNKNOWN",
        target_type.upper() if target_type else "UNKNOWN",
    )

    if source_type == "sqlite":
        table.add_row("Path", source_path or ".aurite_db/aurite.db", "")
    else:
        table.add_row("Host", f"{source_host}:{source_port}", "")
        table.add_row("Database", source_name, "")

    if target_type == "sqlite":
        table.add_row("Path", "", target_path or ".aurite/aurite_migrated.db")
    else:
        table.add_row("Host", "", f"{target_host}:{target_port}")
        table.add_row("Database", "", target_name)

    console.print(table)

    # Confirm migration
    if interactive:
        if not Confirm.ask("\nProceed with migration?", default=True):
            console.print("[yellow]Migration cancelled.[/yellow]")
            raise typer.Exit()

    # Perform migration
    console.print("\n[bold green]Starting migration...[/bold green]")
    migrator = DatabaseMigrator(source_url, target_url)

    try:
        components_count, history_count = migrator.migrate_all()

        if components_count == 0 and history_count == 0:
            console.print("[yellow]Warning: No data was migrated. The source database may be empty.[/yellow]")
        else:
            console.print("\n[bold green]✅ Migration completed successfully![/bold green]")
            console.print(f"  • Migrated {components_count} component configurations")
            console.print(f"  • Migrated {history_count} agent history records")

        # Verify migration if requested
        if verify:
            console.print("\n[bold]Verifying migration...[/bold]")
            if migrator.verify_migration():
                console.print("[green]✅ Migration verification successful - all records match[/green]")
            else:
                console.print("[yellow]⚠️  Migration verification failed - record counts do not match[/yellow]")
                console.print("Please check the logs for more details.")

    except Exception as e:
        console.print(f"\n[bold red]Error during migration:[/bold red] {e}")
        raise typer.Exit(code=1) from e


def migrate_from_env():
    """
    Migrate from the current database (configured via environment variables) to a different database type.

    This is a convenience command that uses your current database configuration as the source
    and prompts you for the target database configuration.
    """
    console.print("\n[bold cyan]Database Migration from Current Configuration[/bold cyan]")

    # Get current database configuration from environment
    current_db_type = os.getenv("AURITE_DB_TYPE", "sqlite").lower()
    current_db_url = get_database_url()

    console.print(f"Current database type: [bold]{current_db_type.upper()}[/bold]")

    # Determine target type (opposite of current)
    target_type = "postgresql" if current_db_type == "sqlite" else "sqlite"

    if Confirm.ask(f"\nMigrate to {target_type.upper()}?", default=True):
        # Get target configuration
        console.print(f"\n[bold]Target {target_type.upper()} Configuration[/bold]")

        if target_type == "sqlite":
            target_path = Prompt.ask("Target SQLite database path", default=".aurite/aurite_migrated.db")
            target_url = build_database_url("sqlite", path=target_path)
        else:
            # Use environment variables as defaults when migrating from SQLite to PostgreSQL
            target_host = Prompt.ask("Target PostgreSQL host", default=os.getenv("AURITE_DB_HOST", "localhost"))
            target_port = int(Prompt.ask("Target PostgreSQL port", default=os.getenv("AURITE_DB_PORT", "5432")))

            default_user = os.getenv("AURITE_DB_USER")
            if default_user:
                target_user = Prompt.ask("Target PostgreSQL user", default=default_user)
            else:
                target_user = Prompt.ask("Target PostgreSQL user")

            # Check if password is in environment
            env_password = os.getenv("AURITE_DB_PASSWORD")
            if env_password:
                use_env_password = Confirm.ask(
                    "Use password from environment variable AURITE_DB_PASSWORD?", default=True
                )
                if use_env_password:
                    target_password = env_password
                else:
                    target_password = Prompt.ask("Target PostgreSQL password", password=True)
            else:
                target_password = Prompt.ask("Target PostgreSQL password", password=True)

            target_name = Prompt.ask(
                "Target PostgreSQL database name", default=os.getenv("AURITE_DB_NAME", "aurite_storage")
            )

            target_url = build_database_url(
                "postgresql",
                host=target_host,
                port=target_port,
                user=target_user,
                password=target_password,
                name=target_name,
            )

        if not target_url:
            console.print("[bold red]Error:[/bold red] Failed to build target database URL")
            raise typer.Exit(code=1)

        # Perform migration
        console.print("\n[bold green]Starting migration...[/bold green]")
        migrator = DatabaseMigrator(current_db_url, target_url)  # type: ignore

        try:
            components_count, history_count = migrator.migrate_all()

            if components_count == 0 and history_count == 0:
                console.print("[yellow]Warning: No data was migrated. The source database may be empty.[/yellow]")
            else:
                console.print("\n[bold green]✅ Migration completed successfully![/bold green]")
                console.print(f"  • Migrated {components_count} component configurations")
                console.print(f"  • Migrated {history_count} agent history records")

            # Verify migration
            console.print("\n[bold]Verifying migration...[/bold]")
            if migrator.verify_migration():
                console.print("[green]✅ Migration verification successful - all records match[/green]")
            else:
                console.print("[yellow]⚠️  Migration verification failed - record counts do not match[/yellow]")
                console.print("Please check the logs for more details.")

            # Offer to update environment configuration
            if target_type == "sqlite":
                console.print("\nTo use the new database, update your .env file:")
                console.print("  AURITE_DB_TYPE=sqlite")
                console.print(f"  AURITE_DB_PATH={target_path}")
            else:
                console.print("\nTo use the new database, update your .env file:")
                console.print("  AURITE_DB_TYPE=postgresql")
                console.print(f"  AURITE_DB_HOST={target_host}")
                console.print(f"  AURITE_DB_PORT={target_port}")
                console.print(f"  AURITE_DB_USER={target_user}")
                console.print("  AURITE_DB_PASSWORD=<your_password>")
                console.print(f"  AURITE_DB_NAME={target_name}")

        except Exception as e:
            console.print(f"\n[bold red]Error during migration:[/bold red] {e}")
            raise typer.Exit(code=1) from e
    else:
        console.print("[yellow]Migration cancelled.[/yellow]")
