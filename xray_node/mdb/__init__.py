from loguru import logger
from tortoise import Tortoise


async def init_db():
    logger.info("初始化内存数据库")
    await Tortoise.init(db_url="sqlite://:memory:", modules={"models": ["xray_node.mdb.models"]})
    await Tortoise.generate_schemas()
