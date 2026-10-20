
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import pika
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, DateTime
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://orders:orderspass@localhost:5432/orders",
)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("order-service")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    product: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PLACED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class OrderRequest(BaseModel):
    product: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0, le=1000)


app = FastAPI(title="MaltaShop Order Service")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


def publish_order_event(
    order_id, product, quantity, created_at, correlation_id
):
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "OrderPlaced",
        "order_id": order_id,
        "correlation_id": correlation_id,
        "product": product,
        "quantity": quantity,
        "created_at": created_at.isoformat(),
    }

    for attempt in range(5):
        connection = None
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    heartbeat=30,
                    connection_attempts=3,
                    retry_delay=2,
                )
            )

            channel = connection.channel()
            channel.queue_declare(
                queue="order_events",
                durable=True,
            )
            channel.confirm_delivery()

            channel.basic_publish(
                exchange="",
                routing_key="order_events",
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    message_id=event["event_id"],
                    correlation_id=correlation_id,
                ),
                mandatory=True,
            )

            logger.info(
                "OrderPlaced event published order_id=%s "
                "event_id=%s correlation_id=%s",
                order_id,
                event["event_id"],
                correlation_id,
            )
            return

        except Exception:
            logger.exception(
                "Event publishing attempt %s failed", attempt + 1
            )
            if attempt == 4:
                raise
            time.sleep(2)

        finally:
            if connection is not None and connection.is_open:
                connection.close()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "order-service"}


@app.post("/orders", status_code=201)
def place_order(request: OrderRequest, http_request: Request):
    # Reuse a valid incoming correlation ID or create a new one.
    incoming_id = http_request.headers.get("X-Correlation-ID")
    correlation_id = incoming_id or str(uuid.uuid4())

    order_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    logger.info(
        "Order request received correlation_id=%s",
        correlation_id,
    )

    order = Order(
        id=order_id,
        product=request.product,
        quantity=request.quantity,
        status="PLACED",
        created_at=created_at,
    )

    try:
        with SessionLocal() as session:
            session.add(order)
            session.commit()
    except Exception as exc:
        logger.exception(
            "Order database save failed correlation_id=%s",
            correlation_id,
        )
        raise HTTPException(
            status_code=503,
            detail="Order could not be saved",
        ) from exc

    try:
        publish_order_event(
            order_id,
            request.product,
            request.quantity,
            created_at,
            correlation_id,
        )
    except Exception as exc:
        logger.exception(
            "Order saved but event publishing failed "
            "correlation_id=%s order_id=%s",
            correlation_id,
            order_id,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Order was saved but event publishing failed",
                "order_id": order_id,
                "correlation_id": correlation_id,
            },
        ) from exc

    return {
        "order_id": order_id,
        "correlation_id": correlation_id,
        "product": request.product,
        "quantity": request.quantity,
        "status": "PLACED",
        "created_at": created_at.isoformat(),
    }
