# Async Bot with Redis Integration

This Python project showcases an asynchronous bot that integrates with Redis for efficient data management. It's designed to manage guests, cache messages from a Google Sheet into a Redis database, providing quick access to data for bot operations.

## Features

- **Asynchronous Operations**: Utilizes `asyncio` for non-blocking task execution, enhancing performance.
- **Redis Caching**: Caches data from Google Sheets into Redis, ensuring fast data retrieval.
- **Command Handling**: Includes a command handler for the `/start` command, demonstrating how to interact with users.

## Getting Started

### Prerequisites

Docker. If you don't have Docker installed, you can download it from the official website: [https://www.docker.com/get-started](https://www.docker.com/get-started)

Under the hood, the project uses the following technologies:
- Python 3.7+
- Redis server
- gspread for Google Sheets integration

### Installation

1. Clone the repository
2. Set up your .env file using `example.env` as a template
3. Run the following command to build the Docker image:
```bash
docker-compose up --build -d
```


### Tests
Can be run with `pytest` if installed.:

```bash
make test
```