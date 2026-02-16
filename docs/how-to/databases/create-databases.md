# Setting Up the Relational and Vector Databases

This guide walks you through provisioning a **PostgreSQL 16** (relational) and **Qdrant** (vector) database on a remote Ubuntu/Debian server using Docker Compose.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Ubuntu server | Get one from any cloud provider (AWS, Azure, GCP, etc.) |
| SSH access | Open port **22** on the server for SSH |
| Open ports | **5432** (Postgres), **6333** (Qdrant HTTP), **6334** (Qdrant gRPC) |

> **Note:** In production, restrict port access to only the IP addresses that need connectivity.

---

## Instructions

- SSH into your server
```bash
ssh user@<YOUR_SERVER_IPV4>
```

- Copy the `databases/` directory to your server
```bash
scp -r docs/how-to/databases/ user@<YOUR_SERVER_IPV4>:~
```

- Provide appropriate permissions and run the bootstrap script
 ```bash
cd ~/databases
chmod +x setup-server.sh
./setup-server.sh
```

The script will:
1. Install Docker Engine & Docker Compose plugin
2. Start the Postgres + Qdrant stack
3. Grant all necessary database permissions to the configured user

---


## Testing Connectivity

- Test Postgres connection
```bash
psql -h <YOUR_SERVER_IPV4> -p 5432 -U database_user -d database_name
```

- Test Qdrant
```bash
curl http://<YOUR_SERVER_IPV4>:6333/readyz
```
---