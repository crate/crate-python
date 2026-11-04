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

import os
import re
import socket
import time
from io import BytesIO
from pathlib import Path

import pytest

import crate.testing.layer
from crate.client import connect
from crate.testing.layer import (
    CrateLayer,
    http_url_from_host_port,
    prepend_http,
    wait_for_http_url,
)
from tests.client.settings import crate_path
from tests.conftest import download_cratedb, get_crate_url

HTTP_LOG_LINE = (
    b"[i.c.p.h.CrateNettyHttpServerTransport] [crate] "
    b"publish_address {127.0.0.1:4200}"
)


def free_port() -> int:
    """
    Returns a port the OS considers free
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until(predicate, timeout=30, interval=0.5) -> bool:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            return False
        time.sleep(interval)
    return True


def query(layer, stmt):
    with connect(layer.crate_servers) as conn:
        cursor = conn.cursor()
        cursor.execute(stmt)
        return cursor.fetchall()


def fake_crate(tmp_path: Path, script: str) -> str:
    """
    Returns a stand-in for `bin/crate`
    """
    path = tmp_path / "fake-crate"
    path.write_text("#!/bin/sh\n" + script)
    path.chmod(0o755)
    return str(path)


@pytest.mark.parametrize(
    "host, expected",
    [
        ("localhost", "http://localhost"),
        ("http://localhost", "http://localhost"),
        ("https://localhost", "https://localhost"),
        ("http", "http://http"),
    ],
)
def test_prepend_http(host, expected):
    assert prepend_http(host) == expected


@pytest.mark.parametrize(
    "host, port, expected",
    [
        (None, None, None),
        ("localhost", None, None),
        (None, 4200, None),
        ("localhost", 4200, "http://localhost:4200"),
        ("localhost", "4200", "http://localhost:4200"),
        ("https://crate", 4200, "https://crate:4200"),
        ("localhost", "4200-4299", None),
    ],
)
def test_http_url_from_host_port(host, port, expected):
    assert http_url_from_host_port(host, port) == expected


@pytest.mark.parametrize(
    "log, expected",
    [
        (HTTP_LOG_LINE, "http://127.0.0.1:4200"),
        (b"starting\n" + HTTP_LOG_LINE, "http://127.0.0.1:4200"),
        (b"[i.c.p.h.CrateNettyHttpServerTransport] publish_address {}", None),
        (b"", None),
    ],
)
def test_wait_for_http_url(log, expected):
    assert wait_for_http_url(BytesIO(log), timeout=1) == expected


def test_wait_for_http_url_verbose(capsys):
    wait_for_http_url(BytesIO(b"starting\n"), timeout=1, verbose=True)
    assert "starting" in capsys.readouterr().err


def test_default_settings(tmp_path):
    layer = CrateLayer("crate", crate_home=str(tmp_path))
    assert layer.start_cmd[0] == str(tmp_path / "bin" / "crate")
    for flag in [
        "-Chttp.port=4200-4299",
        "-Ctransport.tcp.port=4300-4399",
        "-Cnetwork.host=127.0.0.1",
        "-Cnode.name=crate",
        "-Ccluster.name=TestingDynamic",
        "-Cpath.conf={}".format(tmp_path / "config"),
    ]:
        assert flag in layer.start_cmd
    assert layer.crate_servers == []
    assert layer.wdPath().endswith(os.path.join("crate_layer", "crate"))


def test_static_ports(tmp_path):
    layer = CrateLayer(
        "crate",
        crate_home=str(tmp_path),
        port=44219,
        transport_port=44319,
        cluster_name="my_cluster",
    )
    assert layer.crate_servers == ["http://127.0.0.1:44219"]
    for flag in [
        "-Chttp.port=44219",
        "-Ctransport.tcp.port=44319",
        "-Ccluster.name=my_cluster",
    ]:
        assert flag in layer.start_cmd


def test_additional_settings(tmp_path):
    """
    Additional settings are handed over to CrateDB using ``-C`` flags, and
    take precedence over keyword arguments.
    """
    layer = CrateLayer(
        "custom",
        str(tmp_path),
        port=44401,
        settings={
            "cluster.graceful_stop.min_availability": "none",
            "http.port": 44402,
            "lang.js.enabled": True,
        },
    )
    assert layer.crate_servers == ["http://127.0.0.1:44402"]
    for flag in [
        "-Ccluster.graceful_stop.min_availability=none",
        "-Chttp.port=44402",
        "-Clang.js.enabled=true",
    ]:
        assert flag in layer.start_cmd


def test_crate_config_directory(tmp_path):
    config_dir = tmp_path / "conf"
    config_dir.mkdir()
    layer = CrateLayer("crate", str(tmp_path), crate_config=str(config_dir))
    assert "-Cpath.conf={}".format(config_dir) in layer.start_cmd


def test_crate_config_file(tmp_path):
    config = tmp_path / "conf" / "crate.yml"
    config.parent.mkdir()
    config.touch()
    layer = CrateLayer("crate", str(tmp_path), crate_config=str(config))
    assert "-Cpath.conf={}".format(config.parent) in layer.start_cmd


def test_crate_config_must_be_named_crate_yml(tmp_path):
    config = tmp_path / "other.yml"
    config.touch()
    with pytest.raises(ValueError, match="crate.yml"):
        CrateLayer("crate", str(tmp_path), crate_config=str(config))


def test_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("JAVA_HOME", "/opt/jdk")
    layer = CrateLayer("crate", str(tmp_path), env={"CRATE_HEAP_SIZE": "300m"})
    assert layer.env == {
        "CRATE_HEAP_SIZE": "300m",
        "CRATE_USE_IPV4": "true",
        "JAVA_HOME": "/opt/jdk",
    }


@pytest.mark.parametrize(
    "java_home, env, expected",
    [
        # JAVA_HOME must not be set to `None`: It would be literally
        # interpreted as a string 'None', which is an invalid path.
        (None, None, ""),
        ("/opt/jdk-11", None, "/opt/jdk-11"),
        ("/opt/jdk-11", {"JAVA_HOME": "/opt/jdk-12"}, "/opt/jdk-12"),
    ],
)
def test_java_home(tmp_path, monkeypatch, java_home, env, expected):
    if java_home is None:
        monkeypatch.delenv("JAVA_HOME", raising=False)
    else:
        monkeypatch.setenv("JAVA_HOME", java_home)
    layer = CrateLayer("crate", str(tmp_path), env=env)
    assert layer.env["JAVA_HOME"] == expected


def test_layer_from_uri(tmp_path, monkeypatch):
    """
    The layer can also be created from a URI pointing to a CrateDB tarball.
    """
    monkeypatch.setattr(
        crate.testing.layer,
        "_download_and_extract",
        lambda uri, directory: None,
    )
    layer = CrateLayer.from_uri(
        get_crate_url(),
        name="crate-by-uri",
        http_port=42203,
        directory=str(tmp_path),
    )
    assert layer.crate_servers == ["http://127.0.0.1:42203"]


def test_start_fails_when_process_exits(tmp_path):
    exe = fake_crate(tmp_path, "echo starting\nsleep 1\n")
    layer = CrateLayer("crate", str(tmp_path), crate_exec=exe)
    with pytest.raises(SystemError, match="HTTP address not found"):
        layer.start()
    assert layer.process is None


def test_start_fails_after_timeout(tmp_path):
    exe = fake_crate(tmp_path, "while true; do echo waiting; sleep 0.1; done\n")
    layer = CrateLayer("crate", str(tmp_path), crate_exec=exe)
    layer.startup_timeout = 1
    with pytest.raises(SystemError, match="within 1s"):
        layer.start()
    assert layer.process is None


def test_stop_without_start(tmp_path):
    CrateLayer("crate", str(tmp_path)).stop()


@pytest.fixture(scope="module")
def crate_home():
    download_cratedb(Path(crate_path()))
    return crate_path()


@pytest.fixture
def start_layer(crate_home, tmp_path, monkeypatch):
    """
    Starts CrateDB layers, which are stopped after the test, also on failure.
    """
    monkeypatch.setattr(CrateLayer, "tmpdir", str(tmp_path))
    layers = []

    def start(name="crate", **kwargs):
        layer = CrateLayer(name, crate_home=crate_home, **kwargs)
        layer.start()
        layers.append(layer)
        return layer

    yield start
    for layer in layers:
        layer.stop()


def test_start_and_stop(crate_home, tmp_path, monkeypatch):
    """
    The layer starts CrateDB on the first free port of the default range,
    reads the chosen address from the startup logs, and stops it again.
    """
    monkeypatch.setattr(CrateLayer, "tmpdir", str(tmp_path))
    with CrateLayer("crate", crate_home=crate_home) as layer:
        assert re.match(r"http://127.0.0.1:42\d\d$", layer.crate_servers[0])
        result = query(layer, "select name from sys.cluster")
        assert result == [["TestingDynamic"]]
        process = layer.process

    assert layer.process is None
    assert process.poll() is not None
    assert not os.path.exists(layer.wdPath())


def test_static_ports_and_environment(start_layer):
    port = free_port()
    layer = start_layer(
        port=port,
        transport_port=free_port(),
        env={"CRATE_HEAP_SIZE": "300m"},
    )
    assert layer.crate_servers == ["http://127.0.0.1:{}".format(port)]
    result = query(layer, "select heap['max'] from sys.nodes")
    assert result == [[314572800]]


def test_cluster(start_layer):
    """
    Layers with the same cluster name find each other and form a cluster.
    """
    layer1 = start_layer("crate1", host="_local_", cluster_name="my_cluster")
    start_layer(
        "crate2",
        host="_local_",
        cluster_name="my_cluster",
        settings={"discovery.initial_state_timeout": "10s"},
    )
    assert wait_until(
        lambda: query(layer1, "select count(*) from sys.nodes") == [[2]]
    )
