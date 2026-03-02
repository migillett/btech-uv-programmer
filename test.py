import asyncio
from typing import Optional
import json
import logging
from os import path

from bleak import BleakScanner, BleakClient
from pydantic import BaseModel


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class DeviceNotFoundError(Exception):
    pass


class MissingRadioConfigError(Exception):
    pass


class RadioCharacteristics(BaseModel):
    MacAddress: str
    SdpUuid: Optional[str] = None
    SdpWrite: Optional[str] = None
    SdpRead: Optional[str] = None

    def has_sdp_config(self) -> bool:
        return (
            self.SdpRead is not None and
            self.SdpWrite is not None and
            self.SdpUuid is not None
        )


async def scan_for_device() -> str:
    logger.info('Scanning BLE devices for UV-PRO...')
    devices = await BleakScanner.discover(timeout=15)
    for device in devices:
        logger.info(f"* {device.name} - {device.address}")
        if device.name == 'UV-PRO':
            logger.info(f'Found UV-PRO at address: {device.address}')
            return device.address
    raise DeviceNotFoundError('Unable to find UV-PRO BLE device')


def dump_radio_config(radio_config: RadioCharacteristics, json_path: str = './config.json') -> None:
    with open(json_path, 'w') as dump:
        json.dump(radio_config.model_dump(mode='json'), dump, indent=2)
        logger.info(f'Dumped config to path: {json_path}')


def load_radio_config(json_path: str = './config.json') -> RadioCharacteristics | None:
    if path.exists(json_path):
        with open(json_path, 'r') as json_load:
            logger.info(f'Loading config from path: {json_path}')
            data = RadioCharacteristics.model_validate(json.load(json_load))
            return data
    return None


async def discover_services(
        client: BleakClient,
        radio_config: RadioCharacteristics
    ) -> None:
    logger.info('Attempting service discovery for device...')
    for service in client.services:
        logger.info("[Service] %s", service)
        for char in service.characteristics:
            if "read" in char.properties:
                try:
                    value = await client.read_gatt_char(char)
                    extra = f", Value: {value}"
                except Exception as e:
                    extra = f", Error: {e}"
            else:
                extra = ""

            if "write-without-response" in char.properties:
                extra += f", Max write w/o rsp size: {char.max_write_without_response_size}"

            logger.info(
                "  [Characteristic] %s (%s)%s",
                char,
                ",".join(char.properties),
                extra,
            )

            for descriptor in char.descriptors:
                try:
                    value = await client.read_gatt_descriptor(descriptor)
                    logger.info("    [Descriptor] %s, Value: %r", descriptor, value)
                except Exception as e:
                    logger.error("    [Descriptor] %s, Error: %s", descriptor, e)


        # logger.info(f'{service.description}: {service.characteristics}')
        # if service.description == 'SDP':
        #     logger.info(f'Found SDP Service: {service}')
        #     radio_config.SdpUuid = service.uuid
        #     for char in service.characteristics:
        #         if 'read' in char.properties:
        #             radio_config.SdpRead = char.uuid
        #         elif 'write' in char.properties:
        #             radio_config.SdpWrite = char.uuid
    
    logger.info(radio_config.model_dump(mode='json'))


async def read_gatt_chars(client: BleakClient, sdp_read_uuid: str) -> None:
    details = await client.read_gatt_char(sdp_read_uuid)
    logger.debug(details)


async def find_radio(reload: bool) -> RadioCharacteristics:
    radio_details = load_radio_config()
    if radio_details is None or reload:
        address = await scan_for_device()
        radio_details = RadioCharacteristics(MacAddress=address)
    return radio_details


async def main(reload: bool = False) -> None:
    radio_details = await find_radio(reload)
    async with BleakClient(radio_details.MacAddress, timeout=15) as client:
        logger.info(f'Connected to radio {radio_details.MacAddress}')
        try:
            for service in client.services:
                print(service)

            if not radio_details.has_sdp_config():
                await discover_services(client, radio_details)

            if not radio_details.has_sdp_config():
                raise MissingRadioConfigError()
            
            logger.debug("Reading characteristics...")
            details = await client.read_gatt_char(radio_details.SdpRead)
            logger.debug(details)
        except Exception as e:
            logger.exception(e)
        finally:
            dump_radio_config(radio_details)


if __name__ == "__main__":
    force_reload = False
    asyncio.run(main(force_reload))
