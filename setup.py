#!/usr/bin/env python
import setuptools

import sys

REQUIRED_PACKAGES= [
    "SMHI-python3-radar_pyutils",
    "python3-pyasn1",
    "python3-pycryptodomex",
    "python3-inotify",
    "python3-daemon",
    "werkzeug"
]

setuptools.setup(name="bexchange",
    version="0.1",
    namespace_packages=["bexchange"],
    setup_requires=[],
    packages=setuptools.find_packages(
        "src",
    ),
    package_dir={
        "": "src"
    },
    package_data={
        "": ["*.sql", "*.cfg"]
    },
    install_requires=REQUIRED_PACKAGES,
    entry_points = {
        "bexchange.auth": [
            "noauth = bexchange.auth:NoAuth",
            "tink = bexchange.auth.tinkauth:TinkAuth",
            "crypto = bexchange.auth.coreauth:CryptoAuth",
            "keyczar = bexchange.auth.keyczarauth:KeyczarAuth"
        ],
        "bexchange.client.commands": [
            "store = bexchange.client.cmd:StoreFile",
            "batchtest = bexchange.client.cmd:BatchTest",
            "post_message = bexchange.client.cmd:PostJsonMessage",
            "get_statistics = bexchange.client.cmd:GetStatistics",
            "list_statistic_ids = bexchange.client.cmd:ListStatisticIds",
            "server_info = bexchange.client.cmd:ServerInfo",
        ],
        "bexchange.config.commands": [
            "create_keys = bexchange.client.cfgcmd:CreateKeys",
            "test_filter = bexchange.client.cfgcmd:TestFilter",
            "create_publication = bexchange.client.cfgcmd:CreatePublication",
            "create_subscription = bexchange.client.cfgcmd:CreateSubscription",
        ],
        "console_scripts" : [
            "baltrad-exchange-server = bexchange.server_main:run",
            "baltrad-exchange-client = bexchange.client_main:run",
            "baltrad-exchange-config = bexchange.config_main:run"
        ]
    },
    test_suite="nose.collector",
    tests_require=[
        "mock >= 0.7",
    ],
)
