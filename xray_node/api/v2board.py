from typing import Union, List
from urllib.parse import urljoin, urlparse

from loguru import logger

from xray_node.api import BaseAPI, entities
from xray_node.exceptions import UnsupportedNode, ReportUserTrafficError


class V2BoardAPI(BaseAPI):
    def __init__(self, endpoint: str, node_id: int, api_key: str, node_type: str):
        super(V2BoardAPI, self).__init__(endpoint=endpoint, node_id=node_id, api_key=api_key, node_type=node_type)
        self.token = self.api_key

        self.node = None
        self.multi_user: Union[None, entities.SSUser] = None
        self._prepare_api()

    def _prepare_api(self) -> None:
        # V2ray
        if self.node_type in ("vmess", "vless"):
            self.fetch_user_list_api = urljoin(self.endpoint, "/api/v1/server/Deepbwork/user")
            self.fetch_node_info_api = urljoin(self.endpoint, "/api/v1/server/Deepbwork/config")
            self.report_user_traffic_api = urljoin(self.endpoint, "/api/v1/server/Deepbwork/submit")
        # Shadowsocks
        elif self.node_type == "shadowsocks":
            self.fetch_user_list_api = urljoin(self.endpoint, "/api/v1/server/ShadowsocksTidalab/user")
            self.fetch_node_info_api = urljoin(self.endpoint, "")
            self.report_user_traffic_api = urljoin(self.endpoint, "/api/v1/server/ShadowsocksTidalab/submit")
        # Trojan
        elif self.node_type == "trojan":
            self.fetch_user_list_api = urljoin(self.endpoint, "/api/v1/server/TrojanTidalab/user")
            self.fetch_node_info_api = urljoin(self.endpoint, "/api/v1/server/TrojanTidalab/config")
            self.report_user_traffic_api = urljoin(self.endpoint, "/api/v1/server/TrojanTidalab/submit")
        else:
            raise UnsupportedNode(msg=self.node_type)

    async def fetch_node_info(self):
        req = await self.session.get(
            self.fetch_node_info_api, params={"node_id": self.node_id, "token": self.token, "local_port": 1}
        )
        result = self.parse_resp(req=req)

        if self.node_type in ("vmess", "vless"):
            self.node = self.parse_vmess(result)
        elif self.node_type == "shadowsocks":
            self.node = self.parse_ss(result)
        elif self.node_type == "trojan":
            self.node = self.parse_trojan(result)
        else:
            raise UnsupportedNode(msg=self.node_type)

        return self.node

    async def report_node_stats(self):
        return

    def handle_multi_user(self):
        """
        v2board节点部分信息保存在用户数据中
        :return:
        """
        if self.multi_user and self.node_type == "shadowsocks" and self.node:
            self.node.listen_port = self.multi_user.listen_port
            self.node.method = self.multi_user.method
        else:
            logger.debug("不满足合并单端口承载用户信息条件，跳过")

    def parse_ss(self, raw_data: dict) -> entities.SSNode:
        node = entities.SSNode(
            node_id=self.node_id,
            panel_name=urlparse(self.endpoint).netloc,
            listen_port=0,
            listen_host="0.0.0.0",
        )
        return node

    def parse_vmess(self, raw_data: dict) -> entities.VMessNode:
        inbound_info = raw_data.get("inbound", {})
        port = inbound_info.get("port", 0)
        transport = inbound_info.get("streamSettings", {}).get("network", "")
        enable_tls = inbound_info.get("streamSettings", {}).get("security") == "tls"

        host, path = "", ""
        if transport == "ws":
            host = inbound_info.get("streamSettings", {}).get("wsSettings", {}).get("headers", "")
            path = inbound_info.get("streamSettings", {}).get("wsSettings", {}).get("path", "")

        node = entities.VMessNode(
            node_id=self.node_id,
            panel_name=urlparse(self.endpoint).netloc,
            listen_host="0.0.0.0",
            listen_port=port,
            alter_id=0,
            transport=transport,
            enable_tls=enable_tls,
            tls_type="tls",
            host=host,
            path=path,
        )
        return node

    def parse_trojan(self, raw_data: dict) -> entities.TrojanNode:
        host = raw_data.get("ssl", {}).get("sni", "")
        port = raw_data.get("local_port", 0)

        node = entities.TrojanNode(
            node_id=self.node_id,
            panel_name=urlparse(self.endpoint).netloc,
            listen_port=port,
            listen_host="0.0.0.0",
            host=host,
            enable_xtls=False,
            enable_vless=False,
        )
        return node

    async def fetch_user_list(self) -> list:
        req = await self.session.get(
            self.fetch_user_list_api, params={"node_id": self.node_id, "token": self.token, "local_port": 1}
        )
        result = self.parse_resp(req=req)

        user_data = result["data"]
        if len(user_data) > 0:
            logger.info(f"获取用户信息成功，本次获取到 {len(user_data)} 个用户信息")
            users = [self.parse_user(data=u, idx=idx) for idx, u in enumerate(user_data)]
        else:
            logger.warning(f"未获取到有效用户")
            users = []

        self.handle_multi_user()
        return users

    async def report_user_stats(self, stats_data: list) -> bool:
        pass

    async def report_user_traffic(self, traffic_data: List[entities.V2BoardTrafficData]) -> bool:
        post_body = [{"user_id": d.user_id, "u": d.upload, "d": d.download} for d in traffic_data]
        req = await self.session.post(
            url=self.report_user_traffic_api, params={"node_id": self.node_id, "token": self.token}, json=post_body
        )
        result = self.parse_resp(req=req)
        ret = result["ret"]
        if ret != 1:
            raise ReportUserTrafficError(msg=result["data"])
        else:
            return True

    def parse_user(self, data: dict, idx: int = 0):
        uid = data.get("id", -1)
        email = data.get("email", f"{uid}@{urlparse(self.endpoint).netloc}")
        speed_limit = 0

        if self.node_type is None:
            raise Exception("节点信息未获取")

        if self.node_type == "shadowsocks":
            user = entities.SSUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                password=data.get("secret", ""),
                method=data.get("cipher"),
                is_multi_user=idx == 0,
                listen_port=data.get("port", 0),
            )
            if idx == 0 and self.multi_user is None:
                self.multi_user = user

        elif self.node_type in ("vmess", "vless"):
            user = entities.VMessUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                uuid=data.get("trojan_user", {}).get("uuid", ""),
            )
            if idx == 0:
                self.node.alter_id = data.get("alter_id", 0)
        elif self.node_type == "trojan":
            user = entities.TrojanUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                uuid=data.get("v2ray_user", {}).get("uuid", ""),
            )
        else:
            raise

        return user
