import pytest

from xray_node.config import init_config, Config
from xray_node.utils.install import XrayFile


class TestConfig(object):
    xray_f = XrayFile()
    cfg_f = xray_f.xray_install_path / "xnode.yaml"

    @pytest.mark.asyncio
    async def test_init_config(self):
        await init_config(target=self.cfg_f)
        assert self.cfg_f.exists()

    def test_config_cls(self):
        cfg = Config(cfg=self.cfg_f)
        assert cfg.local_api_host == "127.0.0.1"
        assert cfg.local_api_port == 10085
