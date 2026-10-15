# -*- coding: utf-8; -*-
#
# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.

import logging

import pytest

from crate.client import exceptions
from crate.client._pool import _ServerPool
from crate.client.http import Client

NODE1 = "http://localhost:4200"
NODE2 = "http://localhost:4201"
NODE3 = "http://localhost:4202"


class FakeClock:
    def __init__(self, now: float = 1_700_000_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


def test_round_robin(clock):
    pool = _ServerPool([NODE1, NODE2, NODE3], clock=clock)
    picked = [pool._get_server() for _ in range(4)]
    assert picked == [NODE1, NODE2, NODE3, NODE1]


def test_active_servers_is_a_copy(clock):
    pool = _ServerPool([NODE1, NODE2], clock=clock)
    active = pool.active_servers
    active.clear()
    assert pool.active_servers == [NODE1, NODE2]


def test_drop_server(clock):
    pool = _ServerPool([NODE1, NODE2], clock=clock)
    pool._drop_server(NODE1, "Connection refused")
    assert pool.active_servers == [NODE2]
    assert pool._inactive_servers == [(clock.now, NODE1, "Connection refused")]
    assert [pool._get_server() for _ in range(2)] == [NODE2, NODE2]


def test_drop_unknown_server_is_ignored(clock):
    pool = _ServerPool([NODE1, NODE2], clock=clock)
    pool._drop_server(NODE3, "Connection refused")
    assert pool.active_servers == [NODE1, NODE2]
    assert pool._inactive_servers == []


def test_drop_last_server_raises(clock):
    pool = _ServerPool([NODE1, NODE2], clock=clock)
    pool._drop_server(NODE1, "Connection refused")
    with pytest.raises(
        exceptions.ConnectionError,
        match="No more Servers available, exception from last server: "
        "Read timed out",
    ):
        pool._drop_server(NODE2, "Read timed out")
    assert pool.active_servers == []


def test_server_restored_after_retry_interval(clock):
    pool = _ServerPool([NODE1, NODE2], clock=clock)
    pool.retry_interval = 5
    pool._drop_server(NODE1, "Connection refused")

    clock.now += 4
    pool._get_server()
    assert pool.active_servers == [NODE2]

    clock.now += 1
    assert pool._get_server() == NODE2
    assert pool.active_servers == [NODE1, NODE2]
    assert pool._inactive_servers == []


def test_retry_interval_class_default(clock):
    pool = _ServerPool([NODE1, NODE2], clock=clock)
    pool._drop_server(NODE1, "Connection refused")

    clock.now += 29
    pool._get_server()
    assert pool.active_servers == [NODE2]

    clock.now += 1
    pool._get_server()
    assert sorted(pool.active_servers) == [NODE1, NODE2]


def test_oldest_server_restored_when_none_is_active(clock):
    pool = _ServerPool([NODE1, NODE2, NODE3], clock=clock)
    pool._drop_server(NODE2, "Connection refused")
    clock.now += 1
    pool._drop_server(NODE1, "Connection refused")
    pool._active_servers = []

    assert pool._get_server() == NODE2
    assert pool.active_servers == [NODE2]
    assert pool._inactive_servers == [(clock.now, NODE1, "Connection refused")]


def test_pool_logs_on_subclass_logger(clock, caplog):
    class Pool(_ServerPool):
        _logger = logging.getLogger("crate.client.test")

    pool = Pool([NODE1, NODE2], clock=clock)
    pool.retry_interval = 5
    with caplog.at_level(logging.WARNING):
        pool._drop_server(NODE1, "Connection refused")
        clock.now += 5
        pool._get_server()
    assert [(r.name, r.getMessage()) for r in caplog.records] == [
        ("crate.client.test", f"Removed server {NODE1} from active pool"),
        ("crate.client.test", f"Restored server {NODE1} into active pool"),
    ]


def test_client_logs_on_http_logger(caplog):
    client = Client(servers=[NODE1, NODE2])
    with caplog.at_level(logging.WARNING):
        client._drop_server(NODE1, "Connection refused")
    assert [r.name for r in caplog.records] == ["crate.client.http"]
