import time
time.sleep(20)  # E2E driver head start; no external API — pure compute
fib = [0, 1]
for _ in range(28):
    fib.append(fib[-1] + fib[-2])
primes = [x for x in range(2, 200) if all(x % p for p in range(2, int(x ** 0.5) + 1))]
md = "fib(30)=%d; liczb pierwszych <200: %d (max %d)" % (fib[-1], len(primes), primes[-1])
results = {"fib30": fib[-1], "primes_count": len(primes), "max_prime": primes[-1]}
