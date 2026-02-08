# btech-uv-programmer
Python3 library for automating the CSV configuration of the BTECH UV-PRO Handheld Radio

## Example

Loading from a CSV file:

```python
from btech_uv_programmer import BtechUvProProgrammer

pgm = BtechUvProProgrammer()
pgm.load_csv_config('example.csv')
```

Creating from Scatch:

```python
from btech_uv_programmer import BtechUvProProgrammer

pgm = BtechUvProProgrammer()

pgm.load_natnl_2m_simplex()
pgm.load_natnl_70cm_simplex()
pgm.load_natnl_aprs()

pgm.dump_csv_config('example.csv')
```
