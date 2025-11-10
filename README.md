# Platform Root (Mac Studio)

This is the root folder for your platform. It currently includes 3 apps:

- **amp-support-bot**
- **amp-sql-gen**
- **amp-translator**

## Structure
- apps/ — each app has its own folder, Dockerfile, and code
- infra/compose/ — docker-compose.yml files
- infra/cloudflared/ — Cloudflare Tunnel config for this machine
- data/ — persistent data volumes
- logs/ — logs
- models/ — AI/ML model files
- backups/ — DB dumps, exports
- scripts/ — helper scripts
