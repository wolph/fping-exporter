# fping-exporter
Prometheus Exporter for fping that can give similar output to Smokeping.

## Install

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

## Configuration

Now that you have everything installed you need to create a configuration file. The format is rather simple and mostly explained in the [default configuration](https://github.com/WoLpH/fping-exporter/blob/master/fping_exporter.default.cfg).

You can save the file in any (or multiple) of the following locations:

 - `/etc/fping_exporter.cfg`
 - `/usr/local/etc/fping_exporter.cfg`
 - `~/.fping_exporter.cfg`
 - `~/config/fping_exporter.cfg`
 - `fping_exporter.cfg`

## Running

Simply running the script to test can be done like this:

```bash
pipenv run python fping_exporter.py
```
Or without pipenv:
```bash
python fping_exporter.py
```

## Running as a service

I recommend using [pm2](https://pm2.keymetrics.io/docs/usage/quick-start/):

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
