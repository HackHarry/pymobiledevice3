import asyncio
import logging
from typing import List, TextIO

import click
from cryptography.hazmat.primitives.asymmetric import rsa

from pymobiledevice3.cli.cli_common import RSDCommand, print_json, prompt_device_list
from pymobiledevice3.remote.bonjour import get_remoted_addresses
from pymobiledevice3.remote.remote_service_discovery import RSD_PORT, RemoteServiceDiscoveryService
from pymobiledevice3.remote.utils import stop_remoted

try:
    from pymobiledevice3.remote.core_device_tunnel_service import create_core_device_tunnel_service
except ImportError:
    # isn't supported on Windows
    pass

logger = logging.getLogger(__name__)


def get_device_list() -> List[RemoteServiceDiscoveryService]:
    result = []
    with stop_remoted():
        for address in get_remoted_addresses():
            rsd = RemoteServiceDiscoveryService((address, RSD_PORT))
            rsd.connect()
            result.append(rsd)
    return result


@click.group()
def cli():
    """ remote cli """
    pass


@cli.group('remote')
def remote_cli():
    """ remote options """
    pass


@remote_cli.command('browse')
@click.option('--color/--no-color', default=True)
def browse(color: bool):
    """ browse devices using bonjour """
    devices = []
    for rsd in get_device_list():
        devices.append({'address': rsd.service.address[0],
                        'port': RSD_PORT,
                        'UniqueDeviceID': rsd.peer_info['Properties']['UniqueDeviceID'],
                        'ProductType': rsd.peer_info['Properties']['ProductType'],
                        'OSVersion': rsd.peer_info['Properties']['OSVersion']})
    print_json(devices, colored=color)


@remote_cli.command('rsd-info', cls=RSDCommand)
@click.option('--color/--no-color', default=True)
def rsd_info(service_provider: RemoteServiceDiscoveryService, color: bool):
    """ show info extracted from RSD peer """
    print_json(service_provider.peer_info, colored=color)


async def start_quic_tunnel(service_provider: RemoteServiceDiscoveryService, secrets: TextIO) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with create_core_device_tunnel_service(service_provider, autopair=True) as service:
        async with service.start_quic_tunnel(private_key, secrets_log_file=secrets) as tunnel_result:
            if secrets is not None:
                print(click.style('Secrets: ', bold=True, fg='magenta') +
                      click.style(secrets.name, bold=True, fg='white'))
            print(click.style('Interface: ', bold=True, fg='yellow') +
                  click.style(tunnel_result.interface, bold=True, fg='white'))
            print(click.style('RSD Address: ', bold=True, fg='yellow') +
                  click.style(tunnel_result.address, bold=True, fg='white'))
            print(click.style('RSD Port: ', bold=True, fg='yellow') +
                  click.style(tunnel_result.port, bold=True, fg='white'))
            print(click.style('Use the follow connection option:\n', bold=True, fg='yellow') +
                  click.style(f'--rsd {tunnel_result.address} {tunnel_result.port}', bold=True, fg='cyan'))

            while True:
                # wait user input while the asyncio tasks execute
                await asyncio.sleep(.5)


@remote_cli.command('start-quic-tunnel')
@click.option('--secrets', type=click.File('wt'), help='TLS keyfile for decrypting with Wireshark')
def cli_start_quic_tunnel(secrets: TextIO):
    """ start quic tunnel """
    devices = get_device_list()
    if not devices:
        print('No device could be found')
        return
    if len(devices) == 1:
        rsd = devices[0]
    else:
        rsd = prompt_device_list(devices)
    asyncio.run(start_quic_tunnel(rsd, secrets), debug=True)


@remote_cli.command('shell', cls=RSDCommand)
@click.argument('service')
def cli_shell(service_provider: RemoteServiceDiscoveryService, service: str):
    """ start an ipython shell for interacting with given service """
    with service_provider.start_remote_service(service) as service:
        service.shell()