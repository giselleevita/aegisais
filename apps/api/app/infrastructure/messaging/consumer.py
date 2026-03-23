import json
import logging
from typing import Callable, Any, Dict
from app.infrastructure.cache.redis_client import get_redis_client
from app.core.config import settings

log = logging.getLogger("aegisais.messaging")

class RedisConsumer:
    """
    Consumes events from Redis Streams using Consumer Groups.
    """
    def __init__(self, stream_name: str, group_name: str, consumer_name: str):
        self.redis = get_redis_client()
        self.prefix = settings.redis_prefix
        self.stream_key = f"{self.prefix}:stream:{stream_name}"
        self.group_name = group_name
        self.consumer_name = consumer_name
        
        self._setup_group()

    def _setup_group(self):
        """Create the consumer group if it doesn't exist."""
        try:
            self.redis.xgroup_create(self.stream_key, self.group_name, id="0", mkstream=True)
        except Exception as e:
            if "BUSYGROUP" in str(e):
                log.debug("Consumer group %s already exists for %s", self.group_name, self.stream_key)
            else:
                log.error("Failed to setup consumer group: %s", e)

    def get_lag(self) -> int:
        """
        Get the number of messages pending in the stream.
        """
        try:
            return self.redis.xlen(self.stream_key)
        except Exception as e:
            log.error("Failed to get stream lag: %s", e)
            return 0

    def listen(self, callback: Callable[[str, Dict[str, Any]], None], on_tick: Callable[[], None] = None, block_ms: int = 1000, count: int = 10):
        """
        Listen for messages in a blocking loop.
        
        Args:
            callback: Function to call for each message: func(message_id, data)
            on_tick: Optional function to call every loop iteration (useful for metrics)
            block_ms: How long to block waiting for new messages
            count: Max messages to read per batch
        """
        log.info("Starting consumer %s for group %s on %s", self.consumer_name, self.group_name, self.stream_key)
        
        while True:
            try:
                if on_tick:
                    on_tick()

                # Read from the group. ">" means only new messages that haven't been delivered
                # to any other consumer in this group.
                messages = self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=count,
                    block=block_ms
                )
                
                if not messages:
                    continue
                
                for stream, msg_list in messages:
                    for msg_id, payload_dict in msg_list:
                        try:
                            # Payload is in 'payload' field as JSON string
                            data = json.loads(payload_dict["payload"])
                            callback(msg_id, data)
                            
                            # Acknowledge the message so it's removed from PEL
                            self.redis.xack(self.stream_key, self.group_name, msg_id)
                        except Exception as e:
                            log.error("Failed to process message %s: %s", msg_id, e)
                            # In production, we might want to move these to a Dead Letter Queue 
                            # or just leave them un-acked for a retry.
            except Exception as e:
                log.error("Error reading from stream: %s", e)
