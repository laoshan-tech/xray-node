from xray_node.utils import http


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
