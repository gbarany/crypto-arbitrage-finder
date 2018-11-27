from aiokafka import AIOKafkaProducer
import asyncio
import json
import time

loop = asyncio.get_event_loop()


async def send_one():

    producer = AIOKafkaProducer(loop=loop,bootstrap_servers='kafka.cryptoindex.me:9092',
                                value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    # Get cluster layout and initial topic/partition leadership information
    await producer.start()
    try:

        payload_json = {
            'test': 'Hello World!'
        }
        payload = json.dumps(payload_json)
    
        for i in range(100):
            await producer.send_and_wait("arbitrageDeals", payload)
            time.sleep(1)
    finally:
        # Wait for all pending messages to be delivered or expire.
        await producer.stop()


loop.run_until_complete(send_one())
