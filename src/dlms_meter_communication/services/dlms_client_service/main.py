from dlms_meter_communication.services.dlms_client_service.utils.enums import (
    CommunicationProfileType,
    ConnectionProviderType,
)
from .dlms_client import DLMSClient

client = DLMSClient(
    ip_address="10.105.39.91",
    port=4059,
    communication_profile=CommunicationProfileType.HDLC_TUNNELING_PROFILE,
    connection_provider=ConnectionProviderType.SOCKET,
)

client.connect()

# from socket import socket, AF_INET, SOCK_STREAM

# HOST = "10.105.39.91"
# PORT = 4059

# data = b"~\xa0+\x03!\x10\xfb\xaf\xe6\xe6\x00`\x1d\xa1\t\x06\x07`\x85t\x05\x08\x01\x01\xbe\x10\x04\x0e\x01\x00\x00\x00\x06_\x1f\x04\x00@\x1e]\xff\xff\x91#~"

# try:
#     s = socket(AF_INET, SOCK_STREAM)
#     s.settimeout(5)  # evita bloqueos eternos

#     print(f"Conectando a {HOST}:{PORT} ...")
#     s.connect((HOST, PORT))
#     print("Conectado ✅")

#     print(f"AARQ: {data}")
#     s.sendall(data)
#     print("Trama enviada ✅")

#     response = s.recv(1024)
#     print("Respuesta recibida:")
#     print(f"Response: {response}")

# except Exception as e:
#     print(f"Error durante la conexión o envío: {e}")

# finally:
#     s.close()
#     print("Socket cerrado ✅")

# from gurux_dlms import GXDLMSClient, GXReplyData
# from gurux_dlms.enums import InterfaceType
# from socket import socket, AF_INET, SOCK_STREAM

# HOST = "10.105.39.91"
# PORT = 4059

# client = GXDLMSClient(
#     useLogicalNameReferencing=True,
#     clientAddress=16,
#     serverAddress=1,
#     interfaceType=InterfaceType.WRAPPER,
# )

# with socket(AF_INET, SOCK_STREAM) as s:
#     s.settimeout(10)
#     s.connect((HOST, PORT))

#     snrm = client.snrmRequest()
#     if snrm:
#         s.send(snrm)
#         print(f"SNRM: {snrm}")
#         ua = s.recv(1024)
#         print(f"UA: {ua}")

#     aarq = client.aarqRequest()
#     print(f"AARQ: {aarq[0]}")
#     s.send(aarq[0])
#     aare = s.recv(1024)
#     print(f"AARE: {aare}")

#     print("Asociación DLMS establecida ✅")
