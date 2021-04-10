from pathlib import Path

import pytest

from xray_node.config import init_config, Config


class TestConfig(object):
    @pytest.mark.asyncio
    async def test_init_config(self):
        fn = Path("./xnode.yaml")
        init_config(target=fn)
        assert fn.exists()

    def test_config_cls(self):
        cfg = Config()
        assert cfg.local_api_host == "127.0.0.1"
        assert cfg.local_api_port == 10085
