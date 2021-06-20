import time
from typing import List, Union
from urllib.parse import urljoin, urlparse

import psutil
from loguru import logger

from xray_node.api import BaseAPI, entities
from xray_node.exceptions import FetchNodeInfoError, ReportNodeStatsError, ReportUserTrafficError, APIStatusError
from xray_node.utils.consts import SSPANEL_NODE_TYPE, NodeTypeEnum


class SSPanelAPI(BaseAPI):
    """
    SSPanel
    """

    def __init__(self, endpoint: str, mu_key: str, node_id: int):
        super(SSPanelAPI, self).__init__(endpoint=endpoint)
        self.mu_key = mu_key
        self.node_id = node_id

        self.node = None
        self.node_type = None
        self.multi_user: Union[None, entities.SSUser] = None
        self.__prepare_api()

    def __prepare_api(self) -> None:
        self.fetch_node_info_api = urljoin(base=self.endpoint, url=f"/mod_mu/nodes/{self.node_id}/info")
        self.fetch_user_list_api = urljoin(base=self.endpoint, url=f"/mod_mu/users")
        self.report_node_stats_api = urljoin(base=self.endpoint, url=f"/mod_mu/nodes/{self.node_id}/info")
        self.report_user_online_ip_api = urljoin(base=self.endpoint, url=f"/mod_mu/users/aliveip")
        self.report_user_traffic_api = urljoin(base=self.endpoint, url=f"/mod_mu/users/traffic")

    async def fetch_node_info(
        self,
    ) -> Union[entities.SSNode, entities.VMessNode, entities.VLessNode, entities.TrojanNode]:
        req = await self.session.get(url=self.fetch_node_info_api, params={"key": self.mu_key})
        if req.status_code != 200:
            raise APIStatusError(msg=req.status_code)
        result = req.json()
        ret = result["ret"]
        if ret != 1:
            raise FetchNodeInfoError(msg=result["data"])

        node_data = result["data"]
        self.node_type = SSPANEL_NODE_TYPE.get(int(node_data["sort"]))

        if self.node_type == NodeTypeEnum.Shadowsocks:
            self.node = self.parse_ss(raw_data=node_data["server"])
        elif self.node_type in (NodeTypeEnum.VMess, NodeTypeEnum.VLess):
            self.node = self.parse_vmess(raw_data=node_data["server"])
        elif self.node_type == NodeTypeEnum.Trojan:
            self.node = self.parse_trojan(raw_data=node_data["server"])
        else:
            raise

        self.handle_ss_multi_user()
        return self.node

    async def report_node_stats(self) -> bool:
        """
        上报节点状态
        :return:
        """
        load = psutil.getloadavg()
        post_body = {"uptime": time.time() - psutil.boot_time(), "load": " ".join(("%.2f" % i for i in load))}

        req = await self.session.post(url=self.report_node_stats_api, params={"key": self.mu_key}, json=post_body)
        if req.status_code != 200:
            raise APIStatusError(msg=req.status_code)
        result = req.json()
        ret = result["ret"]
        if ret != 1:
            raise ReportNodeStatsError(msg=result["data"])
        else:
            return True

    def parse_ss(self, raw_data: str) -> entities.SSNode:
        """
        解析SS信息
        :param raw_data:
        :return:
        """
        parts = raw_data.split(";")
        ip = parts[0]
        extra = parts[1].split("|") if len(parts) >= 2 else []

        conn_port, listen_port = 0, 0
        for item in extra:
            key, value = item.split("=", maxsplit=1)
            if key == "":
                continue

            # 目前拿不到这部分信息，即便配置了也没用
            if key == "port":
                conn_port, listen_port = value.split("#", maxsplit=1)

        node = entities.SSNode(
            node_id=self.node_id,
            panel_name=urlparse(self.endpoint).netloc,
            listen_port=int(listen_port),
            listen_host="0.0.0.0",
        )
        return node

    def parse_vmess(self, raw_data: str) -> Union[entities.VMessNode, entities.VLessNode]:
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
            node = entities.VLessNode(
                node_id=self.node_id,
                panel_name=urlparse(self.endpoint).netloc,
                listen_port=int(port),
                listen_host="0.0.0.0",
                alter_id=alter_id,
                transport=transport,
                enable_tls=enable_tls,
                tls_type=tls_type,
                path=path,
                host=host,
            )
        else:
            node = entities.VMessNode(
                node_id=self.node_id,
                panel_name=urlparse(self.endpoint).netloc,
                listen_port=int(port),
                listen_host="0.0.0.0",
                alter_id=alter_id,
                transport=transport,
                enable_tls=enable_tls,
                tls_type=tls_type,
                path=path,
                host=host,
            )
        return node

    def parse_trojan(self, raw_data: str) -> entities.TrojanNode:
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

        node = entities.TrojanNode(
            node_id=self.node_id,
            panel_name=urlparse(self.endpoint).netloc,
            listen_port=int(listen_port),
            listen_host="0.0.0.0",
            host=host,
            enable_xtls=enable_xtls,
            enable_vless=enable_vless,
        )
        return node

    async def fetch_user_list(self) -> List[entities.GenericUser]:
        req = await self.session.get(url=self.fetch_user_list_api, params={"key": self.mu_key, "node_id": self.node_id})
        if req.status_code != 200:
            raise APIStatusError(msg=req.status_code)
        result = req.json()
        ret = result["ret"]
        if ret != 1:
            raise FetchNodeInfoError(msg=result["data"])

        user_data = req.json()["data"]
        if len(user_data) > 0:
            logger.info(f"获取用户信息成功，本次获取到 {len(user_data)} 个用户信息")
            users = [self.parse_user(data=u) for u in user_data]
        else:
            logger.warning(f"未获取到有效用户")
            users = []

        self.handle_ss_multi_user()
        return users

    def parse_user(self, data: dict) -> entities.GenericUser:
        """
        从API数据解析用户信息
        :return:
        """
        uid = data.get("id", -1)
        email = data.get("email", f"{uid}@{urlparse(self.endpoint).netloc}")
        speed_limit = data.get("node_speedlimit", 0)

        if self.node_type is None:
            raise Exception("节点信息未获取")

        if self.node_type == NodeTypeEnum.Shadowsocks:
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

        elif self.node_type == NodeTypeEnum.VMess:
            user = entities.VMessUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                uuid=data.get("uuid", ""),
            )
        elif self.node_type == NodeTypeEnum.VLess:
            user = entities.VLessUser(
                user_id=uid,
                panel_name=self.node.panel_name,
                node_id=self.node.node_id,
                email=email,
                speed_limit=speed_limit,
                uuid=data.get("uuid", ""),
            )
        elif self.node_type == NodeTypeEnum.Trojan:
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

    def handle_ss_multi_user(self):
        """
        SS单端口多用户时需要单独处理承载用户的情况
        :return:
        """
        if self.multi_user and self.node_type == NodeTypeEnum.Shadowsocks and self.node:
            self.node.listen_port = self.multi_user.listen_port
            self.node.method = self.multi_user.method
        else:
            logger.debug("不满足合并单端口承载用户信息条件，跳过")

    async def report_user_stats(self, stats_data: List[entities.SSPanelOnlineIPData]) -> bool:
        """
        上报用户在线IP
        :param stats_data:
        :return:
        """
        ds = []
        for d in stats_data:
            ds.extend([{"ip": ip, "user_id": d.user_id} for ip in d.ip])
        post_body = {"data": ds}

        req = await self.session.post(
            url=self.report_user_online_ip_api, params={"key": self.mu_key, "node_id": self.node_id}, json=post_body
        )
        result = req.json()
        ret = result["ret"]
        if ret != 1:
            raise ReportNodeStatsError(msg=result["data"])
        else:
            return True

    async def report_user_traffic(self, traffic_data: List[entities.SSPanelTrafficData]) -> bool:
        """
        上报用户流量
        :param traffic_data:
        :return:
        """
        post_body = {"data": [{"user_id": d.user_id, "u": d.upload, "d": d.download} for d in traffic_data]}
        req = await self.session.post(
            url=self.report_user_traffic_api, params={"key": self.mu_key, "node_id": self.node_id}, json=post_body
        )
        result = req.json()
        ret = result["ret"]
        if ret != 1:
            raise ReportUserTrafficError(msg=result["data"])
        else:
            return True
