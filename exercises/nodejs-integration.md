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

   > 📝 What is a bucket?
   >
   > A bucket is a range container counting how many observations fall below or equal to its upper bound.
   > Each value in the buckets array defines the upper limit of that range.
   >
   > For each threshold in buckets (0.1 s, 0.3 s, …, 5 s) plus a final “+Inf” bucket, the client automatically exposes a metric called: `app_request_duration_seconds_bucket{…, le="<threshold>", …}`
   >
   > Each of those is a cumulative counter: it increments by one whenever a request’s duration is less than or equal to that threshold.
   > Prometheus periodically “scrapes” (fetches) your /metrics endpoint to collect current values. In this examples we instructed Prometheus to scrape every 15s.
   > Each scrape produces a sample (essentially a pair): `<value> @ <timestamp>` where `<value>` is the current counter and `<timestamp>` is when the scrape happened (Unix time with fractions).

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

5. **Raw Buckets Query**

   ```promql
   app_request_duration_seconds_bucket[5m]
   ```

   Purpose: View the number of observations per bucket over the last 5 minutes.

   Output: Time series with label le indicating each bucket’s upper bound.

   > 📝 Note
   > When you run a PromQL query like the one above, you ask Prometheus for all samples of that time-series over the last five minutes.
   > Prometheus replies with lines such as: 1 @ 1747721597.399, 1 @ 1747721612.397, ...etc.
   > The “1” is the bucket’s counter at that scrape, the “@ timestamp” is when it was collected.
   > These lines are stacked (“impilati”) because you’re looking at every scrape in that window.
   > Because you scrape every 15 seconds, in any given time window of length W seconds you’ll see roughly W / 15 samples.
   > A [1m] (60 s) query returns about 60 s ÷ 15 s = 4 samples.
   > A [5m] (300 s) query returns about 300 s ÷ 15 s = 20 samples.
   > In the end is important to remeber that range vectors ([Xm]) simply collect all those points over the past X minutes—hence the direct proportionality between window length and number of samples.

6. **Applying rate()**

   ```promql
   rate(app_request_duration_seconds_bucket[5m])
   ```

   Why rate? Converts the monotonically increasing bucket counters into per-second rates of observations.

   Result: A rate value for each bucket time series.

   > 📝 Note
   >
   > 1. What rate() Does
   >
   > - Input: a range vector of samples from a single counter metric over a fixed time window (e.g. app_request_duration_seconds_bucket[5m] gives you all of that bucket’s values at each scrape in the last five minutes).
   >
   > - Output: an instant vector — one number per distinct series (i.e. per unique combination of your labels, including each bucket "le" value).
   >
   > 2. From Range to Single Value
   >    You start with a list of pairs: `value₁ @ t₁, value₂ @ t₂, …, valueₙ @ tₙ`
   >
   >    To get precise “start” and “end” values at exactly 5 minutes ago and “now,” Prometheus linearly interpolates between the nearest two real samples at each end.
   >
   >    This basically means that we compute an istant vector. As a matter of fact, unlike metric[5m], which returns all the raw points, rate(metric[5m]) collapses them into one averaged-per-second value.
   >
   >    This instanct vector is a simple arithmetic rate (total increase ÷ total time), it is not a median or a series of segment-by-segment averages — it’s the end-to-end slope of your counter over the full window.

7. **Aggregating by Bucket Upper Bound (le)**

   ```promql
   sum by (le)(rate(app_request_duration_seconds_bucket[5m]))
   ```

   `sum by (le)`: Aggregates rates across all label dimensions except the bucket bound (le).

   Result: Total rate of observations for each bucket threshold.

   > Note
   > sum by (le)(…) discards all other labels (like HTTP method, route, status code) and then adds up every instance’s rate, separately for each le value (e.g. le="0.1", le="0.3", …, le="+Inf").
   >
   > You end up with one rate number per bucket threshold, representing the average number of requests per second, across your entire service, that fall into each “≤ le” category over the last five minutes.
   >
   > This gives you the aggregated histogram data needed to see, for example, how many sub-0.1 s or sub-1 s requests you’re getting per second overall.
   >
   > It’s also the required pre-aggregation step for percentile functions like histogram_quantile().

8. **Computing the Quantile**

   ```promql
   histogram_quantile(0.95, sum by (le)(rate(app_request_duration_seconds_bucket[5m])))
   ```

   Or if you want to see the results for each route

   ```promql
   histogram_quantile(
      0.95,
      sum by (route, method, le)(rate(app_request_duration_seconds_bucket[5m]))
   )
   ```

   - histogram_quantile(φ, ...): Calculates the φ-th quantile (here, 95th percentile) from bucketed data.

   Parameters:

   - 0.95: Desired percentile.

   - sum by (le)(rate(...)): Aggregated bucket rates.

   Outcome: The latency value below which 95% of requests fall

   > ✅ Tip
   > It might be intereseting to deliberately cause a latency in one of the endpoints, just to see the effects.

   > 📝 Note
   > What histogram_quantile() Does
   > It takes a quantile parameter (here 0.95) and an aggregated histogram (your summed rates per bucket) and returns an estimated value (in seconds) at which that quantile occurs.
   >
   > In plain terms, it answers: “What request duration marks the 95th percentile of all requests in the last 5 minutes, for each route-method pair?”
   >
   > 0.95 → the target quantile (95%).
   >
   > sum by (route, method, le)(rate(...)) → for each (route, method, le) you have a single rate value: the average number of requests/sec that fell into “≤ le” during the past 5 minutes.

---

## Hints

- `histogram_quantile` computes percentiles from bucketed data.
- Confirm bucket labels via `app_request_duration_seconds_bucket`.

---

## Your Notes / Answers

1. ## What is the 95th percentile latency?

2. ## Which bucket has the most observations?

---

**Exercise 4: Grafana Dashboard for Node.js Metrics (Extended)**

**Objective**
Build and enhance a Grafana dashboard to monitor not only core performance metrics of your Node.js service but also advanced aspects like error rates, garbage collection, logs, alerting, and dynamic variables.

---

## Steps

1. **Add Dashboard Variables**

   - Go to **Dashboard Settings → Variables → Add variable**.
   - Select `Custom` from the variable type dropdown.
   - Create a variable named `job`.
   - Set the custom value as `node_app`.
   - Reference `${job}` in every query to make the dashboard reusable across different services.

2. **Panel: CPU Usage**

   - Panel Type: Gauge.
   - Query:

     ```promql
     rate(process_cpu_seconds_total{job="${job}"}[1m])
     ```

   - Title: "CPU Usage (1m rate)".
   - Unit Display: In the panel’s Field tab under Standard options, set Unit percent (0-100) for a percentage view.
   - Thresholds and Coloring: In Field → Thresholds, define thresholds (e.g., warning at 80%, critical at 90%) for visual alerting.

3. **Panel: Memory Usage**

   - Panel Type: Gauge.
   - Query:

     ```promql
     process_resident_memory_bytes{job="${job}"}
     ```

   - Title: "Memory Usage (RSS)".
   - **Unit Display**: In the panel’s **Field** tab under **Standard options**, set **Unit** to **bytes (IEC)** or **bytes (SI)** so Grafana automatically displays values in KB, MB, or GB based on magnitude.

4. **Panel: Request Rate**

   - Panel Type: Bar chart, Table, or Heatmap (alternative to Time series).

     - Bar chart or Bar gauge: compares request rates per route in a single snapshot (e.g., last minute).
     - Table: displays numeric rates per route with sorting and threshold coloring.
     - Heatmap: visualizes rate distributions over time across routes.

   - Query:

     ```promql
     sum by (route)(rate(http_requests_total{job="${job}"}[1m]))
     ```

   - Title: "Requests per Route".
   - Legend Formatting: Under the panel’s Field (or Display) settings, set Legend to {{route}} so only the route label appears, removing the full query expression from the legend.
   - Unit Display: Set Unit to requests/sec under Field → Standard option

5. **Panel: Latency (95th Percentile)**

   - Recommended Panel Types:

     - Time series: classic view showing latency over time.
     - Heatmap: visualize distribution of request latencies over time buckets—ideal for spotting shifts in response-time patterns.
     - Gauge or Stat: show the current 95th percentile value as a single-figure metric.

   - Query:

     ```promql
     histogram_quantile(0.95,
       sum by (le)(rate(app_request_duration_seconds_bucket{job="${job}"}[5m]))
     )
     ```

   - Title: "95th Percentile Request Latency".

   - Unit Display:

     - In the panel’s Field tab under Standard options, set Unit to milliseconds (ms) or seconds (s) depending on your application’s scale.

     - Grafana will automatically convert the float seconds value into the chosen unit (e.g., 0.123 → 123 ms).

   - Thresholds and Coloring:

     - In Field → Thresholds, define thresholds for warning (e.g., 200 ms) and critical (e.g., 500 ms

<!-- 6. **Panel: Error Rate**

   - Recommended Panel Types:

     - Stat or Gauge: display the current 5xx error rate as a single value.
     - Bar gauge: show the error percentage against defined thresholds.
     - Time series: track the error rate trend over time.

   - Query:

     ```promql
     sum by (status)(rate(http_requests_total{job="${job}",status_code=~"5.."}[5m]))
       /
     sum(rate(http_requests_total{job="${job}"}[5m]))
     * 100
     ```

   - Title: "5xx Error Rate (%)".
   - Unit Display: In Field → Standard options, set Unit to percent (0-100).

   - Thresholds and Coloring:

     - In Field → Thresholds, add a warning threshold at 1% and a critical threshold at 5%.
     - For Bar gauge, configure color steps matching these thresholds.

   - Legend and Display:
     - For Time series, set Legend to {{status}} so only status codes appear.
     - For single-value panels (Stat/Gauge), hide the legend to reduce clutter. Panel: Garbage Collection -->

7. **Panel: Garbage Collection**
   //TODO: capire a quale comando fa riferimento perchè questo manca

   - Panel Type: Time series.
   - Query:

     ```promql
     rate(nodejs_gc_runs_total{job="${job}"}[1m])
     ```

   - Title: "GC Runs per Minute".

8. **Panel: Heap Usage**

   - Recommended Panel Types:

     - Time series: compare heap used and total size over time.
     - Stat or Gauge: show current heap usage or usage percentage.
     - Bar gauge: useful for displaying used vs. total heap as a single visualization.

   - Queries:

     - `nodejs_heap_used_bytes{job="${job}"}`
     - `nodejs_heap_size_total_bytes{job="${job}"}`

   - Title: "Heap Used vs Heap Size".

   - Unit Display: In Field → Standard options, set Unit to bytes (SI) or megabytes (MiB). Grafana will auto-scale.

   - Thresholds and Coloring: In Field → Thresholds, add thresholds on Heap Usage (%) at warning (e.g., 70%) and critical (e.g., 90%).

   - Legend and Display:
     - For multi-series panels, set Legend to {{__field.name}}.
     - For single-value panels, hide the legend and display field titles clearly.

---

## Hints

- Use **Template Variables** to filter metrics by service name or environment without duplicating dashboards.
- **Stat** and **Gauge** panels are ideal for single-value metrics like error rates or GC counts.
- Use a single **Graph** panel with multiple series to compare related metrics (e.g., heap used vs heap size).
- **Annotations** help correlate operational events (deploys, incidents) with metric trends.
- Ensure your **Alert** rules include both notification channels and clear severity labels.

---

## Reflection Questions

1. Which dashboard variable makes the dashboard most flexible across environments?
2. How did you configure the alert for error rate? Which threshold and evaluation interval did you choose?
3. In what ways did deploy annotations assist in your post-mortem analysis?
4. What patterns did you observe in garbage collection metrics after extended load tests?
5. If you needed to add a custom internal metric (e.g., queue length), how would you instrument it in Node.js and consume it in Prometheus + Grafana?

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

7. **Visualize the alert in Grafana**  
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
