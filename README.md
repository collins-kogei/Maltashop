# MaltaShop Microservices Prototype

## Overview

MaltaShop is a prototype demonstrating an order-processing workflow using a microservices architecture. It contains an Order Service and a Notification Service that communicate asynchronously through RabbitMQ.

## Technologies

- Python 3.12
- FastAPI
- PostgreSQL
- RabbitMQ
- Docker and Docker Compose

## Architecture

The Order Service exposes a REST API and stores orders in its own PostgreSQL database. After an order is saved, it publishes an `OrderPlaced` event to RabbitMQ. The Notification Service consumes the event and records the notification in a separate PostgreSQL database.

## Requirements

- Docker Desktop with the Docker engine running
- Git

## Running the application

Clone the repository and enter its directory:

```bash
git clone https://github.com/collins-kogei/Maltashop.git
cd Maltashop
```

Build and start the services:

```bash
docker compose up --build -d
```

Check container status:

```bash
docker compose ps
```

Open the interactive Order Service API documentation at:

http://localhost:8000/docs

## Example request

Send a POST request to `/orders` with:

```json
{
  "product": "Samsung Galaxy 15",
  "quantity": 2
}
```

A successful request returns HTTP 201 and an order identifier.

## Viewing logs

```bash
docker compose logs --tail 50 order-service notification-service
```

## Stopping the application

```bash
docker compose down
```

The default Compose volumes preserve database and RabbitMQ data when containers are stopped and removed. Do not use `docker compose down -v` unless you intend to delete that data.

## Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Connection string for each service's own PostgreSQL database |
| `RABBITMQ_HOST` | RabbitMQ hostname used by the services |

The current Compose configuration supplies these variables. The credentials in this educational prototype are for local development only and must be replaced with securely managed secrets before production use.

## Current limitations

- The prototype does not yet implement a transactional outbox.
- Order, payment and inventory saga coordination is not implemented.
- Automated tests and production-grade authentication are still required.
- Message retry and dead-letter handling need further hardening.