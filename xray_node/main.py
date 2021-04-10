import asyncio
import logging
import os
import platform

import click

from xray_node.core.xray import Xray

logger = logging.getLogger(__name__)


class XrayNode(object):
    def __init__(self):
        self.__prepared = False

    def __init_config(self) -> None:
        self.config = {
            "LISTEN_HOST": os.getenv("SS_LISTEN_HOST", "0.0.0.0"),
            "SENTRY_DSN": os.getenv("SS_SENTRY_DSN"),
            "API_ENDPOINT": os.getenv("SS_API_ENDPOINT"),
            "LOG_LEVEL": os.getenv("SS_LOG_LEVEL", "INFO"),
            "SYNC_TIME": int(os.getenv("SS_SYNC_TIME", 60)),
            "STREAM_DNS_SERVER": os.getenv("SS_STREAM_DNS_SERVER"),
            "TIME_OUT_LIMIT": int(os.getenv("SS_TIME_OUT_LIMIT", 60)),
            "USER_TCP_CONN_LIMIT": int(os.getenv("SS_TCP_CONN_LIMIT", 60)),
            "PANEL_TYPE": os.getenv("PANEL_TYPE", None),
        }
        self.log_level = self.config["LOG_LEVEL"]
        self.sync_time = self.config["SYNC_TIME"]
        self.sentry_dsn = self.config["SENTRY_DSN"]
        self.listen_host = self.config["LISTEN_HOST"]
        self.api_endpoint = self.config["API_ENDPOINT"]
        self.panel_type = self.config["PANEL_TYPE"]
        self.timeout_limit = self.config["TIME_OUT_LIMIT"]
        self.stream_dns_server = self.config["STREAM_DNS_SERVER"]
        self.user_tcp_conn_limit = self.config["USER_TCP_CONN_LIMIT"]

        self.use_sentry = True if self.sentry_dsn else False
        self.use_json = False if self.api_endpoint or self.panel_type else True

    def __prepare_logger(self) -> None:
        """
        初始化日志类
        :return:
        """
        log_levels = {
            "CRITICAL": logging.CRITICAL,
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
        }
        level = log_levels[self.log_level.upper()]
        logging.basicConfig(
            format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)s - %(message)s",
            level=level,
        )

    def __init_loop(self) -> None:
        """
        初始化事件循环
        :return:
        """
        is_win = platform.system().lower() == "windows"
        if not is_win:
            import uvloop

            logger.info("使用 uvloop 加速")
            uvloop.install()
        else:
            logger.info("使用原生 asyncio")

        self.loop = asyncio.get_event_loop()

    def __prepare(self) -> None:
        """
        预处理
        :return:
        """
        if self.__prepared:
            return

        self.__init_config()
        self.__prepare_logger()
        self.__init_loop()

        self.xray = Xray()

        self.__prepared = True

    def __shutdown(self) -> None:
        """
        停止所有服务
        :return:
        """
        logger.info("正在关闭 Xray 服务")
        self.loop.run_until_complete(self.xray.stop())
        if self.loop.is_running():
            self.loop.stop()

    def __run_loop(self) -> None:
        """
        启动事件循环
        :return:
        """
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.__shutdown()

    def start(self) -> None:
        """
        启动服务
        :return:
        """
        self.__prepare()
        self.loop.create_task(self.xray.start())
        self.__run_loop()


@click.command()
def main():
    """
    xray_node is a nice tool to manage ss/vmess/vless proxy nodes based on xray-core.
    """
    pass


if __name__ == "__main__":
    main()
