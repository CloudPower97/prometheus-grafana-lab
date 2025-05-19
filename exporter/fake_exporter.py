
from prometheus_client import start_http_server, Gauge, Counter
import random, time

g = Gauge('fake_random_metric', 'A fake random gauge')
c = Counter('fake_counter', 'A fake counter')

if __name__ == '__main__':
    start_http_server(8000)
    while True:
        g.set(random.random() * 100)
        c.inc(random.randint(0, 5))
        time.sleep(5)
