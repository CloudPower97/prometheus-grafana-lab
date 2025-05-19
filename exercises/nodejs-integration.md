# Exercise 1: Instrumenting Your Express App

**Objective**
Add Prometheus metrics to the existing Node.js/Express server and verify they are exposed.

---

## Steps

1. **Install the client library**

   ```bash
   cd node-app
   npm install prom-client
   ```

2. **Enable default metrics**
   In your `app.js`, add at the top:

   ```js
   const client = require("prom-client");
   client.collectDefaultMetrics({ timeout: 5000 });
   ```

3. **Add a request counter**

   ```js
   const httpRequests = new client.Counter({
     name: "http_requests_total",
     help: "Total HTTP requests",
     labelNames: ["method", "route", "status_code"],
   });
   ```

4. **Middleware for counting**

   ```js
   app.use((req, res, next) => {
     const end = res.end;
     res.end = function (chunk, encoding) {
       httpRequests.inc({
         method: req.method,
         route: req.route ? req.route.path : req.path,
         status_code: res.statusCode,
       });
       end.apply(this, [chunk, encoding]);
     };
     next();
   });
   ```

5. **Expose `/metrics` endpoint**

   ```js
   app.get("/metrics", async (req, res) => {
     res.set("Content-Type", client.register.contentType);
     res.end(await client.register.metrics());
   });
   ```

6. **Test output**

   ```bash
   docker-compose up -d node-app
   curl http://localhost:3001/metrics
   ```

---

## Hints

- Default metrics include CPU, memory, event loop lag, etc.
- Ensure your server rebuilds after code changes (`docker-compose up -d --build node-app`).

---

## Your Notes / Answers

1. ## Which default metrics did you see?

2. ## What labels appear on `http_requests_total`?

---

# Exercise 2: Writing PromQL for Node.js Metrics

**Objective**
Query the newly exposed Node.js metrics in Prometheus.

---

## Steps

1. **Open Prometheus UI**
   [http://localhost:9090](http://localhost:9090)
2. **Query CPU usage**

   ```
   process_cpu_seconds_total
   ```

3. **Query memory RSS**

   ```
   process_resident_memory_bytes
   ```

4. **Compute request rate by route**

   ```
   sum by (route)(rate(http_requests_total[5m]))
   ```

5. **Filter successful requests**

   ```
   sum by (route)(rate(http_requests_total{status_code="200"}[5m]))
   ```

---

## Hints

- Use `sum by(...)` to aggregate metrics by label.
- Adjust the time window `[5m]` as needed.

---

## Your Notes / Answers

1. ## What is the approximate request rate for each route?

2. ## How does CPU usage compare to memory usage?

---

# Exercise 3: Measuring Request Latency

**Objective**
Instrument and analyze HTTP request durations.

---

## Steps

1. **Add a Histogram**

   ```js
   const httpDuration = new client.Histogram({
     name: "app_request_duration_seconds",
     help: "Request duration in seconds",
     labelNames: ["method", "route", "status_code"],
     buckets: [0.1, 0.3, 1, 5],
   });
   ```

2. **Wrap route handlers**

   ```js
   app.use((req, res, next) => {
     const end = httpDuration.startTimer({
       method: req.method,
       route: req.path,
     });
     res.on("finish", () => {
       end({ status_code: res.statusCode });
     });
     next();
   });
   ```

3. **Rebuild and restart**

   ```bash
   docker-compose up -d --build node-app
   ```

4. **Query latency in Prometheus**

   ```
   histogram_quantile(0.95, sum by (le)(rate(app_request_duration_seconds_bucket[5m])))
   ```

5. **Visualize in Grafana**
   Create a panel with the above query.

---

## Hints

- `histogram_quantile` computes percentiles from bucketed data.
- Confirm bucket labels via `app_request_duration_seconds_bucket`.

---

## Your Notes / Answers

1. ## What is the 95th percentile latency?

2. ## Which bucket has the most observations?

---

# Exercise 4: Grafana Dashboard for Node.js Metrics

**Objective**
Build a Grafana dashboard to monitor Node.js application performance.

---

## Steps

1. **Import a dashboard**

   - In Grafana, click **+ → Dashboard → Import**.
   - Use JSON from `grafana/provisioning/dashboards/node_app.json` (create if missing).

2. **Panel: CPU Usage**
   Query: `rate(process_cpu_seconds_total{job="node_app"}[1m])`.

3. **Panel: Memory Usage**
   Query: `process_resident_memory_bytes{job="node_app"}`.

4. **Panel: Request Rate**
   Query: `sum by (route)(rate(http_requests_total{job="node_app"}[1m]))`.

5. **Panel: Latency**
   Query: `histogram_quantile(0.95, sum by (le)(rate(app_request_duration_seconds_bucket{job="node_app"}[5m])))`.

---

## Hints

- Use **Time series** panels for numeric metrics.
- Add titles and descriptions for clarity.

---

## Your Notes / Answers

1. ## Which panel shows the most variability?

2. ## Did you group by any labels?

---

# Exercise 5: Alerting on Error Rate in Prometheus

**Objective**
Define an alert that fires when the 5m error rate exceeds a threshold.

---

## Steps

1. **Add an error counter**
   In your `app.js`, import and configure a new counter for 5xx errors:

   ```js
   const client = require("prom-client");
   // existing default metrics and httpRequests...

   // Add this below your other metrics:
   const errorCounter = new client.Counter({
     name: "http_error_requests_total",
     help: "Total HTTP 5xx error requests",
     labelNames: ["method", "route", "status_code"],
   });
   ```

   Then update your counting middleware to increment this counter when the response status is 500 or above:

   ```js
   app.use((req, res, next) => {
     const end = res.end;
     res.end = function (chunk, encoding) {
       if (res.statusCode >= 500) {
         errorCounter.inc({
           method: req.method,
           route: req.route ? req.route.path : req.path,
           status_code: res.statusCode,
         });
       }
       httpRequests.inc({
         /* existing counter code */
       });
       end.apply(this, [chunk, encoding]);
     };
     next();
   });
   ```

2. **Create alert rule**
   In `prometheus/rules/node_alerts.yml`:

   ```yaml
   groups:
     - name: node_error_alerts
       rules:
         - alert: HighErrorRate
           expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.1
           for: 2m
           labels:
             severity: critical
           annotations:
             summary: "High 5xx error rate detected"
             description: "Error rate above 0.1 rps for 2 minutes."
   ```

3. **Include rule file**
   Update `rule_files:` in `prometheus.yml`.

4. **Reload Prometheus**

   ```bash
   docker-compose exec prometheus kill -HUP 1
   ```

5. **Verify**

   - Restart Prometheus and hit your error route to generate 5xx errors.
   - In Prometheus UI, click **Alerts** and confirm `HighErrorRate` appears when errors exceed the threshold.

6. **Simulate error traffic**
   To produce a stream of 500 errors for testing, add a test route to `app.js`:

   ```js
   app.get("/error", (req, res) => {
     res.status(500).send("Internal Server Error");
   });
   ```

   Then run in a separate terminal:

   ```bash
   while true; do
      curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3001/error
      sleep 1
   done
   ```

This continuously triggers the error counter so you can observe the alert firing in Grafana.

Generate 5xx errors and check **Alerts** in UI.

7.  **Visualize the alert in Grafana**  
    You can view the alert status directly in a Grafana panel without needing Alertmanager:

    1. Create a new **Time series** panel on any dashboard.
    2. Use this Prometheus query:

       ```promql
       ALERTS{alertname="HighErrorRate",alertstate="firing"}
       ```

    3. Configure the panel: set **Unit** to `none` or `short`, adjust the **Legend** to show `alertname` and `alertstate`.
    4. Click **Apply** and save your dashboard.

When the `HighErrorRate` alert fires, this panel shows `1`, otherwise it shows `0`. This way you have a near real-time view of your Prometheus alerts in Grafana.

---

## Hints

- Regex `5..` matches any 5xx code.
- Use `rate(...[5m])` for per-second error rate.

---

## Your Notes / Answers

1. Did the alert fire as expected?

-

2. How many errors per second triggered it?

- ***

## Hints

- Regex `5..` matches any 5xx code.
- Use `rate(...[5m])` for per-second error rate.

---

## Your Notes / Answers

1. Did the alert fire as expected?

-

2. How many errors per second triggered it?

-
