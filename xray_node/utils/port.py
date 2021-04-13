import asyncio
import logging

logger = logging.getLogger(__name__)


async def check_port_alive(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    检测端口开放
    :param host:
    :param port:
    :param timeout:
    :return:
    """
    try:
        future = asyncio.open_connection(host=host, port=port)
        reader, writer = await asyncio.wait_for(future, timeout=timeout)
        writer.close()
        return True
    except (ConnectionRefusedError, asyncio.TimeoutError):
        logger.warning(f"{host}:{port} 端口关闭或连接超时")
        return False
    except Exception as e:
        logger.error(f"{host}:{port} 连接异常，{e}")
        return False
