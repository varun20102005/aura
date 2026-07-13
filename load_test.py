import time
import urllib.request
import concurrent.futures

url = "http://localhost:8000/health/ready"
total_requests = 1000
concurrency = 50

def make_request(i):
    try:
        start = time.time()
        res = urllib.request.urlopen(url, timeout=5)
        status_code = res.getcode()
        elapsed = time.time() - start
        return {"status": status_code, "time": elapsed, "error": None}
    except Exception as e:
        return {"status": 0, "time": 0, "error": str(e)}

if __name__ == "__main__":
    print(f"Starting Load Test on {url}")
    print(f"Total Requests: {total_requests}, Concurrency: {concurrency}")
    
    start_total = time.time()
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, i) for i in range(total_requests)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
            
    total_time = time.time() - start_total
    
    successes = [r for r in results if r["status"] == 200]
    failures = [r for r in results if r["status"] != 200]
    
    times = [r["time"] for r in successes]
    avg_time = sum(times) / len(times) if times else 0
    max_time = max(times) if times else 0
    
    print("\n--- RESULTS ---")
    print(f"Total Time: {total_time:.2f} seconds")
    print(f"Requests per second: {total_requests / total_time:.2f}")
    print(f"Success: {len(successes)} / {total_requests}")
    print(f"Failures: {len(failures)} / {total_requests}")
    print(f"Average Latency: {avg_time*1000:.2f} ms")
    print(f"Max Latency: {max_time*1000:.2f} ms")
    
    if failures:
        status_val = failures[0].get('status')
        err_msg = failures[0].get('error') or f'HTTP {status_val}'
        print(f"Sample Error: {err_msg}")
