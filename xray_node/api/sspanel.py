import logging
from typing import List, Union
from urllib.parse import urljoin, urlparse

from xray_node.api import BaseAPI
from xray_node.api.entities import SSNode, GenericNode, GenericUser, VMessNode, VLessNode, TrojanNode
from xray_node.exceptions import FetchNodeInfoError
from xray_node.utils.consts import SSPANEL_NODE_TYPE

logger = logging.getLogger(__name__)


class SSPanelAPI(BaseAPI):
    """
    SSPanel
    """

    def __init__(self, endpoint: str, mu_key: str, node_id: int):
        super(SSPanelAPI, self).__init__(endpoint=endpoint)
        self.mu_key = mu_key
        self.node_id = node_id

        self.node = None
        self.__prepare_api()

    def __prepare_api(self) -> None:
        self.fetch_node_info_api = urljoin(base=self.endpoint, url=f"/mod_mu/nodes/{self.node_id}/info")
        self.fetch_user_list_api = urljoin(base=self.endpoint, url=f"/mod_mu/users")
        self.report_user_stats_api = self.endpoint

    async def fetch_node_info(self) -> GenericNode:
        req = await self.session.get(url=self.fetch_node_info_api, params={"key", self.mu_key})
        result = req.json()
        ret = result["ret"]
        if ret != 0:
            raise FetchNodeInfoError(msg=result["data"])

        node_data = result["data"]
        _type = SSPANEL_NODE_TYPE.get(int(node_data["sort"]))

        if _type == "ss":
            self.node = self.parse_ss(raw_data=node_data["server"])
        elif _type == "vmess":
            self.node = self.parse_vmess(raw_data=node_data["server"])
        elif _type == "trojan":
            self.node = self.parse_trojan(raw_data=node_data["server"])

        return self.node

    def parse_ss(self, raw_data: str) -> SSNode:
        """
        解析SS信息
        :param raw_data:
        :return:
        """
        parts = raw_data.split(";")
        ip = parts[0]
        extra = parts[1].split("|")

        conn_port, listen_port = 0, 0
        for item in extra:
            key, value = item.split("=", maxsplit=1)
            if key == "":
                continue

            if key == "port":
                conn_port, listen_port = value.split("#", maxsplit=1)

        node = SSNode(node_id=self.node_id, panel_name=urlparse(self.endpoint).netloc, listen_port=int(listen_port))
        return node

    def parse_vmess(self, raw_data: str) -> Union[VMessNode, VLessNode]:
        """
        解析VMess信息
        :return:
        """
        is_vless = False
        parts = raw_data.split(";")

        ip, port, alter_id = parts[0:3]

        transport, tls = parts[3:5]
        if tls:
            tls_type = tls
            enable_tls = True
        else:
            tls_type = None
            enable_tls = False

        extra = parts[5].split("|")
        host, path = "", ""
        for item in extra:
            key, value = item.split("=", maxsplit=1)
            if key == "":
                continue

            if key == "path":
                path = value
            elif key == "host":
                host = value
            elif key == "enable_vless":
                if value == "true":
                    is_vless = True
                else:
                    is_vless = False
            elif key == "inside_port":
                port = int(value)

        if is_vless:
            node = VLessNode(
                node_id=self.node_id,
                panel_name=urlparse(self.endpoint).netloc,
                listen_port=int(port),
                alter_id=alter_id,
                transport=transport,
                enable_tls=enable_tls,
                tls_type=tls_type,
                path=path,
                host=host,
            )
        else:
            node = VMessNode(
                node_id=self.node_id,
                panel_name=urlparse(self.endpoint).netloc,
                listen_port=int(port),
                alter_id=alter_id,
                transport=transport,
                enable_tls=enable_tls,
                tls_type=tls_type,
                path=path,
                host=host,
            )
        return node

    def parse_trojan(self, raw_data: str) -> TrojanNode:
        """
        解析Trojan配置
        :param raw_data:
        :return:
        """
        parts = raw_data.split(";")
        ip = parts[0]
        extra = parts[1].split("|")

        host, conn_port, listen_port, enable_xtls, enable_vless = "", 0, 0, False, False
        for item in extra:
            key, value = item.split("=", maxsplit=1)
            if key == "":
                continue

            if key == "port":
                conn_port, listen_port = value.split("#", maxsplit=1)
            elif key == "host":
                host = value
            elif key == "enable_xtls":
                if value == "true":
                    enable_xtls = True
            elif key == "enable_vless":
                if value == "true":
                    enable_vless = True

        node = TrojanNode(
            node_id=self.node_id,
            panel_name=urlparse(self.endpoint).netloc,
            listen_port=int(listen_port),
            host=host,
            enable_xtls=enable_xtls,
            enable_vless=enable_vless,
        )
        return node

    async def fetch_user_list(self) -> List[GenericUser]:
        req = await self.session.get(url=self.fetch_user_list_api, params={"key": self.mu_key, "node_id": self.node_id})
        result = req.json()
        ret = result["ret"]
        if ret != 0:
            raise FetchNodeInfoError(msg=result["data"])

        user_data = req.json()["data"]
        if len(user_data) > 0:
            logger.info(f"获取用户信息成功，本次获取到 {len(user_data)} 个用户信息")
            return [self.parse_user(data=u) for u in user_data]
        else:
            logger.warning(f"未获取到有效用户")
            return []

    def parse_user(self, data: dict) -> GenericUser:
        """
        从API数据解析用户信息
        :return:
        """
        uid = data.get("id", -1)
        email = data.get("email", f"{uid}")
        sspanel_user = SSPanelUser(id=uid, email=email, password=data.get("passwd", ""))
        return sspanel_user

    async def report_user_stats(self, user_data: list = None) -> None:
        if user_data is None:
            user_data = []

        req = await self.session.post(url=self.report_user_stats_api, json={"user_stats": user_data})
        status = req.json()["status"]
        message = req.json()["message"]
        if status:
            logger.info(f"上报用户信息成功")
        else:
            logger.info(f"上报用户信息异常 {message}")
