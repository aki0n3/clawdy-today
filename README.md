Build docker image:

```bash
docker build -t openclaw-agent .
```

Run with HTTP (local testing):

```bash
docker run --env-file .env -p 8000:8000 openclaw-agent
```

Run with HTTPS (certbot certificates on VPS):

```bash
docker run --env-file .env -p 8000:8000 \
  -e SSL_CERTFILE=/etc/letsencrypt/live/your-domain.com/fullchain.pem \
  -e SSL_KEYFILE=/etc/letsencrypt/live/your-domain.com/privkey.pem \
  -v /etc/letsencrypt:/etc/letsencrypt:ro \
  openclaw-agent
```

Run with Mock Mode (for testing without valid API key):

```bash
docker run --env-file .env -e USE_MOCK=true -p 8000:8000 openclaw-agent
```

## Health Checks & Background Testing

### Run health check once

```bash
cd app
python3 health_check.py --once
```

### Run health check daemon (random 30min-3h intervals)

```bash
cd app
python3 health_check.py --daemon
```

### Setup automatic testing with crontab

Add to your crontab to run health checks every 30 minutes:

```bash
*/30 * * * * cd /path/to/app && python3 health_check.py --once >> ../logs/health_check.log 2>&1
```

For random intervals (30min to 3h between checks), run as systemd service:

### Health check options

```bash
python3 health_check.py --once              # Run once and exit
python3 health_check.py --daemon            # Run as daemon with random intervals
python3 health_check.py --task-only         # Test only /task/send endpoint
python3 health_check.py --stream-only       # Test only /stream endpoint
```

Logs are saved to `logs/health_check.log`

## Web UI

Access the interactive web interface at:
```
http://localhost:8000/
```

Features:
- Send custom tasks with system prompts
- Send random tasks from 750+ predefined examples
- View real-time stream events
- See response statistics (tokens, model, etc)
- Automatic fallback to mock mode if API key is invalid