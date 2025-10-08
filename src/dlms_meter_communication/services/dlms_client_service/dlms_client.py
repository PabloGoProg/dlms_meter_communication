from .media_links.providers import SocketProvider, GuruxProvider
from .enums import ConnectionInterfaceType

p = GuruxProvider(
    ip_address="192.168.1.100",
    port=4059,
    connection_interface_type=ConnectionInterfaceType.TCP,
)
p.connect()
