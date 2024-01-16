#!/usr/bin/env python
import setuptools

import sys

REQUIRED_PACKAGES= [
    "baltradutils",
    "baltradcrypto",
    "baltrad.bdbcommon",
    "baltrad.bdbclient",
    "pyinotify",
    "python-daemon >= 1.6",
    "werkzeug >= 2.0.2",
    "sqlalchemy >= 1.4.31, < 2.0",
    "sqlalchemy-migrate >= 0.13",
    "cherrypy >= 18.6.1",
    "paramiko >= 2.9.3, < 3.0",
    "scp >= 0.13.0, < 0.15"
]

# If we can't get hold of pyhl we install h5py instead
try:
    import _pyhl
except ModuleNotFoundError:
    REQUIRED_PACKAGES.append("h5py >= 3.6, < 4.0")

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
            "file_arrival = bexchange.client.cmd:FileArrival",
        ],
        "bexchange.config.commands": [
            "create_keys = bexchange.client.cfgcmd:CreateKeys",
            "test_filter = bexchange.client.cfgcmd:TestFilter",
            "create_publication = bexchange.client.cfgcmd:CreatePublication",
            "create_subscription = bexchange.client.cfgcmd:CreateSubscription",
        ],
        "bexchange.zmq.commands": [
            "monitor = bexchange.client.zmqcmd:Monitor",
        ],
        "console_scripts" : [
            "baltrad-exchange-server = bexchange.server_main:run",
            "baltrad-exchange-client = bexchange.client_main:run",
            "baltrad-exchange-config = bexchange.config_main:run",
            "baltrad-exchange-zmq = bexchange.zmq_main:run"
        ]
    },
    test_suite="nose.collector",
    tests_require=[
        "mock >= 0.7",
    ],
)
