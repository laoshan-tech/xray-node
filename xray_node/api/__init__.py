from __future__ import annotations

from json import JSONDecodeError
from typing import Union, Type, TYPE_CHECKING

import httpx
from loguru import logger

from xray_node.exceptions import UnsupportedAPI, APIStatusError, APIContentError
from xray_node.utils import http

if TYPE_CHECKING:
    from xray_node.api.sspanel import SSPanelAPI
    from xray_node.api.v2board import V2BoardAPI


class BaseAPI(object):
    """
    API基类
    """

    session = http.client

    def __init__(self, endpoint: str = ""):
        self.endpoint = endpoint
        self.fetch_user_list_api = ""
        self.report_user_online_ip_api = ""

    def _prepare_api(self) -> None:
        """
        拼装API地址
        :return:
        """
        return

    @staticmethod
    def parse_resp(req: httpx.Response) -> dict:
        """
        解析响应包
        :param req:
        :return:
        """
        if req.status_code >= 400:
            logger.error(f"请求 {req.url} 出错，响应详情 {req.text}")
            raise APIStatusError(msg=req.status_code)
        else:
            try:
                d = req.json()
                return d
            except JSONDecodeError:
                logger.error(f"请求 {req.url} 解析JSON失败，响应详情 {req.text}")
                raise APIContentError(msg=req.text)

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
    from xray_node.api.sspanel import SSPanelAPI
    from xray_node.api.v2board import V2BoardAPI

    panel_cls_dict = {"sspanel": SSPanelAPI, "v2board": V2BoardAPI}

    cls = panel_cls_dict.get(panel_type)
    if cls is None:
        raise UnsupportedAPI(msg=panel_type)
    else:
        return cls
