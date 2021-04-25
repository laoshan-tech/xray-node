from xray_node.api.sspanel import SSPanelAPI


class TestSSPanel(object):
    ss_server = "hk.aaa.com;port=12345#23456"
    vmess_server = (
        "1.3.5.7;443;2;ws;tls;path=/v2ray|server=hk.domain.com|host=hk.domain.com|outside_port=34567|inside_port=12345"
    )
    trojan_server = "gz.aaa.com;port=443#12345|host=hk.aaa.com"

    api = SSPanelAPI(endpoint="http://127.0.0.1/", mu_key="sspanel_test", node_id=2)

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
