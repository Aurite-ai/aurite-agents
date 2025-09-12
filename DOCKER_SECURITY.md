# Docker Security Guide for Aurite Agents Framework

## Quick Start - Secure Deployment

```bash
# 1. Generate a secure API key
export API_KEY=$(openssl rand -hex 32)

# 2. Run with security best practices
docker run \
  --read-only \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  --tmpfs /tmp:noexec,nosuid \
  --tmpfs /app/cache:noexec,nosuid \
  -e API_KEY=$API_KEY \
  -v $(pwd)/my-project:/app/project:rw \
  -p 127.0.0.1:8000:8000 \
  aurite/aurite-agents:latest
```

## Security Features

### Built-in Security

- ✅ **Non-root user**: Container runs as `appuser` (UID 1000)
- ✅ **Minimal base image**: Python 3.12-slim with SHA256 verification
- ✅ **No hardcoded secrets**: All credentials via environment variables
- ✅ **Health checks**: Built-in endpoint monitoring
- ✅ **Multi-stage build**: Removes build dependencies from final image

### Required Configuration

#### API Key (Required)

The container **requires** an `API_KEY` environment variable for API authentication:

```bash
# Generate a secure API key
export API_KEY=$(openssl rand -hex 32)

# Pass to container
docker run -e API_KEY=$API_KEY aurite/aurite-agents
```

⚠️ **Warning**: Never hardcode API keys in scripts or commit them to version control.

## Production Security Checklist

### 1. Use TLS/HTTPS

Always use a reverse proxy with TLS in production:

```nginx
# nginx.conf example
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://aurite:8000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Network Isolation

Bind to localhost only or use Docker networks:

```bash
# Bind to localhost only
docker run -p 127.0.0.1:8000:8000 aurite/aurite-agents

# Or use Docker networks (see docker-compose.example.yml)
docker network create aurite-network
docker run --network aurite-network aurite/aurite-agents
```

### 3. Read-Only Filesystem

Run with read-only root filesystem:

```bash
docker run \
  --read-only \
  --tmpfs /tmp:noexec,nosuid \
  --tmpfs /app/cache:noexec,nosuid \
  aurite/aurite-agents
```

### 4. Drop Capabilities

Remove all unnecessary Linux capabilities:

```bash
docker run \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  aurite/aurite-agents
```

### 5. Resource Limits

Set memory and CPU limits:

```bash
docker run \
  --memory="2g" \
  --memory-swap="2g" \
  --cpus="2.0" \
  aurite/aurite-agents
```

## Secrets Management

### Environment Variables (Basic)

```bash
# Create .env file (never commit this!)
cat > .env << EOF
API_KEY=$(openssl rand -hex 32)
AURITE_DB_PASSWORD=$(openssl rand -hex 32)
EOF

# Use with docker run
docker run --env-file .env aurite/aurite-agents
```

### Docker Secrets (Recommended for Swarm)

```bash
# Create secrets
echo "your-api-key" | docker secret create api_key -
echo "your-db-password" | docker secret create db_password -

# Use in docker-compose.yml
services:
  aurite:
    image: aurite/aurite-agents
    secrets:
      - api_key
      - db_password
```

### External Secret Managers (Production)

For production, consider using:

- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager

## Database Security

When using PostgreSQL:

```yaml
environment:
  AURITE_ENABLE_DB: "true"
  AURITE_DB_TYPE: "postgres"
  AURITE_DB_HOST: "postgres"
  AURITE_DB_PORT: "5432"
  AURITE_DB_NAME: "aurite"
  AURITE_DB_USER: "aurite_user"
  AURITE_DB_PASSWORD: "${DB_PASSWORD}" # From .env file
```

**Best Practices:**

- Use strong passwords (minimum 32 characters)
- Enable SSL/TLS for database connections
- Use separate database users with minimal privileges
- Regular backups with encryption

## Security Scanning

### Before Deployment

```bash
# Scan with Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image aurite/aurite-agents:latest

# Scan with Snyk
snyk container test aurite/aurite-agents:latest

# Check for secrets in image layers
docker history aurite/aurite-agents:latest --no-trunc | grep -i secret
```

### Runtime Security

```bash
# Run with AppArmor (if available)
docker run --security-opt apparmor=docker-default aurite/aurite-agents

# Run with SELinux (if available)
docker run --security-opt label=level:s0:c100,c200 aurite/aurite-agents

# Enable user namespace remapping
dockerd --userns-remap=default
```

## Monitoring & Logging

### Health Checks

The container includes a health check endpoint:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' container_name

# Manual health check
curl http://localhost:8000/health
```

### Logging Configuration

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service=aurite,environment=production"
```

### Security Events to Monitor

- Failed authentication attempts
- Unusual API request patterns
- Container restart events
- Resource limit violations
- Network connection anomalies

## Incident Response

### If Compromised

1. **Immediate Actions:**

   ```bash
   # Stop the container
   docker stop aurite-agents

   # Rotate all credentials
   export NEW_API_KEY=$(openssl rand -hex 32)

   # Pull latest image
   docker pull aurite/aurite-agents:latest
   ```

2. **Investigation:**

   ```bash
   # Check logs
   docker logs aurite-agents --since 24h

   # Inspect container
   docker inspect aurite-agents

   # Check for modifications
   docker diff aurite-agents
   ```

3. **Recovery:**
   - Rotate all API keys and passwords
   - Update to latest patched version
   - Review and update security policies
   - Notify affected users if applicable

## Security Updates

### Stay Updated

```bash
# Check for updates
docker pull aurite/aurite-agents:latest

# View image details
docker inspect aurite/aurite-agents:latest | jq '.[0].Config.Labels'

# Subscribe to security advisories
# https://github.com/Aurite-ai/aurite-agents/security/advisories
```

### Automated Updates (with caution)

```yaml
# Using Watchtower (test thoroughly before production use)
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 86400 --cleanup aurite-agents
```

## Compliance & Auditing

### Security Compliance

The Aurite Agents Docker image follows:

- CIS Docker Benchmark recommendations
- OWASP Docker Security Top 10
- NIST Cybersecurity Framework guidelines

### Audit Checklist

- [ ] API_KEY is securely generated and stored
- [ ] TLS/HTTPS is configured for production
- [ ] Container runs as non-root user
- [ ] Resource limits are configured
- [ ] Network access is restricted
- [ ] Logs are collected and monitored
- [ ] Regular security updates are applied
- [ ] Backup and recovery procedures are tested

## Support & Reporting

### Security Issues

Report security vulnerabilities to: security@aurite.ai

**Do not** report security issues via public GitHub issues.

### Documentation

- [Main Documentation](https://github.com/Aurite-ai/aurite-agents)
- [Security Policy](https://github.com/Aurite-ai/aurite-agents/blob/main/SECURITY.md)
- [Docker Hub](https://hub.docker.com/r/aurite/aurite-agents)

## Example Configurations

### Development (Relaxed Security)

```bash
docker run \
  -e API_KEY=dev-key-for-testing \
  -e AURITE_AUTO_INIT=true \
  -v $(pwd):/app/project \
  -p 8000:8000 \
  aurite/aurite-agents
```

### Production (Maximum Security)

```bash
docker run \
  --name aurite-prod \
  --read-only \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  --cap-add=CHOWN,SETUID,SETGID \
  --memory="2g" \
  --memory-swap="2g" \
  --cpus="2.0" \
  --tmpfs /tmp:noexec,nosuid,size=100M \
  --tmpfs /app/cache:noexec,nosuid,size=500M \
  -e API_KEY_FILE=/run/secrets/api_key \
  -v $(pwd)/project:/app/project:ro \
  -v $(pwd)/secrets:/run/secrets:ro \
  --network aurite-network \
  --restart unless-stopped \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  aurite/aurite-agents
```

---

_Last Updated: 2025-09-06_
_Version: 0.3.28_
