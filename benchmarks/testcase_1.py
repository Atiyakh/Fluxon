import asyncio
import aiohttp
from time import time
from Fluxon.Connect import ConnectionHandler

NUM_REQUESTS = 400
DJANGO_URL = "http://127.0.0.1:8000/benchmark_test/"
FASTAPI_URL = "http://192.168.1.6:8001/benchmark_test/"
FLASK_URL = "http://127.0.0.1:8002/benchmark_test/"
FLUXON_HOST = "192.168.1.6"
FLUXON_PORT = 8080
FLUXON_REQUEST = {"action": "benchmark_test"}

async def test_django():
    """Benchmarking Django."""
    async with aiohttp.ClientSession() as session:
        start_time = time()
        tasks = [session.get(DJANGO_URL) for _ in range(NUM_REQUESTS)]
        responses = await asyncio.gather(*tasks)
        end_time = time()
        print(f"Django Benchmark:")
        print(f"  Total time for {NUM_REQUESTS} requests: {end_time - start_time:.2f}s")
        print(f"  Average response time: {(end_time - start_time) / NUM_REQUESTS:.4f}s")

async def test_flask():
    """Benchmarking Flask."""
    async with aiohttp.ClientSession() as session:
        start_time = time()
        tasks = [session.get(FLASK_URL) for _ in range(NUM_REQUESTS)]
        responses = await asyncio.gather(*tasks)
        end_time = time()
        print(f"Flask Benchmark:")
        print(f"  Total time for {NUM_REQUESTS} requests: {end_time - start_time:.2f}s")
        print(f"  Average response time: {(end_time - start_time) / NUM_REQUESTS:.4f}s")

async def test_fastapi():
    """Benchmarking FastAPI."""
    async with aiohttp.ClientSession() as session:
        start_time = time()
        tasks = [session.get(FASTAPI_URL) for _ in range(NUM_REQUESTS)]
        responses = await asyncio.gather(*tasks)
        end_time = time()
        print(f"FastAPI Benchmark:")
        print(f"  Total time for {NUM_REQUESTS} requests: {end_time - start_time:.2f}s")
        print(f"  Average response time: {(end_time - start_time) / NUM_REQUESTS:.4f}s")

async def test_fluxon():
    """Benchmarking Fluxon's AsyncServer using its built-in client interface."""
    conn = ConnectionHandler(host=FLUXON_HOST, port=FLUXON_PORT)
    start_time = time()
    tasks = [conn.send_request("benchmark_test", FLUXON_REQUEST) for _ in range(NUM_REQUESTS)]
    end_time = time()
    print(f"Fluxon Benchmark:")
    print(f"  Total time for {NUM_REQUESTS} requests: {end_time - start_time:.2f}s")
    print(f"  Average response time: {(end_time - start_time) / NUM_REQUESTS:.4f}s")

async def main():
    """Run all benchmarks."""
    print("Starting benchmarks...")
    await test_django()
    await test_fastapi()
    await test_flask()
    await test_fluxon()

asyncio.run(main())

# all results are from (11th Gen Intel(R) Core i7 2.80 GHz | 16 GB of RAM)

# Starting benchmarks...
# Django Benchmark:
#   Total time for 400 requests: 1.56s
#   Average response time: 0.0039s
# FastAPI Benchmark:
#   Total time for 400 requests: 0.70s
#   Average response time: 0.0018s
# Flask Benchmark:
#   Total time for 400 requests: 1.42s
#   Average response time: 0.0035s 
# Fluxon Benchmark:
#   Total time for 400 requests: 0.83s
#   Average response time: 0.0021s
