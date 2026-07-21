"""
ipc_socket.py - Local IPC Layer for Clew V5 Architecture
Provides a high-speed Unix Domain Socket or TCP localhost fallback interface
for external tools, UI clients, and voice workers to inspect and mutate state.
"""

import os
import sys
import json
import socket
import asyncio
from typing import Optional, Dict, Any

from version_engine import VersionEngine
from reconciliation import ReconciliationEngine
from watchdog import StateWatchdog
from merkle_dag import serialize_graph_crdt

class ClewIPCServer:
    """
    Asynchronous IPC server for dispatching JSON commands to Clew engines.
    """

    def __init__(
        self,
        version_engine: VersionEngine,
        reconciliation_engine: Optional[ReconciliationEngine] = None,
        watchdog: Optional[StateWatchdog] = None,
        socket_path: str = "/tmp/clew_ipc.sock",
        host: str = "127.0.0.1",
        port: int = 9876
    ):
        self.version_engine = version_engine
        self.reconciliation_engine = reconciliation_engine
        self.watchdog = watchdog
        self.socket_path = socket_path
        self.host = host
        self.port = port
        self.server: Optional[asyncio.AbstractServer] = None

    async def start_async(self):
        """Starts the IPC server listening on either Unix Domain Socket or TCP fallback."""
        use_unix = hasattr(socket, "AF_UNIX") and sys.platform != "win32"
        if use_unix:
            # Ensure path directory exists
            dir_name = os.path.dirname(self.socket_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            # Remove old socket file if exists
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass
            self.server = await asyncio.start_unix_server(self._handle_client, path=self.socket_path)
        else:
            self.server = await asyncio.start_server(self._handle_client, host=self.host, port=self.port)

    async def stop(self):
        """Stops the IPC server and cleans up resources."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

        # Clean up UDS file if applicable
        use_unix = hasattr(socket, "AF_UNIX") and sys.platform != "win32"
        if use_unix and os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handles single incoming socket connection and reads newline-terminated messages."""
        try:
            while True:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break
                line_str = line_bytes.decode("utf-8").strip()
                if not line_str:
                    continue

                try:
                    request = json.loads(line_str)
                except Exception as e:
                    response = {"status": "error", "error": f"Invalid JSON payload: {str(e)}"}
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()
                    continue

                command = request.get("command")
                response = await self._dispatch_command(command, request)
                writer.write((json.dumps(response) + "\n").encode("utf-8"))
                await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch_command(self, command: Optional[str], request: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches command string to appropriate engine and formats response."""
        if not command:
            return {"status": "error", "error": "Missing command field"}

        if command == "COMMIT":
            message = request.get("message", "IPC Commit")
            try:
                commit = self.version_engine.commit(message=message)
                return {
                    "status": "success",
                    "data": {
                        "commit_hash": commit.commit_hash,
                        "state_root_hash": commit.state_root_hash
                    }
                }
            except Exception as e:
                return {"status": "error", "error": f"Commit failed: {str(e)}"}

        elif command == "CHECKOUT":
            commit_hash = request.get("commit_hash")
            if not commit_hash:
                return {"status": "error", "error": "Missing commit_hash parameter"}
            try:
                success = self.version_engine.checkout(commit_hash=commit_hash)
                if success:
                    return {
                        "status": "success",
                        "data": {
                            "commit_hash": commit_hash
                        }
                    }
                else:
                    return {"status": "error", "error": "Checkout failed"}
            except Exception as e:
                return {"status": "error", "error": f"Checkout failed: {str(e)}"}

        elif command == "RECONCILE":
            if not self.reconciliation_engine:
                return {"status": "error", "error": "Reconciliation engine not configured"}
            try:
                resolved_count = await self.reconciliation_engine.reconcile_divergences()
                return {
                    "status": "success",
                    "data": {
                        "resolved_count": resolved_count
                    }
                }
            except Exception as e:
                return {"status": "error", "error": f"Reconciliation failed: {str(e)}"}

        elif command == "HEALTH_CHECK":
            if not self.watchdog:
                return {"status": "error", "error": "State watchdog not configured"}
            try:
                is_valid, status_message = self.watchdog.verify_state_integrity()
                drift_detected = self.watchdog.detect_drift()
                return {
                    "status": "success",
                    "data": {
                        "is_valid": is_valid,
                        "status_message": status_message,
                        "drift_detected": drift_detected
                    }
                }
            except Exception as e:
                return {"status": "error", "error": f"Health check failed: {str(e)}"}

        elif command == "INSPECT_STATE":
            try:
                state_data = serialize_graph_crdt(self.version_engine.crdt)
                return {
                    "status": "success",
                    "data": state_data
                }
            except Exception as e:
                return {"status": "error", "error": f"State inspection failed: {str(e)}"}

        else:
            return {"status": "error", "error": f"Unknown command: {command}"}

class ClewIPCClient:
    """
    Client for interacting with the ClewIPCServer over UDS or TCP.
    """

    def __init__(self, socket_path: str = "/tmp/clew_ipc.sock", host: str = "127.0.0.1", port: int = 9876):
        self.socket_path = socket_path
        self.host = host
        self.port = port

    async def send_command(self, command: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Connects, sends a single JSON command, and parses the response."""
        payload_data = payload or {}
        request_obj = {"command": command, **payload_data}
        request_str = json.dumps(request_obj) + "\n"

        use_unix = hasattr(socket, "AF_UNIX") and sys.platform != "win32"
        if use_unix:
            reader, writer = await asyncio.open_unix_connection(path=self.socket_path)
        else:
            reader, writer = await asyncio.open_connection(host=self.host, port=self.port)

        try:
            writer.write(request_str.encode("utf-8"))
            await writer.drain()

            response_bytes = await reader.readline()
            response_str = response_bytes.decode("utf-8").strip()
            if not response_str:
                return {"status": "error", "error": "Empty response from server"}
            return json.loads(response_str)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
