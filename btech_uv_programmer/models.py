from enum import StrEnum, IntEnum

from btech_uv_programmer.exceptions import RadioConfigurationError

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TransmitPower(StrEnum):
    H = "H"
    M = "M"
    L = "L"


class FmBandwidth(IntEnum):
    WIDE = 25000
    NARROW = 12500


class Modulation(IntEnum):
    FM = 0
    AM = 1


class Toggle(IntEnum):
    ENABLED = 1
    DISABLED = 0


class RadioChannelConfig(BaseModel):
    title: str

    tx_freq: int
    rx_freq: int

    tx_sub_audio: int = Field(
        default=0,
        alias="tx_sub_audio(CTCSS=freq/DCS=number)"
    )
    rx_sub_audio: int = Field(
        default=0,
        alias="rx_sub_audio(CTCSS=freq/DCS=number)"
    )

    tx_power: TransmitPower = Field(
        default=TransmitPower.H,
        alias="tx_power(H/M/L)"
    )

    bandwidth: FmBandwidth = Field(
        default=FmBandwidth.WIDE,
        alias="bandwidth(12500/25000)"
    )

    scan: Toggle = Field(
        default=Toggle.DISABLED,
        alias="scan(0=OFF/1=ON)"
    )

    talk_around: Toggle = Field(
        default=Toggle.DISABLED,
        alias="talk around(0=OFF/1=ON)"
    )

    pre_de_emph_bypass: Toggle = Field(
        default=Toggle.DISABLED,
        alias="pre_de_emph_bypass(0=OFF/1=ON)"
    )

    sign: Toggle = Field(
        default=Toggle.DISABLED,
        alias="sign(0=OFF/1=ON)"
    )

    tx_dis: Toggle = Field(
        default=Toggle.DISABLED,
        alias="tx_dis(0=OFF/1=ON)"
    )

    bclo: Toggle = Field(
        default=Toggle.DISABLED,
        alias="bclo(0=OFF/1=ON)"
    )

    mute: Toggle = Field(
        default=Toggle.DISABLED,
        alias="mute(0=OFF/1=ON)"
    )

    rx_modulation: Modulation = Field(
        default=Modulation.FM,
        alias="rx_modulation(0=FM/1=AM)"
    )

    tx_modulation: Modulation = Field(
        default=Modulation.FM,
        alias="tx_modulation(0=FM/1=AM)"
    )

    model_config = ConfigDict(
        populate_by_name=True
    )

    @field_validator('title', mode = 'after')
    def validate_title(cls, value: str) -> str:
        if len(value) > 8:
            raise RadioConfigurationError(f'Invalid title: {value}. Titles must have 8 or fewer characters.')
        return value

    @field_validator('tx_freq', 'rx_freq', mode = 'after')
    def validate(cls, value: int) -> int:
        # if user supplies MHz, convert to hertz
        if (
            # VHF Check
            value < 136e6 or value > 174e6
        ) and (
            # UHF Check
            value < 400e6 or value >= 520e6
        ):
            raise RadioConfigurationError(
                f'Selected frequency exceeds BTECH UV-Pro capabilities: {value}')
        return value
