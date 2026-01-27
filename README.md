# Instagram Reels Telegram Bot

This project provides a Telegram bot that allows users to parse Instagram reels from specified accounts and receive the data in XLSX format. The system consists of a Telegram bot service and an API service for Instagram parsing, supported by PostgreSQL database, Redis cache, and proxy management.

## Project Structure

The project is organized as follows:

- `app/`: API service built with FastAPI
  - `api/`: API endpoints for Instagram parsing and account management
  - `core/`: Configuration and settings
  - `db/`: Database models and data access objects
  - `exceptions/`: Custom exception classes
  - `models/`: Data models
  - `parser/`: Instagram parsing logic
  - `services/`: Business logic services
- `bot/`: Telegram bot service built with aiogram
  - `handlers/`: Command handlers
  - `keyboards/`: Inline keyboards
  - `states/`: FSM states
  - `utils/`: Utility functions
- `alembic/`: Database migration scripts
- `docker-compose.yml`: Docker Compose configuration
- `Dockerfile`: Multi-stage Docker build file
- `.env`: Environment variables configuration

## Running the Project

### Prerequisites

- Docker and Docker Compose
- Python 3.12 or higher (for local development)
- PostgreSQL (for local development)
- Redis (for local development)

### Docker Setup

1. Ensure Docker and Docker Compose are installed.

2. Create a `.env` file in the project root with the required environment variables. Refer to `.env.test` for the expected format and variables.

3. Run the following command to start all services:

   ```
   docker-compose up --build
   ```

   This will start the following services:
   - PostgreSQL database on port 5432
   - Redis on port 6379
   - API service on port 8000
   - Telegram bot

4. The bot will be ready to receive commands once all services are healthy.

### Local Development Setup

1. Install Python 3.12 or higher.

2. Install dependencies using uv:

   ```
   pip install uv
   uv sync
   ```

3. Install Playwright browsers:

   ```
   uv run playwright install chromium
   uv run playwright install-deps chromium
   ```

4. Set up PostgreSQL and Redis locally, or use Docker for these services:

   ```
   docker run -d --name postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=instagram_parser -p 5432:5432 postgres:18
   docker run -d --name redis -p 6379:6379 redis:8
   ```

5. Create a `.env` file with the required environment variables.

6. Run database migrations:

   ```
   uv run alembic upgrade head
   ```

7. Start the API service:

   ```
   uv run -m app.main
   ```

8. In a separate terminal, start the bot:

   ```
   uv run -m bot.main
   ```

## Workflow

The Telegram bot interacts with the API service to parse Instagram reels. The typical workflow is as follows:

1. User sends `/parse` command to the bot.

2. Bot prompts for Instagram username input.

3. Bot validates the username format.

4. Bot prompts for maximum number of reels to parse (1-1000 or 0 for all).

5. Bot sends a request to the API service with the provided parameters.

6. API service:
   - Retrieves a valid Instagram account from the database
   - Uses browser automation to authenticate and fetch reels data
   - Handles pagination to collect all requested reels
   - Generates an XLSX file with reel data
   - Updates account usage statistics

7. API returns the XLSX file to the bot.

8. Bot sends the file to the user.

Error handling includes:

- Private accounts: Returns 403 Forbidden with message "This account private"
- Account not found: Returns 404 Not Found with message "Account not found"
- No valid accounts available: Returns 404 Not Found with message "No valid Instagram accounts available. Please add an account first."
- Authentication failures: Invalidates the account and returns 500 Internal Server Error
- Other errors: Returns 500 Internal Server Error and may invalidate the account

## API Endpoints

### POST /instagram/parse/xlsx

Parses Instagram reels from a specified username and returns data in XLSX format.

**Path:** `/instagram/parse/xlsx`

**Method:** POST

**Request Body:**

```json
{
	"target_username": "iamrigbycat",
	"max_reels": 100
}
```

**Parameters:**

- `target_username` (string, required): Instagram username to parse reels from
- `max_reels` (integer, optional): Maximum number of reels to parse (1-1000). If null or omitted, parses all available reels.

**Response:**

- Status 200: XLSX file download with filename `{username}_reels.xlsx`
- Status 403: Account is private
- Status 404: Account not found or no valid accounts available
- Status 500: Internal server error

**XLSX File Structure:**
The generated XLSX file contains a sheet named "Reels" with the following columns:

- Ссылка (Link): Direct URL to the reel
- Просмотры (Views): Number of views
- Лайки (Likes): Number of likes
- Комменты (Comments): Number of comments
- Вирусность (Virality): Engagement rate calculated as (likes + comments) / views

**Example Request (Python):**

```python
import httpx

async def parse_reels():
    url = "http://localhost:8000/instagram/parse/xlsx"
    data = {
        "target_username": "iamrigbycat",
        "max_reels": 100
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        response.raise_for_status()

        # Save the XLSX file
        with open("reels.xlsx", "wb") as f:
            f.write(response.content)
```

**Example Response:**

- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Content-Disposition: `attachment; filename=iamrigbycat_reels.xlsx`

### Instagram Account Management

#### GET /accounts

Retrieves a list of all Inst1agram accounts.

**Method:** GET

**Response:**

- Status 200: List of accounts
- Status 404: No accounts found
- Status 500: Internal server error

**Response Body:**

```json
{
	"total": 2,
	"accounts": [
		{
			"login": "user1",
			"password": "password1",
			"cookies": {},
			"last_used_at": "2024-01-01T12:00:00Z"
		},
		{
			"login": "user2",
			"password": "password2",
			"cookies": {},
			"last_used_at": "2024-01-02T12:00:00Z"
		}
	]
}
```

#### GET /accounts/{login}

Retrieves detailed information about a specific Instagram account.

**Method:** GET

**Parameters:**

- `login` (string, required): Instagram account login

**Response:**

- Status 200: Account details
- Status 404: Account not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"login": "user1",
	"password": "password1",
	"cookies": {},
	"last_used_at": "2024-01-01T12:00:00Z"
}
```

#### POST /accounts

Adds a new Instagram account by logging in and extracting credentials.

**Method:** POST

**Request Body:**

```json
{
	"login": "newuser",
	"password": "newpassword"
}
```

**Response:**

- Status 201: Account added successfully
- Status 400: Account already exists or invalid credentials
- Status 500: Internal server error

**Response Body:**

```json
{
	"login": "newuser",
	"password": "newpassword",
	"cookies": {},
	"last_used_at": null
}
```

#### PUT /accounts/{login}

Updates the password of a specific Instagram account.

**Method:** PUT

**Parameters:**

- `login` (string, required): Instagram account login

**Request Body:**

```json
{
	"password": "newpassword"
}
```

**Response:**

- Status 200: Account updated successfully
- Status 404: Account not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"login": "user1",
	"password": "newpassword",
	"cookies": {},
	"last_used_at": "2024-01-01T12:00:00Z"
}
```

#### PATCH /accounts/{login}/validity

Updates the validity status of a specific Instagram account.

**Method:** PATCH

**Parameters:**

- `login` (string, required): Instagram account login

**Request Body:**

```json
{
	"valid": true
}
```

**Response:**

- Status 200: Account validity updated
- Status 404: Account not found
- Status 500: Internal server error

#### POST /accounts/{login}/test

Tests the validity of a specific Instagram account by attempting login.

**Method:** POST

**Parameters:**

- `login` (string, required): Instagram account login

**Response:**

- Status 200: Account test completed
- Status 404: Account not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"status": "valid",
	"message": "Account login successful"
}
```

#### DELETE /accounts/{login}

Deletes a specific Instagram account.

**Method:** DELETE

**Parameters:**

- `login` (string, required): Instagram account login

**Response:**

- Status 200: Account deleted successfully
- Status 404: Account not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"status": "success"
}
```

### Proxy Management

#### GET /proxies

Retrieves a list of all proxies.

**Method:** GET

**Response:**

- Status 200: List of proxies
- Status 404: No proxies found
- Status 500: Internal server error

**Response Body:**

```json
{
	"total": 2,
	"proxies": [
		{
			"host": "192.168.1.1",
			"port": 8080,
			"is_blocked": false,
			"request_count": 15
		},
		{
			"host": "192.168.1.2",
			"port": 8080,
			"is_blocked": true,
			"request_count": 5
		}
	]
}
```

#### GET /proxies/{proxy_id}

Retrieves detailed information about a specific proxy.

**Method:** GET

**Parameters:**

- `proxy_id` (string, required): Proxy identifier (host:port format)

**Response:**

- Status 200: Proxy details
- Status 404: Proxy not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"host": "192.168.1.1",
	"port": 8080,
	"is_blocked": false,
	"request_count": 15
}
```

#### POST /proxies

Adds a new proxy to the pool.

**Method:** POST

**Request Body:**

```json
{
	"host": "192.168.1.1",
	"port": 8080,
	"username": "admin",
	"password": "password",
	"protocol": "http"
}
```

**Response:**

- Status 200: Proxy added successfully
- Status 400: Invalid proxy data
- Status 500: Internal server error

**Response Body:**

```json
{
	"status": "success",
	"proxy_id": "192.168.1.1:8080"
}
```

#### PUT /proxies/{proxy_id}

Updates information for a specific proxy.

**Method:** PUT

**Parameters:**

- `proxy_id` (string, required): Proxy identifier (host:port format)

**Request Body:**

```json
{
	"host": "192.168.1.1",
	"port": 9090,
	"username": "newadmin",
	"password": "newpassword",
	"protocol": "http"
}
```

**Response:**

- Status 200: Proxy updated successfully
- Status 404: Proxy not found
- Status 500: Internal server error

#### DELETE /proxies/{proxy_id}

Deletes a specific proxy from the pool.

**Method:** DELETE

**Parameters:**

- `proxy_id` (string, required): Proxy identifier (host:port format)

**Response:**

- Status 200: Proxy deleted successfully
- Status 404: Proxy not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"status": "success"
}
```

#### POST /proxies/{proxy_id}/block

Manually blocks a specific proxy.

**Method:** POST

**Parameters:**

- `proxy_id` (string, required): Proxy identifier (host:port format)

**Response:**

- Status 200: Proxy blocked successfully
- Status 404: Proxy not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"status": "success"
}
```

#### POST /proxies/{proxy_id}/unblock

Manually unblocks a specific proxy.

**Method:** POST

**Parameters:**

- `proxy_id` (string, required): Proxy identifier (host:port format)

**Response:**

- Status 200: Proxy unblocked successfully
- Status 404: Proxy not found
- Status 500: Internal server error

**Response Body:**

```json
{
	"status": "success"
}
```
