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

   ```bash
   docker compose up --build
   ```

   This will start the following services:
   - PostgreSQL database on port 5432
   - Redis on port 6379
   - Migration service (runs database migrations)
   - API service on port 8000
   - Telegram bot

4. The bot will be ready to receive commands once all services are healthy.

### Local Development Setup

1. Install Python 3.12 or higher.

2. Install dependencies using uv:

   ```bash
   pip install uv
   uv sync
   ```

3. Install Playwright browsers:

   ```bash
   uv run playwright install chromium
   uv run playwright install-deps chromium
   ```

4. Set up PostgreSQL and Redis locally, or use Docker for these services:

   ```bash
   docker run -d --name postgres -e POSTGRES_PASSWORD=password -e POSTGRES_DB=instagram_parser -p 5432:5432 postgres:18
   docker run -d --name redis -p 6379:6379 redis:8
   ```

5. Create a `.env` file with the required environment variables.

6. Run database migrations:

   ```bash
   uv run alembic upgrade head
   ```

7. Start the API service:

   ```bash
   uv run -m app.main
   ```

8. In a separate terminal, start the bot:

   ```bash
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

### User Management Endpoints

#### GET /users/{tg_id}/limit

Check if a Telegram user can perform more analyses.

**Method:** GET

**Parameters:**

- `tg_id` (integer, required): Telegram user ID

**Response:**

- Status 200: Limit information
- Status 404: User not found
- Status 500: Internal server error

**Response Body:**

```json
{
 "can_parse": true,
 "remaining": 50,
 "max_reels": 10
}
```

**Fields:**

- `can_parse` (boolean): Whether user can perform more analyses
- `remaining` (integer): Remaining analyses (-1 for unlimited)
- `max_reels` (integer): Maximum reels per request for user's plan

**Example Request (cURL):**

```bash
curl -X GET "http://localhost:8000/users/123456789/limit"
```

#### POST /users/{tg_id}/register

Register a new Telegram user with the TEST plan.

**Method:** POST

**Parameters:**

- `tg_id` (integer, required): Telegram user ID

**Response:**

- Status 200: User registered or already exists
- Status 404: Test plan not found
- Status 500: Internal server error

**Response Body:**

```json
{
 "status": "created",
 "user": {
  "id": 1,
  "telegram_id": 123456789,
  "plan_id": 1,
  "analyses_used": 0,
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-02-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
 }
}
```

**Example Request (cURL):**

```bash
curl -X POST "http://localhost:8000/users/123456789/register"
```

#### GET /users/{tg_id}/profile

Get user's current plan, usage, and billing period information.

**Method:** GET

**Parameters:**

- `tg_id` (integer, required): Telegram user ID

**Response:**

- Status 200: Profile information
- Status 404: User not found
- Status 500: Internal server error

**Response Body:**

```json
{
 "plan_name": "Base",
 "analyses_used": 5,
 "monthly_analyses": 100,
 "remaining": 95,
 "max_reels_per_request": 10,
 "period_start": "2024-01-01T00:00:00Z",
 "period_end": "2024-02-01T00:00:00Z",
 "has_paid_plan": true
}
```

**Example Request (cURL):**

```bash
curl -X GET "http://localhost:8000/users/123456789/profile"
```

### Plan Management Endpoints

#### GET /plans

Retrieve all active subscription plans.

**Method:** GET

**Response:**

- Status 200: List of plans
- Status 500: Internal server error

**Response Body:**

```json
{
 "total": 3,
 "plans": [
  {
   "id": 1,
   "name": "Test",
   "price": 0,
   "price_rub": 0.0,
   "monthly_analyses": 5,
   "max_reels_per_request": 3,
   "is_active": true,
   "created_at": "2024-01-01T00:00:00Z",
   "updated_at": "2024-01-01T00:00:00Z"
  },
  {
   "id": 2,
   "name": "Base",
   "price": 99000,
   "price_rub": 990.0,
   "monthly_analyses": 100,
   "max_reels_per_request": 10,
   "is_active": true,
   "created_at": "2024-01-01T00:00:00Z",
   "updated_at": "2024-01-01T00:00:00Z"
  }
 ]
}
```

**Example Request (cURL):**

```bash
curl -X GET "http://localhost:8000/plans"
```

#### POST /plans

Create a new subscription plan.

**Method:** POST

**Request Body:**

```json
{
 "name": "Base",
 "price_rub": 990.0,
 "monthly_analyses": 100,
 "max_reels_per_request": 10,
 "is_active": true
}
```

**Parameters:**

- `name` (string, required): Plan type - `Test`, `Base`, or `Unlimited`
- `price_rub` (float, required): Price in rubles
- `monthly_analyses` (integer, optional): Monthly limit (null for unlimited)
- `max_reels_per_request` (integer, required): Maximum reels per request
- `is_active` (boolean, optional): Default true

**Response:**

- Status 201: Plan created successfully
- Status 400: Plan with this name already exists
- Status 500: Internal server error

**Response Body:**

```json
{
 "id": 2,
 "name": "Base",
 "price": 99000,
 "price_rub": 990.0,
 "monthly_analyses": 100,
 "max_reels_per_request": 10,
 "is_active": true,
 "created_at": "2024-01-01T00:00:00Z",
 "updated_at": "2024-01-01T00:00:00Z"
}
```

**Example Request (cURL):**

```bash
curl -X POST "http://localhost:8000/plans" \
  -H "Content-Type: application/json" \
  -d '{"name": "Base", "price_rub": 990.0, "monthly_analyses": 100, "max_reels_per_request": 10}'
```

#### PATCH /plans/{plan_id}

Update specific fields of an existing plan.

**Method:** PATCH

**Parameters:**

- `plan_id` (integer, required): Plan ID

**Request Body (all fields optional):**

```json
{
 "price_rub": 1490.0,
 "monthly_analyses": 150
}
```

**Response:**

- Status 200: Plan updated successfully
- Status 404: Plan not found
- Status 500: Internal server error

**Response Body:**

```json
{
 "id": 2,
 "name": "Base",
 "price": 149000,
 "price_rub": 1490.0,
 "monthly_analyses": 150,
 "max_reels_per_request": 10,
 "is_active": true,
 "created_at": "2024-01-01T00:00:00Z",
 "updated_at": "2024-01-02T00:00:00Z"
}
```

**Example Request (cURL):**

```bash
curl -X PATCH "http://localhost:8000/plans/2" \
  -H "Content-Type: application/json" \
  -d '{"price_rub": 1490.0}'
```

### Payment Endpoints (Robokassa Integration)

#### POST /payments/create

Create a Robokassa payment for plan purchase.

**Method:** POST

**Request Body:**

```json
{
 "tg_id": 123456789,
 "plan_type": "Base"
}
```

**Parameters:**

- `tg_id` (integer, required): Telegram user ID
- `plan_type` (string, required): Plan type - `Test`, `Base`, or `Unlimited`

**Response:**

- Status 200: Payment created successfully
- Status 400: User already has an active paid plan
- Status 404: Plan or user not found
- Status 500: Internal server error

**Response Body:**

```json
{
 "payment_url": "https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=...",
 "invoice_id": "INV_123456789_1708092300"
}
```

**Example Request (cURL):**

```bash
curl -X POST "http://localhost:8000/payments/create" \
  -H "Content-Type: application/json" \
  -d '{"tg_id": 123456789, "plan_type": "Base"}'
```

#### POST /payments/result

Handle Robokassa ResultURL callback. This endpoint receives form-data from Robokassa, not JSON.

**Method:** POST

**Request (form-data):**

```plain
OutSum=990.00
InvId=INV_123456789_1708092300
SignatureValue=a1b2c3d4e5f6...
```

**Parameters:**

- `OutSum` (string): Payment amount
- `InvId` (string): Invoice ID
- `SignatureValue` (string): MD5 signature for verification

**Response:**

- Status 200: Payment processed successfully - returns `OK{InvId}`
- Status 400: Bad signature
- Status 404: Payment or user not found

**Response Body (success):**

```plain
OKINV_123456789_1708092300
```

## Robokassa Payment Integration

### Overview

The system integrates with Robokassa payment gateway to handle subscription purchases. The payment flow involves three parties: the Telegram bot, the API service, and Robokassa.

### Payment Flow

1. User requests to purchase a plan via the Telegram bot
2. Bot calls `POST /payments/create` with user's Telegram ID and plan type
3. API validates the request:
   - Checks plan exists and is active
   - Checks user exists
   - Verifies user does not already have a paid plan
4. API creates a payment record with `pending` status
5. API generates a Robokassa payment link using MD5 signature
6. API returns the payment URL to the bot
7. Bot displays the payment link to the user
8. User completes payment on Robokassa's website
9. Robokassa sends a callback to `POST /payments/result`
10. API verifies the MD5 signature using Password2
11. API marks payment as `paid` and upgrades user's plan
12. API responds with `OK{InvId}` to confirm processing

### Signature Generation

Payment links are secured using MD5 signatures. The signature is generated from:

```plain
MD5({MerchantLogin}:{amount:.2f}:{InvId}:{Password1})
```

For result verification:

```plain
MD5({OutSum}:{InvId}:{Password2})
```

### Invoice ID Format

Invoice IDs follow the pattern: `INV_{telegram_id}_{timestamp}`

Example: `INV_123456789_1708092300`

### Configuration

The following environment variables are required for Robokassa integration:

| Variable | Description |
| ---------- | ------------- |
| `ROBOKASSA_LOGIN` | Merchant login identifier |
| `ROBOKASSA_PASSWORD1` | Password for signature generation |
| `ROBOKASSA_PASSWORD2` | Password for result verification |
| `ROBOKASSA_PAYMENT_URL` | Payment page URL |

### Plan Types

| Type | Description |
| ------ | ------------- |
| `Test` | Free trial plan with limited features |
| `Base` | Standard paid plan |
| `Unlimited` | Premium plan with unlimited analyses |
