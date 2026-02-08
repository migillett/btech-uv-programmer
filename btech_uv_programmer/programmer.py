from csv import DictReader, DictWriter
from time import time
import logging

from btech_uv_programmer.models import RadioChannelConfig, RadioConfigurationError, Toggle


logger = logging.getLogger(__name__)


class BtechUvProProgrammer:
    def __init__(self, max_stations: int = 30) -> None:
        self.max_stations = max_stations
        self.stations: dict[int, RadioChannelConfig | None] = {}
        self.clear_config()

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

    ### COMMON DEFAULTS ###
    def load_natnl_aprs(self, channel_index: int) -> None:
        '''
        Docstring for load_aprs_default
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max.
        :type channel_index: int
        '''
        channel = RadioChannelConfig(
            title='APRS',
            rx_freq=144390000,
            tx_freq=144390000
        )
        channel.mute = Toggle.ENABLED
        self.set_station(channel_index, channel)

    def load_natnl_2m_simplex(self, channel_index: int) -> None:
        '''
        Load the 2 meter simplex national calling frequency into the channels.
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max.
        :type channel_index: int
        '''
        channel = RadioChannelConfig(
            title='146.520',
            rx_freq=146520000,
            tx_freq=146520000
        )
        self.set_station(channel_index, channel)

    def load_natnl_70cm_simplex(self, channel_index: int) -> None:
        '''
        Load the 70 centimeter simplex national calling frequency into the channels.
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max.
        :type channel_index: int
        '''
        channel = RadioChannelConfig(
            title='446.000',
            rx_freq=466000000,
            tx_freq=466000000
        )
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

    def delete_station(self, channel_index: int) -> None:
        '''
        Delete a station configuration at a specific index.
        
        :param channel_index: Channel index for the station. Indexes start at 0 and go to station max.
        :type channel_index: int
        '''
        self.__check_station_index__(channel_index)
        self.stations[channel_index] = None

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
                v = None if v == "" else v
                response[k] = v
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
