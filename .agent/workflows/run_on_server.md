---
description: how to run and manage the website on the server using Docker
---

# Managing the Website on the Server

All commands should be run from the project directory on the server:
`cd ~/mwo_website`

## 1. Start the Website
To start the containers in the background:
```bash
sudo docker compose up -d
```

## 2. Stop the Website
To stop and remove the containers:
```bash
sudo docker compose down
```

## 3. Rebuild and Update
If you have made code changes or want to force a fresh build:
```bash
sudo docker compose up -d --build
```

## 4. View Logs
To check the logs for troubleshooting:
- All services: `sudo docker compose logs -f`
- Backend only: `sudo docker compose logs -f backend`
- Frontend only: `sudo docker compose logs -f frontend`

## 5. Check Status
To see which containers are running and their ports:
```bash
sudo docker compose ps
```

## 6. Access the Website
- **HTTPS (Port 8000)**: `https://121.240.10.8:8000`
- **HTTP (Port 8001)**: `http://121.240.10.8:8001`
