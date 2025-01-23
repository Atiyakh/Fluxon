import asyncio
import aiohttp
from time import time
from Fluxon.Connect import ConnectionHandler

NUM_REQUESTS = 100
DJANGO_URL = "http://127.0.0.1:8000/benchmark_test/"
FLUXON_HOST = "127.0.0.1"
FLUXON_PORT = 8080
FLUXON_REQUEST = {"action": "benchmark_test"}

async def test_django():
    """Benchmarking the Django"""
    async with aiohttp.ClientSession() as session:
        start_time = time()
        tasks = [session.get(DJANGO_URL) for _ in range(NUM_REQUESTS)]
        responses = await asyncio.gather(*tasks)
        end_time = time()
        print(f"Django Benchmark:")
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
    """Run both benchmarks."""
    print("Starting benchmarks...")
    await test_django()
    await test_fluxon()

asyncio.run(main())

# results from the same hardware (my local machine)

# Starting benchmarks...
# Django Benchmark:
#   Total time for 100 requests: 0.61s
#   Average response time: 0.0061s
# Fluxon Benchmark:
#   Total time for 100 requests: 0.46s
#   Average response time: 0.0046s

# That makes Fluxon's AsyncServer 21.67% faster then Django's endpoint!

## and these are the views tested for this benchmarks
# Django
'''
def benchmark(request):
    return HttpResponse(("0"*50_000))
'''
# Fluxon
'''
def benchmark_test(request):
    return "0"*50_000
'''
