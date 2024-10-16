from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import Callable, Coroutine, TypeVar, Generic, Dict, cast
import asyncio

import orjson
from aio_pika import connect_robust, Message
from aio_pika.abc import (
    AbstractExchange,
    AbstractQueue,
    AbstractRobustChannel,
    AbstractRobustConnection,
    AbstractRobustChannel,
    AbstractIncomingMessage,
)
from aio_pika.exceptions import ChannelNotFoundEntity

TExchange = TypeVar("TExchange", bound=Enum)
TQueue = TypeVar("TQueue", bound=Enum)


@dataclass
class QueueSetting(Generic[TExchange]):
    exchange: TExchange
    routing_key: str
    durable: bool


class RMQClient(Generic[TExchange, TQueue]):
    """RMQClient работает только уже с заранее созданными exchanges"""

    _host: str
    _port: int
    _username: str
    _password: str
    _connection: AbstractRobustConnection
    _channel: AbstractRobustChannel
    _exchanges: dict[TExchange, AbstractExchange]
    _queues: dict[TQueue, AbstractQueue]
    _semaphore: asyncio.Semaphore

    async def init(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        queue_settings: Dict[TQueue, QueueSetting[TExchange]],
        max_concurrent_task: int = 100,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._exchanges = {}
        self._queues = {}
        self._queue_settings: Dict[TQueue, QueueSetting[TExchange]] = queue_settings
        self._semaphore = asyncio.Semaphore(value=max_concurrent_task)
        self._connection = await connect_robust(
            host=self._host,
            port=self._port,
            login=self._username,
            password=self._password,
        )
        self._channel = cast(AbstractRobustChannel, await self._connection.channel())
        await self._declare_exchanges()
        await self._declare_and_bind_queues()

    async def _declare_exchanges(self) -> None:
        for settings in self._queue_settings.values():
            remote_exchange: AbstractExchange = await self._channel.get_exchange(
                name=settings.exchange.value
            )
            self._exchanges[settings.exchange] = remote_exchange

    async def _declare_and_bind_queues(self) -> None:
        for queue_name, queue_settings in self._queue_settings.items():
            try:
                queue: AbstractQueue = await self._channel.get_queue(
                    name=queue_name.value, ensure=True
                )
            except ChannelNotFoundEntity:
                await self._channel.reopen()
                queue: AbstractQueue = await self._channel.declare_queue(
                    name=queue_name.value, durable=queue_settings.durable
                )
                remote_exchange = self.get_exchange(queue_settings.exchange)
                await queue.bind(
                    exchange=remote_exchange, routing_key=queue_settings.routing_key
                )
            self._queues[queue_name] = queue

    def get_exchange(self, exchange_name: TExchange) -> AbstractExchange:
        if exchange_name not in self._exchanges:
            raise ValueError("Exchange не найдено!")
        return self._exchanges[exchange_name]

    def get_queue(self, queue_name: TQueue) -> AbstractQueue:
        if queue_name not in self._queues:
            raise ValueError("Queue не найдено!")
        return self._queues[queue_name]

    async def publish(self, exchange: TExchange, queue: TQueue, data: dict) -> None:
        _exchange: AbstractExchange = self.get_exchange(exchange_name=exchange)
        _routing_key: str = self._queue_settings[queue].routing_key
        await _exchange.publish(
            message=Message(body=orjson.dumps(data)), routing_key=_routing_key
        )

    async def __process_callback(
        self,
        callback: Callable[[bytes], Coroutine],
        incoming_message: AbstractIncomingMessage,
    ) -> None:
        try:
            async with self._semaphore:
                await callback(incoming_message.body)
            await incoming_message.ack()
        except:
            await incoming_message.reject()

    async def __queue_waiter(
        self,
        incoming_message: AbstractIncomingMessage,
        callback: Callable[[bytes], Coroutine],
    ) -> None:
        await self._semaphore.acquire()
        asyncio.create_task(
            coro=self.__process_callback(
                callback=callback, incoming_message=incoming_message
            )
        )

    async def consume(
        self,
        callback: Callable[[bytes], Coroutine],
        queue: TQueue,
    ) -> None:
        if queue not in self._queues:
            raise ValueError("Очередь не найдена!")
        _queue: AbstractQueue = self._queues[queue]
        await _queue.consume(callback=partial(self.__queue_waiter, callback=callback))

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
