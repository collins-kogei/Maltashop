
import json
import os
import time
import logging

import pika
import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("notification-service")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://notifications:notify_pass@notification-db:5432/notifications",
)


def save_notification(event):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    event_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                INSERT INTO notifications (event_id, order_id, message)
                VALUES (%s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (
                    event["event_id"],
                    event["order_id"],
                    f"Order {event['order_id']} was placed",
                ),
            )
        conn.commit()


def main():
    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    heartbeat=30,
                    blocked_connection_timeout=60,
                )
            )
            channel = connection.channel()
            channel.queue_declare(
                queue="order_events",
                durable=True,
            )
            channel.basic_qos(prefetch_count=1)

            def handle_event(ch, method, properties, body):
                try:
                    event = json.loads(body)
                    save_notification(event)

                    correlation_id = event.get(
                        "correlation_id", "missing"
                    )

                    logger.info(
                        "Notification processed order_id=%s "
                        "event_id=%s correlation_id=%s",
                        event["order_id"],
                        event["event_id"],
                        correlation_id,
                    )

                    ch.basic_ack(
                        delivery_tag=method.delivery_tag
                    )

                except Exception:
                    logger.exception("Event processing failed")
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True,
                    )

            channel.basic_consume(
                queue="order_events",
                on_message_callback=handle_event,
            )

            logger.info("Waiting for order events")
            channel.start_consuming()

        except Exception:
            logger.exception(
                "Consumer connection failed; retrying"
            )
            time.sleep(5)

        finally:
            if connection is not None and connection.is_open:
                connection.close()


if __name__ == "__main__":
    main()
