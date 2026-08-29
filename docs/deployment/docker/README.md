# Aurite Agents Framework - Docker Image

[![Docker Pulls](https://img.shields.io/docker/pulls/aurite/aurite-agents)](https://hub.docker.com/r/aurite/aurite-agents)
[![Docker Image Size](https://img.shields.io/docker/image-size/aurite/aurite-agents/latest)](https://hub.docker.com/r/aurite/aurite-agents)
[![Docker Image Version](https://img.shields.io/docker/v/aurite/aurite-agents?sort=semver)](https://hub.docker.com/r/aurite/aurite-agents)

A production-ready Docker image for the **Aurite Agents Framework** - a powerful Python framework for building, testing, and running AI agents with Model Context Protocol (MCP) integration.

## 🚀 Quick Start

### Basic Usage

```bash
# Run with your existing project
docker run -v $(pwd):/app/project -p 8000:8000 -e API_KEY=your-secure-key aurite/aurite-agents

# Auto-initialize a new project
docker run -v $(pwd):/app/project -p 8000:8000 -e API_KEY=your-secure-key -e AURITE_AUTO_INIT=true aurite/aurite-agents
```

### With Docker Compose

1. **Download the example configuration:**

   ```bash
   curl -O https://raw.githubusercontent.com/Aurite-ai/aurite-agents/main/docker-compose.example.yml
   mv docker-compose.example.yml docker-compose.yml
   ```

2. **Create your environment file:**

   ```bash
   cat > .env << EOF
   API_KEY=your-secure-api-key-here
   OPENAI_API_KEY=your-openai-key
   ANTHROPIC_API_KEY=your-anthropic-key
   EOF
   ```

3. **Start the services:**
   ```bash
   docker compose up
   ```

## 📋 Environment Variables

### Required

| Variable  | Description                       | Example               |
| --------- | --------------------------------- | --------------------- |
| `API_KEY` | Secure API key for authentication | `your-secure-key-123` |

### Optional Configuration

| Variable           | Default                             | Description                                        |
| ------------------ | ----------------------------------- | -------------------------------------------------- |
| `AURITE_AUTO_INIT` | `false`                             | Auto-initialize project if no `.aurite` file found |
| `AURITE_ENABLE_DB` | `false`                             | Enable database persistence                        |
| `AURITE_DB_TYPE`   | `sqlite`                            | Database type: `sqlite` or `postgres`              |
| `AURITE_DB_PATH`   | `/app/project/.aurite_db/aurite.db` | SQLite database path                               |
| `LOG_LEVEL`        | `INFO`                              | Logging level: `DEBUG`, `INFO`, `WARN`, `ERROR`    |

### LLM Provider Keys

Pass through your LLM provider API keys:

```bash
-e OPENAI_API_KEY=your-key \
-e ANTHROPIC_API_KEY=your-key \
-e GEMINI_API_KEY=your-key \
-e AZURE_API_KEY=your-key
```

### PostgreSQL Configuration

For production deployments with PostgreSQL:

```bash
-e AURITE_ENABLE_DB=true \
-e AURITE_DB_TYPE=postgres \
-e AURITE_DB_HOST=postgres \
-e AURITE_DB_USER=aurite_user \
-e AURITE_DB_PASSWORD=secure_password \
-e AURITE_DB_NAME=aurite_db
```

## 🏗️ Usage Patterns

### 1. Existing Project

If you have an existing Aurite project with a `.aurite` file:

```bash
docker run -d \
  --name aurite-agents \
  -v /path/to/your/project:/app/project \
  -p 8000:8000 \
  -e API_KEY=your-secure-key \
  -e OPENAI_API_KEY=your-openai-key \
  aurite/aurite-agents
```

### 2. New Project (Auto-Initialize)

To create a new project automatically:

```bash
docker run -d \
  --name aurite-agents \
  -v /path/to/empty/directory:/app/project \
  -p 8000:8000 \
  -e API_KEY=your-secure-key \
  -e AURITE_AUTO_INIT=true \
  aurite/aurite-agents
```

### 3. Production Setup with PostgreSQL

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: aurite_user
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: aurite_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  aurite:
    image: aurite/aurite-agents:latest
    depends_on:
      - postgres
    environment:
      - API_KEY=your-secure-key
      - AURITE_ENABLE_DB=true
      - AURITE_DB_TYPE=postgres
      - AURITE_DB_HOST=postgres
      - AURITE_DB_USER=aurite_user
      - AURITE_DB_PASSWORD=secure_password
      - AURITE_DB_NAME=aurite_db
      - OPENAI_API_KEY=your-openai-key
    volumes:
      - ./project:/app/project
    ports:
      - "8000:8000"

volumes:
  postgres_data:
```

## 🔧 CLI Usage

The container provides full access to the Aurite CLI through the `aurite` command:

```bash
# View all available commands
docker run --rm -v $(pwd):/app/project -e API_KEY=your-key aurite/aurite-agents aurite --help

# List available components
docker run --rm -v $(pwd):/app/project -e API_KEY=your-key aurite/aurite-agents aurite list

# Show specific component configuration
docker run --rm -v $(pwd):/app/project -e API_KEY=your-key aurite/aurite-agents aurite show agent my-agent

# Run an agent
docker run --rm -v $(pwd):/app/project -e API_KEY=your-key aurite/aurite-agents aurite run my-agent

# Initialize a new project interactively
docker run -it --rm -v $(pwd):/app/project -e API_KEY=your-key aurite/aurite-agents aurite init

# Interactive shell for debugging
docker run -it --rm -v $(pwd):/app/project -e API_KEY=your-key aurite/aurite-agents bash
```

### Available CLI Commands

The container supports all Aurite CLI commands:

- `init` - Initialize new projects or workspaces
- `list` - List components by type
- `show` - Display component configurations
- `run` - Execute agents or workflows
- `api` - Start the API server (default)
- `studio` - Start the web interface
- `edit` - Launch the configuration editor TUI
- `migrate` - Database migration utilities
- `export` - Export configurations to database

## 🌐 API Access

Once running, the API is available at:

- **Health Check:** `http://localhost:8000/health`
- **API Documentation:** `http://localhost:8000/docs`
- **OpenAPI Spec:** `http://localhost:8000/openapi.json`

## 📁 Volume Mounts

### Project Directory

Mount your project directory to `/app/project`:

```bash
-v /path/to/your/project:/app/project
```

The container will search for `.aurite` files starting from this directory and walking up the directory tree.

### Cache Directory

Optionally mount a cache directory for better performance:

```bash
-v aurite_cache:/app/cache
```

## 🔒 Security

- Runs as non-root user (`appuser`, UID 1000)
- No default API keys included
- Secure defaults for all configurations
- Health checks included for container orchestration

## 🏷️ Image Tags

| Tag          | Description           | Use Case            |
| ------------ | --------------------- | ------------------- |
| `latest`     | Latest stable release | Production          |
| `0.3.28`     | Specific version      | Production (pinned) |
| `0.3.28-dev` | Development build     | Testing             |

## 🔍 Troubleshooting

### Container Won't Start

1. **Check API_KEY is set:**

   ```bash
   docker logs <container-name>
   ```

2. **Verify project structure:**
   ```bash
   docker run --rm -v $(pwd):/app/project aurite/aurite-agents ls -la /app/project
   ```

### Database Connection Issues

1. **PostgreSQL not ready:**

   - The container waits for PostgreSQL to be ready
   - Check PostgreSQL container logs
   - Verify network connectivity

2. **SQLite permissions:**
   - Ensure the mounted directory is writable
   - Check file permissions on the host

### Health Check Failures

The container includes health checks that verify the API server is responding:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' <container-name>

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' <container-name>
```

## 📚 Documentation

- **GitHub Repository:** https://github.com/Aurite-ai/aurite-agents
- **Documentation:** https://github.com/Aurite-ai/aurite-agents/blob/main/README.md
- **Examples:** https://github.com/Aurite-ai/aurite-agents/tree/main/docs/getting-started/tutorials

## 🏗️ Architecture

This image is built with:

- **Base:** Python 3.12 slim
- **Platforms:** linux/amd64, linux/arm64
- **Size:** Optimized multi-stage build
- **Security:** Non-root user, minimal attack surface

## 📄 License

MIT License - see the [LICENSE](https://github.com/Aurite-ai/aurite-agents/blob/main/LICENSE) file for details.

## 🤝 Support

- **Issues:** https://github.com/Aurite-ai/aurite-agents/issues
- **Discussions:** https://github.com/Aurite-ai/aurite-agents/discussions
- **Email:** hello@aurite.ai

---

**Built with ❤️ by the Aurite AI team**
