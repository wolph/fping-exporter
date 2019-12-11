module.exports = {
  apps : [{
    name: 'fping_exporter',
    script: 'fping_exporter.py',
    instances: 1,
    autorestart: true,
    watch: true,
    max_memory_restart: '100M'
  }]
};
