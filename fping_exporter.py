import re
import os
import sys
import pprint
import logging
import asyncio
import functools
import collections
import configparser
import prometheus_client
from datetime import datetime


FPING_SETTINGS = dict(
    period=int,
    tos=int,
    retry=int,
    src=str,
    timeout=int,
    size=int,
    backoff=float,
    count=int,
    ttl=int,
    random=bool,
)

logger = logging.root

# Generate the buckets, can be changed if needed
# Ranges from 0.1ms to 50s with the parameters
bucket_base = 1, 2, 5
buckets = []
for i in range(-4, 2):
    for base in bucket_base:
        buckets.append(base * (10 ** i))
buckets.append(float('inf'))

labels = ['group', 'name', 'address']
histogram = prometheus_client.Histogram(
    'fping', 'Fping latency in seconds', labels, buckets=buckets)


class Host(dict):

    def __init__(self, name):
        self.name = name
        self.process = None
        self.error = None
        self.last_line = None
        self.started = False

    @property
    def address(self):
        return self.get('address', self.name)

    def __setitem__(self, key, value):
        if value == '':
            self.pop(key, None)
        else:
            super().__setitem__(key, value)

    def update(self, items):
        for key, value in items.items():
            self[key] = value

    async def run_process(self, args):
        logger.info('%r', ' '.join(args))
        self.process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        while not self.process.returncode:
            self.last_line = await self.process.stdout.readline()
            if self.last_line:
                line = self.last_line.strip().decode('utf-8')
                logger.debug('%s: %s', self.name, line)
                match = re.match(r'''
                \[(?P<timestamp>[.0-9]+)\]\s+
                (?P<address>[^\s]+)\s+:\s+
                \[(?P<count>\d+)\],\s+
                (?P<bytes>\d+)\s+bytes,\s+
                (?P<latency>[.0-9]+)\s+ms\s+
                .*
                ''', line, re.VERBOSE)
                assert match, 'No match for %r' % line
                
                label_values = dict(
                    group=self.get('group'),
                    name=self.name,
                    address=match.group('address'),
                )
                histogram.labels(**label_values).observe(
                    # Convert to seconds
                    0.001 * float(match.group('latency')))
            else:
                self.error = await self.process.stderr.readline()
                if self.error:
                    logging.fatal('%r error: %s', self, self.error.strip())
                    if not self.process.returncode:
                        await self.process.terminate()

                    break
        self.process == None

    async def run(self, min_backoff=1, max_backoff=600):
        self.started = datetime.now()
        args = ['fping', '--timestamp', '--addr']
        settings = dict()
        for key, cast in FPING_SETTINGS.items():
            value = self.get(key)
            if value:
                value = cast(value)
                settings[key] = value

                if isinstance(value, bool):
                    args.append(f'--{key}')
                else:
                    args.append(f'--{key}={value}')

        if not self.get('count'):
            args.append('--loop')

        args.append(self.address)

        logger.warning('Running %s:%s with: %s', self.name, self['group'],
                    settings)
        assert settings['period']

        backoff = min_backoff
        while True:
            await self.run_process(args)
            logging.info('backing off %s:%s with %ss', self.name,
                         self['group'], backoff)
            await asyncio.sleep(backoff)
            backoff = min(max_backoff, backoff * 2)


class Hosts(dict):
    def __missing__(self, key):
        self[key] = host = Host(key)
        host.update(self.__dict__)
        return host


class Group(dict):

    def __init__(self, name):
        self.name = name
        self.hosts = Hosts()

    def expand_hosts(self):
        hosts = self.pop('hosts', '')
        hosts = re.sub('\s*=\s*', '=', hosts)

        for hostname in hosts.strip().split():
            hostname = hostname.split('=')
            if hostname[1:]:
                address, name = hostname
            else:
                address = name = hostname[0]

            host = self.hosts[name]
            host.update(self)
            host['address'] = address
            host['group'] = self.name


class Groups(dict):

    def __missing__(self, key):
        self[key] = group = Group(key)
        return group


class Config(configparser.ConfigParser):

    CONFIG_FILES = (
        'fping_exporter.default.cfg',
        '/etc/fping_exporter.cfg',
        '/usr/local/etc/fping_exporter.cfg',
        os.path.expanduser('~/.fping_exporter.cfg'),
        os.path.expanduser('~/config/fping_exporter.cfg'),
        'fping_exporter.cfg',
    )

    def __init__(self, *files, **kwargs):
        self.groups = Groups()
        super().__init__(
            interpolation=configparser.ExtendedInterpolation(),
            allow_no_value=True,
            inline_comment_prefixes=('#', ';'),
        )

        self.read(self.CONFIG_FILES + files, encoding='utf-8')
        assert self['DEFAULT']['period'], 'Sanity check for default config'

    def read(self, *args, **kwargs):
        super().read(*args, **kwargs)

        hosts = Hosts()
        for key in self:
            if key.startswith('group:'):
                value = self[key]
                name = key.split(':', 1)[-1]
                group = self.groups[name]
                group.update(value)
                group.expand_hosts()

        for key in self:
            if key.startswith('host:'):
                name = key.split(':', 1)[-1]
                group_name = self.get(key, 'group')
                value = dict(self.items('group:' + group_name))

                # Yes this is crappy, but the configparser does not expose the
                # values of a section without defaults
                value.update(self._sections[key])

                value.pop('hosts', None)
                self.groups[group_name].hosts[name].update(value)


def main():
    logging.basicConfig(level=logging.INFO)

    config = Config()
    listen_port = config.getint('fping_exporter', 'listen_port', fallback=9999)
    prometheus_client.start_http_server(listen_port)
    argv = sys.argv[1:]

    futures = []
    for group_name, group in config.groups.items():
        print(group_name)
        for name, host in group.hosts.items():
            if argv and name not in argv and group_name not in argv:
                continue

            print('\t', name, host)
            futures.append(host.run())

    asyncio.run(asyncio.wait(futures))

if __name__ == '__main__':
    main()
