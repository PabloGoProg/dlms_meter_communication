from __future__ import annotations

from ...ports import IAppLayer

from dataclasses import dataclass
from typing import Any, Optional
from gurux_dlms import GXDLMSClient, GXReplyData, GXByteBuffer, GXDLMSTranslator
from gurux_dlms.enums import Authentication, InterfaceType
from gurux_net import GXNet
from gurux_common import ReceiveParameters

from dlms_meter_communication.schemas import Device, NegotiatedParams


class GuruxCOSEMApp(IAppLayer):
    def __init__(self, use_logical_name_referencing: bool = True):
        self._media = None
        self._use_logical_name_referencing = use_logical_name_referencing

        self._gx_dlms_client = GXDLMSClient(
            useLogicalNameReferencing=self._use_logical_name_referencing,
        )

        self._max_apdu = 0xFFFF  # 64K
        self._conformance = GXDLMSClient.getInitialConformance(
            self._use_logical_name_referencing
        )

        self._is_connected = False

    def associate(self, device: Device, nps: NegotiatedParams) -> None:
        self._connection.open()
        self._is_connected = True

        snrm = self._gx_dlms_client.snrmRequest()

        if (
            self._gx_dlms_client.getInterfaceType() != InterfaceType.WRAPPER
            and snrm is not None
        ):
            self._link_layer.send_apdu(snrm)
            ua = self._link_layer.receive_apdu()
            self._gx_dlms_client.parseUAResponse(ua)

        aarq = self._gx_dlms_client.aarqRequest()
        for frame in aarq:
            self._link_layer.send_apdu(frame)

        aare = self._link_layer.receive_apdu()
        self._gx_dlms_client.parseAareResponse(aare)

        max_pdu = self._gx_dlms_client.getMaxReceivePDUSize()
        self._link_layer._max_pdu_hint = max_pdu

    def get(self, obis_code: str) -> any:
        pass

    def set(self, obis_code: str, value: any) -> None:
        pass

    def action(self, obis_code: str, action: str) -> None:
        pass

    def disconnect(self) -> None:
        if self._link_layer:
            reply = GXReplyData()

            try:
                if self._gx_dlms_client.getInterfaceType() == InterfaceType.WRAPPER:
                    pass
            except Exception:
                pass  # All meters do not support this request

        reply.clear()

    def _read_dlms_packet(self, data, reply: GXReplyData = None) -> bytes:
        if not reply:
            reply = GXReplyData()

        if isinstance(data, bytearray()):
            pass
        elif data:
            for frame in data:
                reply.clear()
                pass

    def _exchange_packet(self, data: bytes, reply: GXReplyData = None) -> bytes:
        if not data:
            raise ValueError("Data cannot be empty")

        notify = GXReplyData()
        eop = (
            0x7E
            if self._gx_dlms_client.getInterfaceType() == InterfaceType.HDLC
            else None
        )

        params = ReceiveParameters()
        params.eop = eop
        params.allData = True
        params.waitTime = 10000

        if eop is None:
            params.count = 0
        else:
            params.count = 5

        buffer = GXByteBuffer()
        pos = 0

        try:
            while not self._gx_dlms_client.getData(buffer, reply, notify):
                if notify.data.size > 0:
                    if not notify.isMoreData():
                        t = GXDLMSTranslator()
                        xml = t.dataToXml(notify.data)
                        print(f"XML: {xml}")
                        notify.clear()
                    continue

                if not params.eop:
                    params.count = self._gx_dlms_client.getFrameSize(buffer)

            while not self._connection.receive(params):
                pass

        except Exception:
            pass
