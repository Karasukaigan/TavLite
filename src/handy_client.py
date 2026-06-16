import sys
from typing import Optional

import requests


class HandyClient:
    """Reusable client for The Handy HTTP API."""

    def __init__(
        self,
        api_key: str = "",
        api_version: str = "v2",
        base_url: Optional[str] = None,
        api_auth_key: str = "",
        access_token: str = "",
        min_speed: float = 10,
        max_speed: float = 80,
        min_depth: float = 0,
        max_depth: float = 100,
        travel_mm: float = 110.0,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key
        self.api_version = self._normalize_api_version(api_version)
        self._base_url_explicit = base_url is not None
        self.base_url = self._normalize_base_url(base_url or self._default_base_url(self.api_version))
        self.api_auth_key = api_auth_key
        self.access_token = access_token
        self.timeout = timeout
        self.session = session or requests.Session()

        self.min_user_speed = min_speed
        self.max_user_speed = max_speed
        self.min_handy_depth = min_depth
        self.max_handy_depth = max_depth
        self.FULL_TRAVEL_MM = travel_mm

        self.last_stroke_speed = 0
        self.last_depth_pos = 50
        self.last_relative_speed = 50
        self.last_mode = None

    def _normalize_api_version(self, api_version: str) -> str:
        version = str(api_version).strip().lower()
        if version in {"2", "v2", "handy_v2"}:
            return "v2"
        if version in {"3", "v3", "handy_v3"}:
            return "v3"
        raise ValueError("api_version must be 'v2' or 'v3'")

    def _default_base_url(self, api_version: str) -> str:
        if api_version == "v3":
            return "https://www.handyfeeling.com/api/handy-rest/v3/"
        return "https://www.handyfeeling.com/api/handy/v2/"

    def _normalize_base_url(self, base_url: str) -> str:
        return str(base_url).rstrip("/") + "/"

    def set_api_version(self, api_version: str, base_url: Optional[str] = None):
        """Switch between Handy API v2 and v3."""
        self.api_version = self._normalize_api_version(api_version)
        if base_url is not None:
            self.base_url = self._normalize_base_url(base_url)
            self._base_url_explicit = True
        elif not self._base_url_explicit:
            self.base_url = self._normalize_base_url(self._default_base_url(self.api_version))

    def set_api_auth(self, api_auth_key: str = "", access_token: str = ""):
        """Set optional v3 authentication credentials."""
        self.api_auth_key = api_auth_key
        self.access_token = access_token

    @property
    def is_connected(self) -> bool:
        return bool(self.api_key)

    def connect(self, api_key: Optional[str] = None, verify: bool = False) -> bool:
        """Store the connection key and optionally verify it against the API."""
        if api_key is not None:
            self.api_key = api_key
        if not self.api_key:
            return False
        if not verify:
            return True
        connected = self.get_connected()
        if not connected:
            return False
        info = self.get_info()
        if not info:
            return False
        fw_status = info.get("fwStatus")
        return fw_status in (0, "0")

    def disconnect(self):
        """Forget the key and stop the current motion."""
        try:
            if self.is_connected:
                self.stop()
        finally:
            self.api_key = ""

    def set_api_key(self, key: str):
        self.api_key = key

    def _auth_headers(self):
        headers = {}
        if self.api_version == "v3":
            if self.api_auth_key:
                headers["X-Api-Key"] = self.api_auth_key
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def get_connected(self):
        response = self._request("GET", "connected")
        if response is None:
            return None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                return bool(payload.get("connected"))
            return bool(payload)
        except ValueError as exc:
            print(f"[HANDY ERROR] Invalid connected payload: {exc}", file=sys.stderr)
            return None

    def get_info(self):
        response = self._request("GET", "info")
        if response is None:
            return None
        try:
            return response.json()
        except ValueError as exc:
            print(f"[HANDY ERROR] Invalid info payload: {exc}", file=sys.stderr)
            return None

    def get_mode(self):
        response = self._request("GET", "mode")
        if response is None:
            return None
        try:
            payload = response.json()
        except ValueError as exc:
            print(f"[HANDY ERROR] Invalid mode payload: {exc}", file=sys.stderr)
            return None
        mode = payload.get("mode")
        self.last_mode = mode
        return mode

    def get_status(self):
        """Return a version-aware status payload."""
        if self.api_version == "v2":
            response = self._request("GET", "status")
            if response is None:
                return None
            try:
                return response.json()
            except ValueError as exc:
                print(f"[HANDY ERROR] Invalid status payload: {exc}", file=sys.stderr)
                return None
        return {
            "connected": self.get_connected(),
            "info": self.get_info(),
            "mode": self.get_mode(),
        }

    def set_mode(self, mode):
        response = self._request("PUT", "mode", {"mode": int(mode)})
        if response is None:
            return False
        try:
            payload = response.json()
        except ValueError:
            self.last_mode = int(mode)
            return True
        if "mode" in payload:
            self.last_mode = payload.get("mode")
        else:
            self.last_mode = int(mode)
        return True

    def _ensure_mode(self, mode):
        current_mode = self.get_mode()
        if current_mode == mode:
            return True
        return self.set_mode(mode)

    def set_motion_limits(self, min_speed, max_speed, min_depth, max_depth):
        self.min_user_speed = min_speed
        self.max_user_speed = max_speed
        self.min_handy_depth = min_depth
        self.max_handy_depth = max_depth

    def update_settings(self, min_speed, max_speed, min_depth, max_depth):
        """Backward-compatible alias used by the app."""
        self.set_motion_limits(min_speed, max_speed, min_depth, max_depth)

    def _headers(self, include_json: bool = True):
        headers = {"X-Connection-Key": self.api_key}
        if include_json:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(self, method: str, path: str, body=None, params=None):
        if not self.api_key:
            return None
        url = f"{self.base_url}{path.lstrip('/')}"
        try:
            headers = self._headers(include_json=method.upper() != "GET")
            headers.update(self._auth_headers())
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as exc:
            print(f"[HANDY ERROR] Request failed for {path}: {exc}", file=sys.stderr)
            return None

    def _send_command(self, path, body=None):
        self._request("PUT", path, body or {})

    def issue_client_token(self, **params):
        """Issue a v3 client token using the authentication headers currently configured."""
        if self.api_version != "v3":
            raise RuntimeError("Client tokens are only available on Handy API v3")
        clean_params = {k: v for k, v in params.items() if v is not None}
        response = self._request("GET", "auth/token/issue", params=clean_params or None)
        if response is None:
            return None
        try:
            return response.json()
        except ValueError as exc:
            print(f"[HANDY ERROR] Invalid token payload: {exc}", file=sys.stderr)
            return None

    def _safe_percent(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(100.0, value))

    def percent_to_mm(self, value):
        return (float(value) / 100.0) * self.FULL_TRAVEL_MM

    def mm_to_percent(self, value):
        return int(round((float(value) / self.FULL_TRAVEL_MM) * 100))

    def move(self, speed, depth, stroke_range):
        """Move inside a calibrated range using percentage inputs."""
        if not self.api_key:
            return

        if speed is not None and speed == 0:
            self.stop()
            return

        if speed is None or depth is None or stroke_range is None:
            print("[HANDY] Incomplete move received, ignoring.", file=sys.stderr)
            return

        if not self._ensure_mode(0):
            return
        self._send_command("hamp/start")

        relative_pos_pct = self._safe_percent(depth)
        absolute_center_pct = self.min_handy_depth + (
            (self.max_handy_depth - self.min_handy_depth) * (relative_pos_pct / 100.0)
        )
        calibrated_range_width = self.max_handy_depth - self.min_handy_depth

        relative_range_pct = self._safe_percent(stroke_range)
        span_abs = (calibrated_range_width * (relative_range_pct / 100.0)) / 2.0

        min_zone_abs = absolute_center_pct - span_abs
        max_zone_abs = absolute_center_pct + span_abs

        clamped_min_zone = max(self.min_handy_depth, min_zone_abs)
        clamped_max_zone = min(self.max_handy_depth, max_zone_abs)

        slide_min = round(100 - clamped_max_zone)
        slide_max = round(100 - clamped_min_zone)

        if slide_min >= slide_max:
            slide_max = slide_min + 2

        slide_max = min(100, slide_max)
        slide_min = max(0, slide_min)

        self._send_command("slide", {"min": slide_min, "max": slide_max})

        relative_speed_pct = self._safe_percent(speed)
        speed_range_width = self.max_user_speed - self.min_user_speed
        final_physical_speed = self.min_user_speed + (speed_range_width * (relative_speed_pct / 100.0))
        final_physical_speed = int(round(final_physical_speed))

        self._send_command("hamp/velocity", {"velocity": final_physical_speed})

        self.last_stroke_speed = final_physical_speed
        self.last_relative_speed = relative_speed_pct
        self.last_depth_pos = int(round(relative_pos_pct))

    def move_to_position_mm(self, target_mm, velocity_mm_per_sec: float = 20.0, stop_on_target: bool = True):
        """Move the carriage to an absolute position in millimeters."""
        if not self.api_key:
            return

        target_mm = max(0.0, min(self.FULL_TRAVEL_MM, float(target_mm)))
        if not self._ensure_mode(2):
            return
        self._send_command(
            "hdsp/xava",
            {"position": target_mm, "velocity": float(velocity_mm_per_sec), "stopOnTarget": bool(stop_on_target)},
        )
        self.last_depth_pos = self.mm_to_percent(target_mm)

    def move_to_position_percent(self, target_percent, velocity_mm_per_sec: float = 20.0, stop_on_target: bool = True):
        """Move the carriage to an absolute position as a percentage."""
        self.move_to_position_mm(self.percent_to_mm(self._safe_percent(target_percent)), velocity_mm_per_sec, stop_on_target)

    def stop(self):
        """Stop the current motion."""
        if not self.api_key:
            return
        if not self._ensure_mode(0):
            return
        self._send_command("hamp/stop")
        self.last_stroke_speed = 0
        self.last_relative_speed = 0

    def nudge(self, direction, min_depth_pct=0, max_depth_pct=100, current_pos_mm=None, step_mm=2.0, velocity_mm_per_sec=20.0):
        """Move a small step within a bounded range."""
        min_mm = self.FULL_TRAVEL_MM * float(min_depth_pct) / 100.0
        max_mm = self.FULL_TRAVEL_MM * float(max_depth_pct) / 100.0

        if current_pos_mm is None:
            current_pos_mm = self.get_position_mm() or min_mm

        target_mm = float(current_pos_mm)
        if direction == "up":
            target_mm = min(target_mm + step_mm, max_mm)
        elif direction == "down":
            target_mm = max(target_mm - step_mm, min_mm)

        if not self._ensure_mode(2):
            return target_mm
        self._send_command(
            "hdsp/xava",
            {"position": target_mm, "velocity": float(velocity_mm_per_sec), "stopOnTarget": True},
        )
        self.last_depth_pos = self.mm_to_percent(target_mm)
        return target_mm

    def get_position_mm(self):
        if not self.api_key:
            return None
        response = self._request("GET", "slide/position/absolute")
        if response is None:
            return None
        try:
            data = response.json()
            return float(data.get("position", 0))
        except (ValueError, TypeError) as exc:
            print(f"[HANDY ERROR] Invalid position payload: {exc}", file=sys.stderr)
            return None

    def get_position_percent(self):
        position_mm = self.get_position_mm()
        if position_mm is None:
            return None
        return self.mm_to_percent(position_mm)
