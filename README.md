# fping-exporter
Prometheus Exporter for fping that can give similar output to Smokeping.

For an easy install you can use [pipenv](https://pipenv.readthedocs.io/en/latest/).

```bash
git clone https://github.com/WoLpH/fping-exporter.git
cd fping-exporter
pipenv install
```

Alternatively a regular pip install works too. The only requirement is `prometheus_client`

```bash
git clone https://github.com/WoLpH/fping-exporter.git
cd fping-exporter
pip install prometheus_client
```

Once you have it installed you need something to run it and to keep it running. I recommend using [pm2](https://pm2.keymetrics.io/docs/usage/quick-start/):

```bash
pm2 start
```

Finally, add the monitor to Prometheus:
```yaml
  - job_name: 'fping'
    scrape_interval: 10s
    static_configs:
      - targets: ['bsd:9999']
```

The Grafana Dashboard definition can be found here: https://github.com/WoLpH/fping-exporter/blob/master/grafana.json

![Grafana Dashboard](https://github.com/WoLpH/fping-exporter/blob/master/grafana_screenshot.png?raw=true)
