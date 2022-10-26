#!/usr/bin/env python
import setuptools

import sys

REQUIRED_PACKAGES= [
    #"baltrad.bdbcommon",
    "jprops >= 2.0.2",
    "pyasn1",
    "pycryptodomex",
    "python-daemon >= 1.6",
    "werkzeug >= 1.0.1"
]

setuptools.setup(name="baltrad.exchange",
    version="0.1",
    namespace_packages=["baltrad"],
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
        "baltrad.exchange.auth": [
            "noauth = baltrad.exchange.auth:NoAuth",
            "tink = baltrad.exchange.auth.tinkauth:TinkAuth",
            "crypto = baltrad.exchange.auth.coreauth:CryptoAuth"
        ],
        "baltrad.exchange.client.commands": [
            "store = baltrad.exchange.client.cmd:StoreFile",
            "batchtest = baltrad.exchange.client.cmd:BatchTest",
            "create_keys = baltrad.exchange.client.cmd:CreateKeys"
        ],
        "console_scripts" : [
            "baltrad-exchange-server = baltrad.exchange.server_main:run",
            "baltrad-exchange-client = baltrad.exchange.client_main:run"
        ]
    },
    test_suite="nose.collector",
    tests_require=[
        "mock >= 0.7",
    ],
)
