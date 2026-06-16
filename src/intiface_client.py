"""Minimal Intiface Central client using only the Python standard library."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable
from urllib.parse import urlparse


class IntifaceClientError(RuntimeError):
    pass


class IntifaceTimeoutError(TimeoutError):
    pass


@dataclass(frozen=True)
class PositionFeature:
    device_index: int
    feature_index: int
    device_name: str = ""
    feature_name: str = ""
    step_count: int = 100


class IntifaceClient:
    def __init__(
        self,
        url: str = "ws://127.0.0.1:12345",
        client_name: str = "Python Intiface Client",
        message_version: int = 4,
        timeout: float = 5.0,
    ) -> None:
        self._url = urlparse(url)
        self._client_name = client_name
        self._message_version = message_version
        self._timeout = timeout
        self._socket: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._state_lock = threading.Condition()
        self._receiver_thread: threading.Thread | None = None
        self._running = False
        self._next_id = 1
        self._server_info: dict[str, Any] | None = None
        self._last_error: str | None = None
        self._devices: dict[int, dict[str, Any]] = {}

    @property
    def server_info(self) -> dict[str, Any] | None:
        return self._server_info

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def connect(self) -> None:
        if self._running:
            return

        host = self._url.hostname or "127.0.0.1"
        port = self._url.port or 12345
        self._socket = socket.create_connection((host, port), timeout=self._timeout)
        self._socket.settimeout(self._timeout)

        websocket_key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self._url.path or '/'} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {websocket_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("ascii")
        self._socket.sendall(request)
        response = self._read_http_response()
        accept = self._parse_websocket_accept(response)
        expected = base64.b64encode(
            hashlib.sha1(
                (websocket_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()
        ).decode("ascii")
        if accept != expected:
            raise IntifaceClientError("WebSocket handshake failed")

        self._running = True
        self._receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._receiver_thread.start()

        self._send_message(
            "RequestServerInfo",
            {"ClientName": self._client_name, "ProtocolVersionMajor": 4, "ProtocolVersionMinor": 0},
        )
        self._send_message("RequestDeviceList", {})
        self._wait_for(lambda: self._server_info is not None, timeout=self._timeout)

    def disconnect(self) -> None:
        if not self._running:
            return

        try:
            self.stop_all()
        except Exception:
            pass

        self._running = False
        socket_obj = self._socket
        self._socket = None
        if socket_obj is not None:
            try:
                self._send_close_frame(socket_obj)
            except Exception:
                pass
            try:
                socket_obj.close()
            except Exception:
                pass

        if self._receiver_thread is not None:
            self._receiver_thread.join(timeout=self._timeout)
            self._receiver_thread = None

    def start_scanning(self) -> None:
        self._send_message("StartScanning", {})

    def stop_scanning(self) -> None:
        self._send_message("StopScanning", {})

    def request_device_list(self) -> None:
        self._send_message("RequestDeviceList", {})

    def refresh_devices(self, timeout: float = 2.0, start_scan: bool = True) -> list[PositionFeature]:
        if start_scan:
            self.start_scanning()
        self.request_device_list()
        time.sleep(timeout)
        return self.find_position_devices()

    def find_position_devices(self) -> list[PositionFeature]:
        targets: list[PositionFeature] = []
        for device_index, device in sorted(self._devices.items()):
            device_name = str(device.get("DeviceName") or device.get("Name") or "")
            for feature in self._iter_position_features(device):
                targets.append(
                    PositionFeature(
                        device_index=device_index,
                        feature_index=feature["feature_index"],
                        device_name=device_name,
                        feature_name=feature.get("feature_name", ""),
                        step_count=feature["step_count"],
                    )
                )
        return targets

    def first_position_device(self) -> PositionFeature:
        devices = self.find_position_devices()
        if not devices:
            raise IntifaceClientError("No device supporting position movement was found")
        return devices[0]

    def send_position(self, target: PositionFeature, position: float, duration_ms: int = 500) -> None:
        if position < 0:
            position = 0
        elif position > 1:
            position = 1
        step_position = round(position * target.step_count)
        step_position = max(0, min(target.step_count, step_position))
        print(f"[send_position] pos_ratio={position:.2f} step_count={target.step_count} -> Value={step_position} Duration={max(1, int(duration_ms))}ms")

        self._send_message(
            "OutputCmd",
            {
                "DeviceIndex": target.device_index,
                "FeatureIndex": target.feature_index,
                "Command": {
                    "HwPositionWithDuration": {
                        "Value": step_position,
                        "Duration": max(1, int(duration_ms)),
                    }
                },
            },
        )

    def stop(self, target: PositionFeature | int | None = None) -> None:
        if target is None:
            self.stop_all()
            return

        device_index = target if isinstance(target, int) else target.device_index
        self._send_message("StopDeviceCmd", {"DeviceIndex": device_index})

    def stop_all(self) -> None:
        self._send_message("StopAllDevices", {})

    def _wait_for(self, predicate: Callable[[], bool], timeout: float) -> None:
        deadline = time.monotonic() + timeout
        with self._state_lock:
            while not predicate():
                if not self._running:
                    err = self._last_error
                    raise IntifaceClientError(f"Connection lost: {err}" if err else "Connection lost before response")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    err = self._last_error
                    msg = f"Timed out waiting for Intiface Central"
                    if err:
                        msg += f" (last error: {err})"
                    raise IntifaceTimeoutError(msg)
                self._state_lock.wait(timeout=remaining)

    def _receiver_loop(self) -> None:
        try:
            while self._running and self._socket is not None:
                frame = self._receive_frame(self._socket)
                if frame is None:
                    break
                if frame["opcode"] == 0x1:
                    text = frame["payload"].decode("utf-8", errors="replace")
                    self._handle_incoming_text(text)
                elif frame["opcode"] == 0x9:
                    self._send_pong(frame["payload"])
                elif frame["opcode"] == 0xA:
                    pass
                elif frame["opcode"] == 0x8:
                    break
        except Exception as exc:
            with self._state_lock:
                self._last_error = str(exc)
                self._state_lock.notify_all()
        finally:
            with self._state_lock:
                self._running = False
                self._state_lock.notify_all()

    def _send_pong(self, payload: bytes) -> None:
        if self._socket is None:
            return
        try:
            self._socket.sendall(self._make_masked_frame(0xA, payload))
        except Exception:
            pass

    def _handle_incoming_text(self, text: str) -> None:
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return

        messages: Iterable[Any]
        if isinstance(decoded, list):
            messages = decoded
        else:
            messages = [decoded]

        with self._state_lock:
            for message in messages:
                if not isinstance(message, dict):
                    continue
                self._update_state_from_message(message)
            self._state_lock.notify_all()

    def _update_state_from_message(self, message: dict[str, Any]) -> None:
        if "ServerInfo" in message:
            self._server_info = message["ServerInfo"]
            return

        if "Error" in message:
            error = message["Error"]
            if isinstance(error, dict):
                self._last_error = str(error.get("Error") or error.get("error") or error)
            else:
                self._last_error = str(error)
            return

        if "DeviceRemoved" in message:
            payload = message["DeviceRemoved"]
            if isinstance(payload, dict) and "DeviceIndex" in payload:
                self._devices.pop(int(payload["DeviceIndex"]), None)
            return

        if "DeviceList" in message or "DeviceAdded" in message:
            payload = message.get("DeviceList") or message.get("DeviceAdded")
            self._merge_devices(payload)

    def _merge_devices(self, payload: Any) -> None:
        if isinstance(payload, dict):
            if "Devices" in payload:
                devices = payload["Devices"]
                if isinstance(devices, dict):
                    for key, device in devices.items():
                        if isinstance(device, dict):
                            index = int(device.get("DeviceIndex", key))
                            self._devices[index] = device
                elif isinstance(devices, list):
                    for device in devices:
                        if isinstance(device, dict) and "DeviceIndex" in device:
                            self._devices[int(device["DeviceIndex"])] = device
            elif "DeviceIndex" in payload:
                self._devices[int(payload["DeviceIndex"])] = payload

        for nested in self._iter_dicts(payload):
            if "DeviceIndex" in nested and ("FeatureIndex" in nested or "Features" in nested):
                self._devices[int(nested["DeviceIndex"])] = nested

    def _iter_position_features(self, device: dict[str, Any]) -> list[dict[str, Any]]:
        features: list[dict[str, Any]] = []
        for candidate in self._iter_dicts(device):
            if "FeatureIndex" not in candidate:
                continue
            if not self._looks_like_position_feature(candidate):
                continue
            features.append(
                {
                    "feature_index": int(candidate["FeatureIndex"]),
                    "feature_name": str(candidate.get("FeatureDescriptor") or candidate.get("Description") or ""),
                    "step_count": self._extract_step_count(candidate),
                }
            )
        unique: list[dict[str, Any]] = []
        seen: set[tuple[int, str]] = set()
        for feature in features:
            key = (feature["feature_index"], feature["feature_name"])
            if key in seen:
                continue
            seen.add(key)
            unique.append(feature)
        return unique

    def _looks_like_position_feature(self, candidate: dict[str, Any]) -> bool:
        haystack = json.dumps(candidate, separators=(",", ":"), ensure_ascii=False)
        markers = (
            "PositionWithDuration",
            "LinearCmd",
            "Linear",
            "Position",
        )
        if any(marker in haystack for marker in markers):
            return True
        output_type = candidate.get("OutputType") or candidate.get("ActuatorType") or candidate.get("Type")
        return str(output_type) in {"Position", "PositionWithDuration", "Linear"}

    def _extract_step_count(self, candidate: dict[str, Any]) -> int:
        direct = candidate.get("StepCount")
        if isinstance(direct, int) and direct > 0:
            return direct
        if isinstance(direct, list) and direct:
            ints = [int(value) for value in direct if isinstance(value, (int, float))]
            if ints:
                return max(ints)

        value = candidate.get("Value")
        if isinstance(value, list) and len(value) == 2 and all(isinstance(v, (int, float)) for v in value):
            low, high = int(value[0]), int(value[1])
            return max(1, abs(high - low))

        for nested in self._iter_dicts(candidate):
            if nested is candidate:
                continue
            step_count = self._extract_step_count(nested)
            if step_count != 100:
                return step_count
        return 100

    def _iter_dicts(self, value: Any) -> Iterable[dict[str, Any]]:
        if isinstance(value, dict):
            yield value
            for nested in value.values():
                yield from self._iter_dicts(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from self._iter_dicts(nested)

    def _send_message(self, name: str, body: dict[str, Any]) -> None:
        if not self._running or self._socket is None:
            raise IntifaceClientError("Client is not connected")

        message = {name: {"Id": self._next_id, **body}}
        self._next_id += 1
        payload = json.dumps([message]).encode("utf-8")

        with self._send_lock:
            self._socket.sendall(self._make_text_frame(payload))

    def _make_text_frame(self, payload: bytes) -> bytes:
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))

        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return bytes(header) + masked

    def _send_close_frame(self, sock: socket.socket) -> None:
        sock.sendall(self._make_masked_frame(0x8, b""))

    def _make_masked_frame(self, opcode: int, payload: bytes) -> bytes:
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return bytes(header) + masked

    def _read_http_response(self) -> bytes:
        assert self._socket is not None
        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = self._socket.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
        return bytes(response)

    def _parse_websocket_accept(self, response: bytes) -> str:
        header, _, _ = response.partition(b"\r\n\r\n")
        lines = header.split(b"\r\n")
        status = lines[0].decode("ascii", errors="ignore")
        if "101" not in status:
            raise IntifaceClientError(f"WebSocket upgrade failed: {status}")
        for line in lines[1:]:
            if line.lower().startswith(b"sec-websocket-accept:"):
                return line.split(b":", 1)[1].strip().decode("ascii")
        raise IntifaceClientError("WebSocket accept header missing")

    def _receive_frame(self, sock: socket.socket) -> dict[str, Any] | None:
        first_two = self._recv_exact(sock, 2)
        if not first_two:
            return None

        fin = bool(first_two[0] & 0x80)
        opcode = first_two[0] & 0x0F
        masked = bool(first_two[1] & 0x80)
        length = first_two[1] & 0x7F

        if length == 126:
            length = struct.unpack("!H", self._recv_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(sock, 8))[0]

        mask = self._recv_exact(sock, 4) if masked else b""
        payload = self._recv_exact(sock, length) if length else b""
        if masked and mask:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))

        if not fin:
            raise IntifaceClientError("Fragmented WebSocket frames are not supported")

        return {"opcode": opcode, "payload": payload}

    def _recv_exact(self, sock: socket.socket, size: int) -> bytes:
        buffer = bytearray()
        while len(buffer) < size:
            chunk = sock.recv(size - len(buffer))
            if not chunk:
                raise ConnectionError("WebSocket connection closed")
            buffer.extend(chunk)
        return bytes(buffer)


__all__ = ["IntifaceClient", "IntifaceClientError", "IntifaceTimeoutError", "PositionFeature"]

