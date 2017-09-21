import pytest
import pika

from mettle.settings import get_settings
from mettle.publisher import publish_event


@pytest.mark.xfail(reason="Need RabbitMQ fixture")
def test_long_routing_key():
    settings = get_settings()
    conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    chan = conn.channel()
    exchange = settings['state_exchange']
    chan.exchange_declare(exchange=exchange, type='topic', durable=True)

    with pytest.raises(ValueError):
        publish_event(chan, exchange, dict(
            description=None,
            tablename='a' * 8000,
            name="foo",
            pipeline_names=None,
            id=15,
            updated_by='vagrant',
        ))
