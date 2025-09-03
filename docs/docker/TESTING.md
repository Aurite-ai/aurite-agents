# Docker Container Testing Guide

This guide explains how to test the Aurite Agents Docker container during development and before publishing to DockerHub.

## Quick Test

To build and test the container locally without publishing:

```bash
./scripts/docker/build_and_publish.sh --build-only
```

This will:

1. Build the Docker image locally (linux/amd64 only for speed)
2. Run automated tests including health checks
3. Test auto-initialization functionality
4. Provide feedback on the build success
5. Show you the command to publish if tests pass

## Container Management System

The container uses an intelligent entrypoint script (`docker-entrypoint.sh`) that handles:

### **Project Detection**

- Searches for `.aurite` files in the mounted directory and parent directories
- Uses the same upward search logic as the ConfigManager
- Provides clear feedback about project status

### **Auto-Initialization**

- Creates new projects when `AURITE_AUTO_INIT=true`
- Falls back to manual project structure creation if CLI fails
- Creates proper `.aurite` configuration and sample files
- Only works in empty directories for safety

### **CLI Command Handling**

- Routes `aurite` commands through the Python module system
- Handles all CLI commands: `init`, `list`, `show`, `run`, `api`, etc.
- Provides proper error handling and logging

## Testing Workflow

### 1. Build and Test Locally

```bash
# Test current version from pyproject.toml
./scripts/docker/build_and_publish.sh --build-only

# Test specific version
./scripts/docker/build_and_publish.sh 0.3.28 --build-only
```

### 2. Manual Testing (Optional)

After the automated tests pass, you can manually test the container:

```bash
# Start the container
docker run -d --name aurite-test \
  -p 8000:8000 \
  -e API_KEY=test-key \
  -e AURITE_AUTO_INIT=true \
  aurite/aurite-agents:0.3.28

# Check health
curl http://localhost:8000/health

# View logs
docker logs aurite-test

# Test API docs
open http://localhost:8000/docs

# Clean up
docker stop aurite-test
docker rm aurite-test
```

### 3. Publish After Testing

Once you're satisfied with the tests:

```bash
# Publish specific version
./scripts/docker/build_and_publish.sh 0.3.28 --push

# Publish as latest (for stable releases)
./scripts/docker/build_and_publish.sh 0.3.28 --push --latest
```

## What Gets Tested

The automated test suite verifies:

1. **Build Success**: Container builds without errors
2. **Startup**: Container starts successfully
3. **Health Check**: Built-in health endpoint responds
4. **Auto-Init**: Project initialization works
5. **API Server**: FastAPI server is accessible
6. **Cleanup**: Test containers are properly removed

## Test Scenarios

### Basic Functionality

- Container starts with minimal configuration
- Health endpoint returns 200 OK
- Auto-initialization creates project structure
- CLI commands work correctly (`aurite --help`, `aurite list`, etc.)

### Auto-Initialization Testing

Test the auto-initialization feature:

```bash
# Test auto-init in empty directory
mkdir -p /tmp/test-aurite-init
docker run --rm \
  -v /tmp/test-aurite-init:/app/project \
  -e API_KEY=test-key \
  -e AURITE_AUTO_INIT=true \
  aurite/aurite-agents:0.3.28 \
  timeout 10 python -c "print('Init test complete')"

# Verify created files
ls -la /tmp/test-aurite-init
cat /tmp/test-aurite-init/.aurite
cat /tmp/test-aurite-init/configs/sample.json

# Clean up
rm -rf /tmp/test-aurite-init
```

### CLI Command Testing

Test all major CLI commands:

```bash
# Test help command
docker run --rm -v $(pwd):/app/project -e API_KEY=test-key aurite/aurite-agents aurite --help

# Test list command (requires existing project)
docker run --rm -v $(pwd):/app/project -e API_KEY=test-key aurite/aurite-agents aurite list

# Test show command
docker run --rm -v $(pwd):/app/project -e API_KEY=test-key aurite/aurite-agents aurite show llm

# Test version
docker run --rm -v $(pwd):/app/project -e API_KEY=test-key aurite/aurite-agents aurite --version
```

### Error Handling

- Missing API_KEY fails gracefully with clear error message
- Non-empty directory prevents auto-initialization
- Invalid configurations show helpful errors
- Container logs provide debugging information

### Performance

- Build completes in reasonable time (~70 seconds)
- Container starts within health check timeout (40 seconds)
- Memory and CPU usage are reasonable
- Health checks respond consistently

## Troubleshooting Tests

### Build Failures

```bash
# Check Docker daemon
docker info

# Verify files exist
ls -la Dockerfile.public docker-entrypoint.sh

# Check from project root
pwd  # Should be in aurite/framework directory
```

### Test Failures

```bash
# View detailed logs
docker logs aurite-test-<pid>

# Check health manually
docker exec aurite-test-<pid> curl -f http://localhost:8000/health

# Inspect container
docker inspect aurite-test-<pid>
```

### Common Issues

1. **Port conflicts**: Change port with `-p 8001:8000`
2. **Permission issues**: Ensure Docker daemon is running
3. **Build context**: Run from project root directory
4. **Resource limits**: Ensure sufficient disk space and memory

## CI/CD Integration

The GitHub Actions workflow automatically:

- Builds multi-platform images (amd64, arm64)
- Runs the same test suite
- Publishes to DockerHub on success
- Updates Docker Hub description

Manual testing is still recommended for:

- Major version releases
- Significant functionality changes
- Before marking releases as "latest"

## Development Testing & Debugging

### Understanding the Container Architecture

The container uses a sophisticated entrypoint system that handles multiple scenarios:

1. **Package Installation**: Uses `poetry install --with storage` in editable mode
2. **CLI Access**: Routes `aurite` commands through Python module system since script entry points aren't created in editable installs
3. **Project Discovery**: Uses ConfigManager's upward search from `/app/project`
4. **Fallback Logic**: Manual project creation if CLI commands fail

### Common Development Issues

#### CLI Command Not Found

**Symptom**: `aurite: not found` or `No module named aurite.bin.cli.__main__`
**Cause**: Script entry points not created during editable install
**Solution**: Use Python module invocation in entrypoint script

#### Auto-Init Failures

**Symptom**: "Failed to run aurite init command"
**Cause**: CLI not available or init command issues
**Solution**: Fallback to manual project structure creation

#### Health Check Failures

**Symptom**: Container marked as unhealthy
**Cause**: API server not starting or responding
**Debug**: Check container logs and environment variables

### Testing New Changes

When modifying the container system:

1. **Update entrypoint script** (`docker-entrypoint.sh`)
2. **Rebuild container**: `./scripts/docker/build_and_publish.sh --build-only`
3. **Test CLI**: `docker run --rm -v $(pwd):/app/project -e API_KEY=test-key aurite/aurite-agents aurite --help`
4. **Test auto-init**: Use empty directory with `AURITE_AUTO_INIT=true`
5. **Verify health**: Check that health checks pass consistently

### Expected Test Outputs

#### Successful CLI Test

```
[INFO] Running aurite CLI command...

 Usage: aurite [OPTIONS] COMMAND [ARGS]...
 A framework for building, testing, and running AI agents.

 [Commands listed...]
```

#### Successful Auto-Init Test

```
[INFO] AURITE_AUTO_INIT is enabled - initializing new project
[INFO] Initializing new Aurite project...
[WARN] Aurite CLI not available, creating basic project structure manually...
[INFO] Creating basic project structure manually...
[INFO] Creating .aurite configuration file...
[INFO] Creating sample configuration file...
[INFO] Project initialization complete!
```

## Next Steps

After successful testing:

1. **Review the output** - Check for any warnings or issues
2. **Test manually** - Verify key functionality works as expected
3. **Publish** - Use the provided command to push to DockerHub
4. **Update documentation** - Ensure Docker Hub README is current
5. **Tag release** - Create GitHub release to trigger automated builds
