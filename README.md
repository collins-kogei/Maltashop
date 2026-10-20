# MaltaShop Microservices Prototype

## 1. Overview

MaltaShop is an educational prototype demonstrating an order-processing workflow using a microservices architecture. It consists of an Order Service and a Notification Service that communicate asynchronously through RabbitMQ.

The prototype demonstrates REST API communication, independent data storage, asynchronous event messaging, correlation IDs for tracing requests, and containerised deployment using Docker Compose.

## 2. Technologies Used

- Python 3.12
- FastAPI
- PostgreSQL
- RabbitMQ
- SQLAlchemy
- Psycopg
- Pika
- Docker and Docker Compose

## 3. System Architecture

The prototype contains two application services and three supporting infrastructure services.

### Order Service

The Order Service exposes a REST API for placing orders. It validates incoming requests and saves accepted orders in its own PostgreSQL database. After saving an order, it publishes an `OrderPlaced` event to RabbitMQ.

### Notification Service

The Notification Service consumes `OrderPlaced` events from RabbitMQ and records notifications in its own PostgreSQL database. It logs the order ID, event ID and correlation ID to support event tracing.

### Supporting Infrastructure

- **Order database:** Stores order records.
- **Notification database:** Stores notification records independently.
- **RabbitMQ:** Provides asynchronous communication between the application services.

The correlation ID helps trace an order request through event publishing and notification processing.

## 4. Requirements

- Docker Desktop with the Docker engine running
- Git
- A web browser

## 5. Running the Application

Clone the repository:

```bash
git clone https://github.com/collins-kogei/Maltashop.git
cd Maltashop
```

Build and start the application:

```bash
docker compose up --build -d
```

Check the status of the containers:

```bash
docker compose ps
```

The application consists of five containers: the Order Service, Notification Service, two PostgreSQL databases and RabbitMQ.

Open the interactive API documentation:

http://localhost:8000/docs

The RabbitMQ management interface is available at:

http://localhost:15672

Use the default local development credentials configured by the RabbitMQ image if prompted.

## 6. Example API Request

Send a `POST` request to `/orders` using the following JSON body:

```json
{
  "product": "Wireless Mouse",
  "quantity": 2
}
```

A successful request returns HTTP `201 Created` and includes the order ID, correlation ID, product, quantity, status and creation timestamp.

The API validates the request. For example, a quantity of zero is rejected with HTTP `422 Unprocessable Entity`.

## 7. Viewing Logs

View recent logs from both application services:

```bash
docker compose logs --tail 50 order-service notification-service
```

To view event publishing messages:

```bash
docker compose logs --since 30m order-service
```

To view notification processing messages:

```bash
docker compose logs --since 30m notification-service
```

Compare the correlation IDs in the two services' logs to trace an order through the asynchronous workflow.

## 8. Verifying Database Records

To view recent orders:

```bash
docker compose exec order-db psql -U orders -d orders -c "SELECT id, product, quantity, status, created_at FROM orders ORDER BY created_at DESC LIMIT 5;"
```

To view recent notifications:

```bash
docker compose exec notification-db psql -U notifications -d notifications -c "SELECT event_id, order_id, message, created_at FROM notifications ORDER BY created_at DESC LIMIT 5;"
```

The order ID in a notification record should match the corresponding order record.

## 9. Testing Performed

The following manual tests were performed during development:

| Test | Expected result | Observed result |
|---|---|---|
| Submit a valid order | HTTP 201 response | Passed |
| Submit an order with quantity zero | HTTP 422 response | Passed |
| Publish an order event | Event published to RabbitMQ | Passed |
| Consume an order event | Notification recorded | Passed |
| Trace an order across services | Matching correlation ID | Passed |
| Check database separation | Orders and notifications stored in separate databases | Passed |
| Validate Docker Compose configuration | No configuration errors | Passed |
| Check container status | Five containers running; databases and RabbitMQ healthy | Passed |

These are manual development tests, not a substitute for an automated test suite.

## 10. Stopping the Application

Stop and remove the containers:

```bash
docker compose down
```

The default named volumes preserve database and RabbitMQ data when containers are removed. Do not use `docker compose down -v` unless you intend to delete the stored volume data.

## 11. Environment Variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Connection string for each service's PostgreSQL database |
| `RABBITMQ_HOST` | RabbitMQ hostname used by the services |

The Docker Compose configuration supplies these variables. The credentials used in this educational prototype are intended for local development only and must be replaced with securely managed secrets before production use.

## 12. Current Limitations and Future Improvements

- A transactional outbox has not been implemented. Saving an order and publishing its event are separate operations, so a failure between them could leave an order without a corresponding event.
- Saga coordination for distributed transactions involving payment or inventory is not implemented.
- Automated unit, integration and end-to-end tests are still required.
- Authentication, authorisation and production-grade secret management are not implemented.
- Message retry and dead-letter handling require further hardening.
- Monitoring, metrics, structured tracing and production deployment configuration could be improved.

## 13. Repository

GitHub repository: https://github.com/collins-kogei/Maltashop
