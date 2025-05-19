# Exercise 1: Discovering the Fake Exporter

**Objective**
Learn how to fetch and inspect metrics exposed by the fake exporter.

---

## Steps

1. **Run the fake exporter**

   ```bash
   docker-compose up -d fake-exporter
   ```

2. **Fetch the raw metrics**

   ```bash
   curl http://localhost:8000/metrics
   ```

3. **Identify the metric names**
   Look for lines like `fake_random_metric` and `fake_counter` in the output.

---

## Hints

- Metrics appear as lines starting with the metric name, followed by a value.
- A _counter_ only goes up; a _gauge_ can go up or down.

---

## Your Notes / Answers

1. ## Which metric(s) did you see?

2. ## What type (gauge or counter) do you think each one is?

---

# Exercise 2: Basic PromQL Queries

**Objective**
Write simple queries in Prometheus to inspect the fake metrics.

---

## Steps

1. **Open Prometheus**
   Go to [http://localhost:9090](http://localhost:9090) in your browser.
2. **Query the current gauge value**
   In the “Expression” box, type:

   ```promql
   fake_random_metric
   ```

   and click **Execute**.

3. **Compute the rate of the counter**
   Enter:

   ```promql
   rate(fake_counter_total[1m])
   ```

   and click **Execute**.

4. **View results**
   Observe the numeric output or graph that Prometheus shows.

---

## Hints

- `fake_random_metric` shows the last gauge sample.
- `rate(fake_counter_total[1m])` gives the per-second increase averaged over 1 minute.

---

## Your Notes / Answers

1. ## What value did you get for `fake_random_metric`?

2. ## What is the approximate rate of `fake_counter`?

---

# Exercise 3: Alerting on the Fake Gauge

**Objective**
Create a Prometheus alert rule that fires when `fake_random_metric` is too high.

---

## Steps

1. **Create a new rules file**
   Save this as `prometheus/rules/fake_alerts.yml`:

   ```yaml
   groups:
     - name: fake_exporter_alerts
       rules:
         - alert: GaugeTooHigh
           expr: fake_random_metric > 80
           for: 1m
           labels:
             severity: warning
           annotations:
             summary: "fake_random_metric is above 80"
             description: "Value has been >80 for more than 1 minute."
   ```

2. **Include it in`prometheus.yml`**
   Under `rule_files:` add:

   ```yaml
   rule_files:
     - "rules/fake_alerts.yml"
   ```

3. **Restart Prometheus**

   ```bash
   docker-compose down && docker-compose up -d prometheus
   ```

4. **Test your alert**

   - Wait until your gauge goes above 80 for at least one minute.
   - In Prometheus UI, click **Alerts** and confirm you see `GaugeTooHigh`.

---

## Hints

- Alerts only show up after the `for` duration has passed.
- You can force a high value by restarting the exporter:

  ```bash
  docker-compose restart fake-exporter
  ```

---

## Your Notes / Answers

1. ## Did `GaugeTooHigh` appear in the Alerts list?

2. ## How long did it take to fire?

---

# Exercise 4: Visualizing with Grafana

**Objective**
Create a simple Grafana panel to display the `fake_random_metric` gauge over time.

---

## Steps

1. **Open Grafana**
   Go to [http://localhost:3000](http://localhost:3000).
2. **Import a new dashboard**

   - Click the **+** icon in the left menu, then **Dashboard**.
   - Click **Add new panel**.

3. **Configure the panel**

   - In **Queries**, select _Prometheus_ as the data source.
   - Enter the query:

     ```promql
     fake_random_metric
     ```

   - Set the **Panel title** to “Fake Random Metric”.

4. **Save the dashboard**

   - Click **Apply**, then **Save dashboard** (give it a name like `Fake Exporter`).

---

## Hints

- You can switch the panel type between **Time series** and **Gauge**.
- Use the **Visualization** tab to change display options.

---

## Your Notes / Answers

1. ## Which visualization type did you choose?

2. ## How does the graph change when you zoom into the last 5 minutes?

---

# Exercise 5: Combining Multiple Metrics

**Objective**
Build a Grafana panel that compares two metrics: `rate(fake_counter_total[1m])` and the gauge `fake_random_metric`.

---

## Steps

1. **Add a new panel**
   In the same `Fake Exporter` dashboard, click **Add panel**.
2. **Write two queries**

   - **A:** `rate(fake_counter_total[1m])`
   - **B:** `fake_random_metric`

3. **Customize the display**

   - In **Field** options, set different units or colors for each metric.
   - Toggle **Legend** to show `{{__name__}}`.

4. **Apply and save**

   - Click **Apply**, then **Save dashboard**.

---

## Hints

- Use the **Overrides** tab to change how each series looks.
- The browser legend shows each series name.

---

## Your Notes / Answers

1. ## Which metric is higher on average?

2. ## Did you use a different unit or color?

---

# Exercise 6: Dashboard Variables and Filtering

**Objective**
Add a variable to filter panels by metric name.

---

## Steps

1. **Open dashboard settings**

   - On your `Fake Exporter` dashboard, click the **gear** icon.

2. **Add a variable**

   - In **Variables**, click **Add variable** → **Custom**.
   - **Name:** `metric`
   - **Values:** `fake_random_metric,fake_counter`
   - **Selection Options:** Enable **Include All option**.

3. **Use the variable in a panel**

   - Edit any panel query and replace the metric with `${metric}`.
   - For example: `${metric}` or `rate(${metric}[1m])`.

4. **Save changes**

   - Apply and save the dashboard.

---

## Hints

- The **All** option runs the query for both metrics at once.
- Use `${variable:label}` in legends to show the variable value.

---

## Your Notes / Answers

1. ## When you select **All**, what happens?

2. ## How would you use a second variable for time range (e.g. `1m`, `5m`, `1h`)?

---

# Exercise 7: Recording Rules for Efficiency

**Objective**
Learn how to create a recording rule to precompute the rate of `fake_counter`.

---

## Steps

1. **Create a rules file**
   Save this as `prometheus/rules/recording_rules.yml`:

   ```yaml
   groups:
     - name: fake_exporter_recording
       rules:
         - record: job:fake_counter:rate1m
           expr: rate(fake_counter[1m])
   ```

2. **Include it in `prometheus.yml`**
   Update `rule_files:` to:

   ```yaml
   rule_files:
     - "rules/fake_alerts.yml"
     - "rules/recording_rules.yml"
   ```

3. **Reload Prometheus**

   ```bash
   docker-compose exec prometheus kill -HUP 1
   ```

4. **Use the new metric**
   In Prometheus UI, query:

   ```promql
   job:fake_counter:rate1m
   ```

---

## Hints

- Recording rules improve performance by caching results.
- You can view active rules under **Status → Rules** in Prometheus UI.

---

## Your Notes / Answers

1. ## Did you see `job:fake_counter:rate1m` listed under recording rules?

2. ## How does querying the recording rule compare to the raw `rate` function?

---

# Exercise 8: Advanced PromQL Functions

**Objective**
Explore functions like `increase()` and `irate()` on `fake_counter`.

---

## Steps

1. **Test `increase`**
   In Prometheus, run:

   ```promql
   increase(fake_counter[5m])
   ```

2. **Test `irate`**
   Run:

   ```promql
   irate(fake_counter[5m])
   ```

3. **Compare results**
   Observe differences between `rate`, `increase`, and `irate`.

---

## Hints

- `increase` shows the total change over the interval.
- `irate` shows the instantaneous per-second rate based on the last two samples.

---

## Your Notes / Answers

1. ## Which function gave the highest value?

2. ## Which function is most “spiky”?

---

# Exercise 9: Grafana Alerting on Panels

**Objective**
Set up an alert in Grafana that triggers when the gauge exceeds a threshold.

---

## Steps

1. **Edit a panel**
   Go to your `Fake Random Metric` panel and click **Edit**.
2. **Alert tab**

   - Switch to the **Alert** tab.
   - Click **Create Alert**.

3. **Define a condition**

   - For example: `WHEN avg() OF query(A, 5m, now) IS ABOVE 80`.
   - Click **Save**.

4. **Notification channel**

   - Configure a simple **Email** channel under **Alerting → Notification channels**.
   - Attach it to the alert.

5. **Test alert**

   - Temporarily change threshold to a low value (e.g. 10) to force firing.
   - Check your email or **Alerting → Alert rules**.

---

## Hints

- Grafana alerting requires **data source** permissions.
- Alerts evaluate at the dashboard’s **evaluation interval**.

---

## Your Notes / Answers

1. ## Did the alert fire and notify you?

2. ## How long did it take to trigger?

---

# Exercise 10: Using Grafana Annotations

**Objective**
Mark important events on your graph with annotations.

---

## Steps

1. **Open dashboard settings**
   Click the **gear** icon on `Fake Exporter` dashboard.
2. **Annotations**

   - Click **Annotations** → **Add Annotation**.
   - **Name:** `High Gauge`
   - **Data source:** _Prometheus_
   - **Query:** `fake_random_metric > 90`

3. **View annotations**
   Return to your panel and refresh.
   You should see vertical lines marking when the gauge exceeded 90.

---

## Hints

- Annotations help correlate metrics with events.
- You can click an annotation line to see details.

---

## Your Notes / Answers

1. ## How many annotation events appeared?

2. ## Did they align with spikes on the gauge?
