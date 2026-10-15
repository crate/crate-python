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

import heapq
import logging
import threading
import time
import typing as t

from crate.client.exceptions import ConnectionError


class _ServerPool:
    """
    Round-robin server selection. A dropped server is taken out of rotation
    for `retry_interval` seconds.

    Subclasses set `_logger` to log server changes on their own logger.
    """

    retry_interval = 30
    """Retry interval for failed servers in seconds."""

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        servers: t.List[str],
        clock: t.Callable[[], float] = time.time,
    ) -> None:
        self._active_servers = servers
        self._inactive_servers: t.List[t.Tuple[float, str, str]] = []
        self._lock = threading.RLock()
        self._clock = clock

    def _get_server(self) -> str:
        """
        Get server to use for request.
        Also process inactive server list, re-add them after given interval.
        """
        with self._lock:
            inactive_server_count = len(self._inactive_servers)
            for _ in range(inactive_server_count):
                try:
                    ts, server, message = heapq.heappop(self._inactive_servers)
                except IndexError:
                    pass
                else:
                    if (ts + self.retry_interval) > self._clock():
                        # Not yet, put it back
                        heapq.heappush(
                            self._inactive_servers, (ts, server, message)
                        )
                    else:
                        self._active_servers.append(server)
                        self._logger.warning(
                            "Restored server %s into active pool", server
                        )

            # if none is old enough, use oldest
            if not self._active_servers:
                ts, server, message = heapq.heappop(self._inactive_servers)
                self._active_servers.append(server)
                self._logger.info("Restored server %s into active pool", server)

            server = self._active_servers[0]
            self._roundrobin()

            return server

    @property
    def active_servers(self) -> t.List[str]:
        """get the active servers for this client"""
        with self._lock:
            return list(self._active_servers)

    def _drop_server(self, server: str, message: str) -> None:
        """
        Drop server from active list and adds it to the inactive ones.
        """
        try:
            self._active_servers.remove(server)
        except ValueError:
            pass
        else:
            heapq.heappush(
                self._inactive_servers, (self._clock(), server, message)
            )
            self._logger.warning("Removed server %s from active pool", server)

        # if this is the last server raise exception, otherwise try next
        if not self._active_servers:
            raise ConnectionError(
                ("No more Servers available, exception from last server: %s")
                % message
            )

    def _roundrobin(self) -> None:
        """
        Very simple round-robin implementation
        """
        self._active_servers.append(self._active_servers.pop(0))
