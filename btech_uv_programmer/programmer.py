from csv import DictReader, DictWriter
from time import time
import logging
from typing import Optional

from btech_uv_programmer.models import RadioChannelConfig, RadioConfigurationError, Toggle

from tabulate import tabulate


logger = logging.getLogger(__name__)


class BtechUvProProgrammer:
    def __init__(self, max_stations: int = 30) -> None:
        self.max_stations = max_stations
        self.stations: dict[int, RadioChannelConfig | None] = {}
        # TODO: add support for 6 banks of 30 stations each
        self.clear_config()

    ### UTILITIES ###
    def __check_stations__(self) -> None:
        if len(self.stations) > self.max_stations:
            raise RadioConfigurationError(f'Number of programmed stations {len(self.stations)} exceeds the maximum ({self.max_stations}).')

    def __check_station_index__(self, index: int) -> None:
        if index > self.max_stations - 1:
            # Python indexes are a little weird, so len(30) max stations means the final station index is 29
            raise IndexError(f'Index {index} is greater than max station index ({self.max_stations - 1})')

    def __get_csv_headers__(self) -> list[str]:
        return [
            field.alias or name
            for name, field in RadioChannelConfig.model_fields.items()
        ]
    
    def mhz_to_hz(self, mhz: float) -> int:
        '''
        Simple utility that converts mhz (float) to hertz (integer)
        
        :param mhz: Frequency in megahertz
        :type mhz: float
        :return: Frequency in hertz
        :rtype: int
        '''
        return int(mhz * 10e6)
    
    def as_table(self) -> None:
        data = [
            x.model_dump(mode='json')
            for x in self.stations.values()
            if x is not None
        ]
        # Print the data as a table, using dictionary keys as headers
        print(tabulate(data, headers="keys", tablefmt="grid"))

    ### COMMON DEFAULTS ###
    def load_natnl_aprs(self, channel_index: Optional[int] = None) -> None:
        '''
        Docstring for load_aprs_default
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max. If undefined, add to next available channel.
        :type channel_index: int | None
        '''
        channel = RadioChannelConfig(
            title='APRS',
            rx_freq=self.mhz_to_hz(144.39),
            tx_freq=self.mhz_to_hz(144.39)
        )
        channel.mute = Toggle.ENABLED
        if not channel_index:
            self.append_station(channel)
        else:
            self.set_station(channel_index, channel)

    def load_natnl_2m_simplex(self, channel_index: Optional[int] = None) -> None:
        '''
        Load the 2 meter simplex national calling frequency into the channels.
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max. If undefined, add to next available channel.
        :type channel_index: int | None
        '''
        channel = RadioChannelConfig(
            title='146.520',
            rx_freq=self.mhz_to_hz(146.52),
            tx_freq=self.mhz_to_hz(146.52)
        )
        if not channel_index:
            self.append_station(channel)
        else:
            self.set_station(channel_index, channel)

    def load_natnl_70cm_simplex(self, channel_index: Optional[int] = None) -> None:
        '''
        Load the 70 centimeter simplex national calling frequency into the channels.
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max. If undefined, add to next available channel.
        :type channel_index: int | None
        '''
        channel = RadioChannelConfig(
            title='446.000',
            rx_freq=self.mhz_to_hz(446.0),
            tx_freq=self.mhz_to_hz(446.0)
        )
        if not channel_index:
            self.append_station(channel)
        else:
            self.set_station(channel_index, channel)

    ### SEARCHING ###
    def search_by_title(self, title: str) -> tuple[int, RadioChannelConfig]:
        for index, config in self.stations.items():
            if config and config.title == title:
                return index, config
        raise RadioConfigurationError(f'Channel with title {title} not found in memory.')

    ### MODIFYING CONFIGURATIONS ###
    def set_station(self, channel_index: int, channel_config: RadioChannelConfig) -> None:
        '''
        Docstring for set_station
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max.
        :type channel_index: int
        :param channel_config: The configuration of the station you wish to add.
        :type channel_config: RadioConfigRow
        '''
        self.__check_station_index__(channel_index)
        self.stations[channel_index] = channel_config
        logger.info(f'Applied configuration for {channel_config.title} to index {channel_index}')

    def clear_config(self) -> None:
        '''
        Clear ALL station configurations.
        '''
        self.stations = {i: None for i in range(self.max_stations)}
        logging.info('Initialized station configuration.')

    def delete_station(self, channel_index: int) -> None:
        '''
        Delete a station configuration at a specific index.
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max.
        :type channel_index: int
        '''
        self.__check_station_index__(channel_index)
        if not self.stations[channel_index]:
            logging.warning(f'No station configuration at channel index {channel_index} to delete.')
        else:
            self.stations[channel_index] = None
            logging.info(f'Deleted station at index {channel_index}')

    def append_station(self, channel_config: RadioChannelConfig) -> None:
        '''
        Append the station configuration to the first open slot in the list.
        
        :param channel_config: The configuration of the station you wish to add.
        :type channel_config: RadioConfigRow
        '''
        for i, config in self.stations.items():
            if not config:
                self.set_station(i, channel_config)
                return
        raise RadioConfigurationError(f'No open slots to add channel.')

    ### CSV FUNCTIONS ###
    def load_csv_config(self, csv_path: str) -> None:
        '''
        Allows you to load a pre-configured CSV file into program memory.
        
        :param csv_path: Relative or absolute path of the CSV file.
        :type csv_path: str
        '''
        def sanitize_input(row_dict: dict) -> dict:
            response = {}
            for k, v in row_dict.items():
                response[k] = None if v == "" else v
            return response
        
        self.clear_config()

        with open(csv_path, 'r') as csv_load:
            reader = DictReader(csv_load)
            for index, row in enumerate(reader):
                sanitized = sanitize_input(row)
                item = RadioChannelConfig.model_validate(sanitized)
                self.stations[index] = item
        
        self.__check_stations__()
        logger.info(f'Loaded {len(self.stations)} channel presets from CSV: {csv_path}')

    def dump_csv_config(self, export_path: str | None = None) -> None:
        '''
        Dump the class station configurations to a CSV path.
        
        :param export_path: Export path of the CSV file. Default will be the current directory with the {timestamp}_export.csv as the filename.
        :type export_path: str | None
        '''
        if not export_path:
            export_path = f'{int(time())}_export.csv'

        if len(self.stations) == 0:
            raise RadioConfigurationError(f'No stations loaded. Unable to export configuration to: {export_path}')
            
        with open(export_path, 'w') as csv_dump:
            writer = DictWriter(
                csv_dump,
                fieldnames=self.__get_csv_headers__(),
                lineterminator='\n'
            )
            writer.writeheader()
            for station in self.stations.values():
                if station:
                    writer.writerow(station.model_dump(mode='json', by_alias=True))
                else:
                    # include stations not defined
                    csv_dump.write('\n')
        logger.info(f'Successfully wrote radio configuration to {export_path}')
