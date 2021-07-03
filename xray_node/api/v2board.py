from urllib.parse import urljoin, urlparse

from loguru import logger

from xray_node.api import BaseAPI, entities
from xray_node.exceptions import UnsupportedNode


class V2BoardAPI(BaseAPI):
    def __init__(self, endpoint: str, node_type: str, node_id: int):
        super(V2BoardAPI, self).__init__(endpoint=endpoint)
        self.node_type = node_type
        self.node_id = node_id

    def _prepare_api(self) -> None:
        if self.node_type == "V2ray":
            self.fetch_user_list_api = urljoin(self.endpoint, "/api/v1/server/Deepbwork/user")
            self.fetch_node_info_api = urljoin(self.endpoint, "/api/v1/server/Deepbwork/config")
        elif self.node_type == "Shadowsocks":
            self.fetch_user_list_api = urljoin(self.endpoint, "/api/v1/server/ShadowsocksTidalab/user")
            self.fetch_node_info_api = urljoin(self.endpoint, "")
        elif self.node_type == "Trojan":
            self.fetch_user_list_api = urljoin(self.endpoint, "/api/v1/server/TrojanTidalab/user")
            self.fetch_node_info_api = urljoin(self.endpoint, "/api/v1/server/TrojanTidalab/config")
        else:
            raise UnsupportedNode(msg=self.node_type)

    def fetch_node_info(self):
        req = await self.session.get(self.fetch_node_info_api, params={"node_id": self.node_id})
        result = self.parse_resp(req=req)

    async def fetch_user_list(self) -> list:
        req = await self.session.get(self.fetch_user_list_api, params={"node_id": self.node_id})
        result = self.parse_resp(req=req)

        user_data = result["data"]
        if len(user_data) > 0:
            logger.info(f"获取用户信息成功，本次获取到 {len(user_data)} 个用户信息")
            users = [self.parse_user(data=u) for u in user_data]
        else:
            logger.warning(f"未获取到有效用户")
            users = []

        return users

    def report_user_stats(self, stats_data: list) -> bool:
        pass

    def report_user_traffic(self, traffic_data: list) -> bool:
        pass

    def parse_user(self, data: dict):
        uid = data.get("id", -1)
        email = data.get("email", f"{uid}@{urlparse(self.endpoint).netloc}")
        speed_limit = 0

        if self.node_type is None:
            raise Exception("节点信息未获取")

        if self.node_type == "Shadowsocks":
            user = entities.SSUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                password=data.get("passwd", ""),
                method=data.get("method"),
                is_multi_user=data.get("is_multi_user", 0),
                listen_port=data.get("port", 0),
            )
            if user.is_multi_user > 0 and self.multi_user is None:
                self.multi_user = user

        elif self.node_type == "V2ray":
            user = entities.VMessUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                uuid=data.get("uuid", ""),
            )
        elif self.node_type == "Trojan":
            user = entities.TrojanUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                uuid=data.get("uuid", ""),
            )
        else:
            raise

        return user
