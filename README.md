# RabbitMQ client

**Этот пакет предназначен для работы с RabbitMQ с помощью либы aio_pika**

### Пример использования

```bash
pip install git+https://github.com/MiMoody/rmq_client.git
```

```python
from rmq_client import RMQClient, QueueSetting

class RMQExchange(Enum):
    PAYMENT = "payment_exchange"

class RMQQueue(Enum):
    SUCCESS_PAYMENTS = "success_payments"

SETTINGS_QUEUES = {
    RMQQueue.SUCCESS_PAYMENTS: QueueSetting(
        exchange=RMQExchange.PAYMENT,
        routing_key="success_payment",
        durable=True,
    )
}

rmq_client = RMQClient()

async def observe_task(body: bytes):
    ...

async def observe_queues():
    await rmq_client.init(
        host=settings.rmq.host,
        port=settings.rmq.port,
        username=settings.rmq.user,
        password=settings.rmq.password,
        queue_settings=SETTINGS_QUEUES
    )
    # consume
    await rmq_client.consume(observe_task, RMQQueue.SUCCESS_PAYMENTS)
    # publish
    await rmq_client.publish(exchange=RMQExchange.PAYMENT, queue=RMQQueue.SUCCESS_PAYMENTS, data=dict())

```
