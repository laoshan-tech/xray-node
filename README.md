# xray-node

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/laoshan-tech/xray-node/Lint?style=flat-square)
![GitHub](https://img.shields.io/github/license/laoshan-tech/xray-node?style=flat-square)
![GitHub repo size](https://img.shields.io/github/repo-size/laoshan-tech/xray-node?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/xray-node?color=blue&style=flat-square)
![Slack](https://img.shields.io/badge/news-telegram-26A5E4?style=flat-square&logo=telegram&link=https://t.me/laoshan_tech)
![Slack](https://img.shields.io/badge/chat-telegram-26A5E4?style=flat-square&logo=telegram&link=https://t.me/laoshan_tech_discuss)

## 简介

Python 开发的基于 [xray-core](https://github.com/XTLS/Xray-core) 的多用户代理后端，支持用户动态管理和流量统计，暂不支持限速和审计。

> _仍处于开发阶段，暂不能提供完整功能。_

## 特性

- xray-core 提供的完整特性
    - VMess
    - VLESS
    - SS（支持单端口多用户）
    - Trojan
- 自动安装、更新 xray-core
- 支持多种用户管理系统（开发中）
    - SSPanel
    - django-sspanel
    - v2board