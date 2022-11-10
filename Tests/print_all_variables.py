import pyads
from connection import conn

conn.open()

try:
    symbols: list[pyads.AdsSymbol] = sorted(
        conn.get_all_symbols(), key=lambda t: t.name
    )
except pyads.ADSError as e:
    print(e.msg)
    conn.close()
    exit(-1)

for symbol in symbols:
    print(symbol.name)

conn.close()
