from fastapi import FastAPI
from dlms_meter_communication.core.config import config
from dlms_meter_communication.core.logging import setup_logging

# logger = setup_logging()

# app = FastAPI(
#     title=config.project_title,
#     description=config.project_description,
#     version=config.project_version,
#     contact={
#         "name": config.project_contact_name,
#         "email": config.project_contact_email,
#     },
# )

from dlms_meter_communication.services.dlms_client_service.main import client

client.connect()

print(client.get_objects())

# from socket import socket, AF_INET, SOCK_STREAM
# from gurux_dlms import GXDLMSClient
# from gurux_dlms.enums import InterfaceType

# HOST = "10.105.39.91"
# PORT = 4060

# client = GXDLMSClient(
#     useLogicalNameReferencing=True,
#     clientAddress=16,
#     serverAddress=1,
#     interfaceType=InterfaceType.HDLC,
# )

# try:
#     s = socket(AF_INET, SOCK_STREAM)
#     s.settimeout(10)  # evita bloqueos eternos

#     print(f"Conectando a {HOST}:{PORT} ...")
#     s.connect((HOST, PORT))
#     print("Conectado ✅")

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

# except Exception as e:
#     print(f"Error durante la conexión o envío: {e}")

# finally:
#     s.close()
#     print("Socket cerrado ✅")
