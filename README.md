# Multisession notebook

## Systemy Rozproszone

This project realizes a functionality of a multisession (multi threaded) collaborative notebook, with authentication. It supports multisession updates, delegated to adequate workers by a `Kafka` message broker.

## Authors

- Łukasz Florek
- Konrad Czerniej
- Jakub Janik

## How to run

### 1. Open terminal in root folder

### 2. Run command

```bash
python3 ./backend/app/init_env.py
```

to generate a test `.env` file locally.

### 3. Run Docker Engine (e.g. run Docker desktop)

### 4. In the root folder run

```bash
docker compose up --build
```

### 5. Wait for the service to start on port `http://localhost:8000`

### 6. You can use Postman agent to test requests
