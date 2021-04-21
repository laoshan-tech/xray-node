import logging
from typing import List
from urllib.parse import urljoin

from xray_node.core.entities import SSPanelUser, SSPanelNode
from xray_node.exceptions import FetchNodeInfoError
from xray_node.utils import http

logger = logging.getLogger(__name__)


class BaseAPI(object):
    """
    API基类
    """

    session = http.client

    def __init__(self, endpoint: str = ""):
        self.endpoint = endpoint
        self.fetch_user_list_api = ""
        self.report_user_stats_api = ""

        self.__prepare_api()

    def __prepare_api(self) -> None:
        """
        拼装API地址
        :return:
        """
        pass

    async def fetch_user_list(self) -> list:
        """
        获取user列表
        :return:
        """
        raise NotImplementedError("fetch_user_list method not defined")

    async def fetch_node_info(self):
        """
        获取节点信息
        :return:
        """
        raise NotImplementedError("fetch_node_info method not defined")

    async def report_user_stats(self, user_data: list) -> None:
        """
        上报user信息
        :param user_data:
        :return:
        """
        raise NotImplementedError("report_user_stats method not defined")


class SSPanelAPI(BaseAPI):
    """
    SSPanel
    """

    def __init__(self, endpoint: str, mu_key: str, node_id: int):
        super(SSPanelAPI, self).__init__(endpoint=endpoint)
        self.mu_key = mu_key
        self.node_id = node_id
        self.__prepare_api()

    def __prepare_api(self) -> None:
        self.fetch_node_info_api = urljoin(base=self.endpoint, url=f"/mod_mu/nodes/{self.node_id}/info")
        self.fetch_user_list_api = urljoin(base=self.endpoint, url=f"/mod_mu/users")
        self.report_user_stats_api = self.endpoint

    async def fetch_node_info(self) -> SSPanelNode:
        req = await self.session.get(url=self.fetch_node_info_api, params={"key", self.mu_key})
        result = req.json()
        ret = result["ret"]
        if ret != 0:
            raise FetchNodeInfoError(msg=result["data"])

        return

    async def fetch_user_list(self) -> List[SSPanelUser]:
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

    def parse_user(self, data: dict) -> SSPanelUser:
        """
        从API数据解析用户信息
        :return:
        """
        uid = data.get("id", -1)
        email = data.get("email", f"{uid}")
        sspanel_user = SSPanelUser(id=uid, email=email, password=data.get("password"))
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
