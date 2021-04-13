import uuid

import pytest

from xray_node.core.xray import Xray, VMessInbound, VLESSInbound, ShadowsocksInbound, TrojanInbound
from xray_node.utils.consts import CIPHER_TYPE_DICT
from xray_node.utils.install import XrayFile
from xray_node.utils.port import check_port_alive


class TestXray(object):
    xray_f = XrayFile()
    xray = Xray(xray_f=xray_f)

    email = "a@test.com"
    host = "127.0.0.1"
    vmess_p = 60001
    vless_p = 60002
    ss_p = 60003
    trojan_p = 60004

    @pytest.mark.asyncio
    async def test_start_xray(self):
        await self.xray.start()
        assert await self.xray.is_running() is True

    @pytest.mark.asyncio
    async def test_add_inbound(self):
        vmess_proto = VMessInbound(email=self.email, level=0, alter_id=64, user_id=str(uuid.uuid4()))
        await self.xray.add_inbound(
            inbound_tag="vmess_test", address=self.host, port=self.vmess_p, protocol=vmess_proto
        )
        assert await check_port_alive(host=self.host, port=self.vmess_p) is True

        vless_proto = VLESSInbound(email=self.email, level=0, flow="", user_id=str(uuid.uuid4()))
        await self.xray.add_inbound(
            inbound_tag="vless_test", address=self.host, port=self.vless_p, protocol=vless_proto
        )
        assert await check_port_alive(host=self.host, port=self.vless_p) is True

        ss_proto = ShadowsocksInbound(
            email=self.email, level=0, password="test", cipher_type=CIPHER_TYPE_DICT["aes-256-gcm"]
        )
        await self.xray.add_inbound(inbound_tag="ss_test", address=self.host, port=self.ss_p, protocol=ss_proto)
        assert await check_port_alive(host=self.host, port=self.ss_p) is True

        trojan_proto = TrojanInbound(email=self.email, level=0, password="test", flow="")
        await self.xray.add_inbound(
            inbound_tag="trojan_test", address=self.host, port=self.trojan_p, protocol=trojan_proto
        )
        assert await check_port_alive(host=self.host, port=self.trojan_p) is True

    @pytest.mark.asyncio
    async def test_remove_inbound(self):
        await self.xray.remove_inbound(inbound_tag="vmess_test")
        assert await check_port_alive(host=self.host, port=self.vmess_p) is False

        await self.xray.remove_inbound(inbound_tag="vless_test")
        assert await check_port_alive(host=self.host, port=self.vless_p) is False

        await self.xray.remove_inbound(inbound_tag="ss_test")
        assert await check_port_alive(host=self.host, port=self.ss_p) is False

        await self.xray.remove_inbound(inbound_tag="trojan_test")
        assert await check_port_alive(host=self.host, port=self.trojan_p) is False

    @pytest.mark.asyncio
    async def test_stop_xray(self):
        await self.xray.stop()
        assert await self.xray.is_running() is False
