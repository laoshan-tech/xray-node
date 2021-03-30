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

INBOUNDS_CFG = {
    "inbounds": [
        {
            "listen": "127.0.0.1",
            "port": 10085,
            "protocol": "dokodemo-door",
            "settings": {"address": "127.0.0.1"},
            "tag": "api",
        },
    ]
}

OUTBOUNDS_CFG = {"outbounds": [{"protocol": "freedom"}]}
