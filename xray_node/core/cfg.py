from xray_node.config import Config

BASE_CFG = {"log": {}, "api": {}, "dns": {}, "stats": {}, "policy": {}, "transport": {}, "routing": {}, "inbounds": []}

API_CFG = {"api": {"tag": "api", "services": ["HandlerService", "LoggerService", "StatsService"]}}

POLICY_CFG = {
    "policy": {
        "levels": {
            "0": {
                "statsUserUplink": True,
                "statsUserDownlink": True,
            }
        },
        "system": {
            "statsInboundUplink": True,
            "statsInboundDownlink": True,
            "statsOutboundUplink": True,
            "statsOutboundDownlink": True,
        },
    }
}

ROUTING_CFG = {
    "routing": {
        "settings": {"rules": [{"inboundTag": ["api"], "outboundTag": "api", "type": "field"}]},
        "strategy": "rules",
    },
}


def get_inbound_cfg(cfg_cls: Config):
    return {
        "inbounds": [
            {
                "listen": cfg_cls.local_api_host,
                "port": cfg_cls.local_api_port,
                "protocol": "dokodemo-door",
                "settings": {"address": cfg_cls.local_api_host},
                "tag": "api",
            },
        ]
    }


OUTBOUNDS_CFG = {"outbounds": [{"protocol": "freedom"}]}
