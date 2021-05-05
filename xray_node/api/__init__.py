from __future__ import annotations

from typing import Union, Type

from xray_node.api.sspanel import SSPanelAPI
from xray_node.api.v2board import V2BoardAPI
from xray_node.exceptions import UnsupportedAPI
from xray_node.utils import http


class BaseAPI(object):
    """
    API基类
    """

    session = http.client

    def __init__(self, endpoint: str = ""):
        self.endpoint = endpoint
        self.fetch_user_list_api = ""
        self.report_user_online_ip_api = ""

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

    async def report_user_traffic(self, traffic_data: list) -> bool:
        """
        上报用户流量信息
        :param traffic_data:
        :return:
        """
        raise NotImplementedError("report_user_traffic method not defined")

    async def report_user_stats(self, stats_data: list) -> bool:
        """
        上报用户状态信息
        :param stats_data:
        :return:
        """
        raise NotImplementedError("report_user_stats method not defined")


def get_api_cls_by_name(panel_type: str) -> Union[Type[SSPanelAPI], Type[V2BoardAPI]]:
    """
    获取API操作类
    :param panel_type:
    :return:
    """
    panel_dict = {"sspanel": SSPanelAPI, "v2board": V2BoardAPI}

    cls = panel_dict.get(panel_type)
    if cls is None:
        raise UnsupportedAPI(msg=panel_type)
    else:
        return cls
