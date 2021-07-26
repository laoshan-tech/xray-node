from urllib.parse import urlparse

import pytest
from pytest_httpserver import HTTPServer

from xray_node.api.sspanel import SSPanelAPI
from xray_node.utils.consts import NodeTypeEnum


class TestSSPanel(object):
    HTTPServer.DEFAULT_LISTEN_PORT = 50650

    ss_server = "hk.aaa.com;port=12345#23456"
    vmess_server = (
        "1.3.5.7;443;2;ws;tls;path=/v2ray|server=hk.domain.com|host=hk.domain.com|outside_port=34567|inside_port=12345"
    )
    trojan_server = "gz.aaa.com;port=443#12345|host=hk.aaa.com"

    api = SSPanelAPI(endpoint=f"http://127.0.0.1:{HTTPServer.DEFAULT_LISTEN_PORT}/", api_key="sspanel_test", node_id=2)

    def test_parse_ss(self):
        node = self.api.parse_ss(raw_data=self.ss_server)
        assert node.node_id == 2
        assert node.listen_port == 23456

    def test_parse_vmess(self):
        node = self.api.parse_vmess(raw_data=self.vmess_server)
        assert node.node_id == 2
        assert node.host == "hk.domain.com"
        assert node.listen_port == 12345
        assert node.transport == "ws"
        assert node.path == "/v2ray"
        assert node.enable_tls is True
        assert node.tls_type == "tls"

    def test_parse_trojan(self):
        node = self.api.parse_trojan(raw_data=self.trojan_server)
        assert node.node_id == 2
        assert node.listen_port == 12345
        assert node.host == "hk.aaa.com"

    @pytest.mark.asyncio
    async def test_fetch_info(self, httpserver: HTTPServer):
        node_uri = urlparse(self.api.fetch_node_info_api).path
        node_handler = httpserver.expect_request(uri=node_uri, query_string=f"key={self.api.mu_key}")
        node_handler.respond_with_json(
            response_json={
                "ret": 1,
                "data": {
                    "node_group": 0,
                    "node_class": 0,
                    "node_speedlimit": 0,
                    "traffic_rate": 1,
                    "mu_only": 1,
                    "sort": 0,
                    "server": "1.1.1.1",
                    "disconnect_time": 60,
                    "type": "SSPanel-UIM",
                },
            }
        )

        user_uri = urlparse(self.api.fetch_user_list_api).path
        user_handler = httpserver.expect_request(
            uri=user_uri, query_string=f"key={self.api.mu_key}&node_id={self.api.node_id}"
        )
        user_handler.respond_with_json(
            response_json={
                "ret": 1,
                "data": [
                    {
                        "id": 1,
                        "passwd": "tVuKjjs0o04CxCac",
                        "u": 0,
                        "d": 0,
                        "transfer_enable": 1073741824,
                        "port": 1025,
                        "method": "rc4-md5",
                        "node_speedlimit": 0,
                        "node_connector": 0,
                        "protocol": "origin",
                        "protocol_param": None,
                        "obfs": "plain",
                        "obfs_param": None,
                        "is_multi_user": 0,
                    },
                    {
                        "id": 2,
                        "passwd": "Km9smW54mcZglG0L",
                        "u": 0,
                        "d": 0,
                        "transfer_enable": 1073741824,
                        "port": 14001,
                        "method": "aes-256-gcm",
                        "node_speedlimit": 0,
                        "node_connector": 0,
                        "protocol": "origin",
                        "protocol_param": "",
                        "obfs": "plain",
                        "obfs_param": "",
                        "is_multi_user": 1,
                    },
                    {
                        "id": 3,
                        "passwd": "oZGK1wrsvOClrJld",
                        "u": 0,
                        "d": 0,
                        "transfer_enable": 1073741824,
                        "port": 38375,
                        "method": "chacha20-ietf",
                        "node_speedlimit": 0,
                        "node_connector": 0,
                        "protocol": "auth_aes128_sha1",
                        "protocol_param": "",
                        "obfs": "http_simple",
                        "obfs_param": "",
                        "is_multi_user": 0,
                    },
                ],
            }
        )

        node = await self.api.fetch_node_info()
        users = await self.api.fetch_user_list()

        assert self.api.node_type == NodeTypeEnum.Shadowsocks
        assert node.node_id == 2
        assert node.listen_port == 14001
        assert node.method == "aes-256-gcm"
        assert len(users) == 3
