# ./src/player.py
import threading
import time
import socket
import serial
from typing import List, Dict, Any

class Player:
    def __init__(self):
        self.funscript = {
            "actions": [{"at": 0, "pos": 50}, {"at": 100, "pos": 50}],
            "inverted": False,
            "range": 100
        }
        self.udp_url = None  # UDP address
        self.serial_device = None  # Serial port
        self.current_mode = "serial"  # serial | udp
        self.is_playing = False  # Whether currently playing
        self.serial_conn = None  # Serial connection object
        self.stop_event = threading.Event()
        self.offset_value = 0  # Offset in milliseconds

        self.max = 100  # Maximum position
        self.min = 0  # Minimum position
        self.freq = 1.0  # Frequency
        self.decline_ratio = 0.5  # Decline interval ratio

        self.now_pos = self.max  # Current position

    def load_script(self, script_data: dict):
        """Load script"""
        if "actions" not in script_data:
            raise ValueError("Missing required field: actions")
        actions = script_data["actions"]
        if not actions:
            raise ValueError("Actions list cannot be empty")
        range_limit = script_data.get("range", 100)
        inverted = script_data.get("inverted", False)
        processed_actions = [
            {
                "at": action["at"],
                "pos": 100 - min(action.get("pos", 50), range_limit) if inverted else min(action.get("pos", 50), range_limit)
            }
            for action in actions
        ]
        sorted_actions = sorted(processed_actions, key=lambda x: x["at"])
        self.funscript = {
            "actions": sorted_actions,
            "inverted": inverted,
            "range": range_limit
        }
        # return {"message": "Script loaded successfully", "data": self.funscript}
        return {"message": "Script loaded successfully"}

    def play(self, start_time_ms=0, use_offset=True):
        """Start playing"""
        if not self.funscript:
            raise ValueError("No script loaded")
        if self.current_mode == "udp" and not self.udp_url:
            raise ValueError("UDP address not set")
        elif self.current_mode == "serial" and not self.serial_device:
            raise ValueError("Serial device not set")

        # Stop current playback
        if self.is_playing:
            self.stop_event.set()
            self.is_playing = False

        # Start new playback
        self.stop_event.clear()
        self.is_playing = True
        adjusted_at = max(0, start_time_ms)
        if use_offset:
            adjusted_at += self.offset_value
        
        playback_thread = threading.Thread(target=self._play_script, args=(adjusted_at,), daemon=True)
        playback_thread.start()
        
        return {
            "message": f"Script playing started from {adjusted_at}ms (original: {start_time_ms}ms, offset: {self.offset_value}ms)",
            "mode": self.current_mode,
            "started_at": adjusted_at
        }

    def stop(self):
        """Stop playing"""
        if self.is_playing:
            self.stop_event.set()
            self.is_playing = False
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
                self.serial_conn = None
            return {"message": "Script playing stopped"}
        return {"message": "No script is currently playing"}

    def _play_script(self, start_time_ms: int):
        """Play script in background thread"""
        try:
            actions = self.funscript["actions"]
            filtered_actions = [action for action in actions if action["at"] >= start_time_ms]
            if not filtered_actions:
                self.is_playing = False
                return

            start_timestamp = time.perf_counter() * 1000 - start_time_ms

            # Initialize sender
            if self.current_mode == "udp":
                host, port = (self.udp_url.split(":")[0], int(self.udp_url.split(":")[1])) if ":" in self.udp_url else (self.udp_url, 8000)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                sender = lambda data: sock.sendto(data.encode('utf-8'), (host, port))
            elif self.current_mode == "serial":
                # Reuse existing connection or create new connection
                if not self.serial_conn or not self.serial_conn.is_open:
                    self.serial_conn = serial.Serial(self.serial_device, 115200, timeout=1)
                sender = lambda data: self.serial_conn.write(data.encode('utf-8'))

            if len(filtered_actions) == 1:
                self.now_pos = filtered_actions[0]["pos"]
                sender(f"L0{self.now_pos}\n")
            else:
                for action in filtered_actions:
                    if self.stop_event.is_set():
                        break

                    # Dynamically calculate target time
                    target_time_ms = action["at"]
                    current_time_ms = (time.perf_counter() * 1000) - start_timestamp
                    wait_time_ms = target_time_ms - current_time_ms
                    wait_time = wait_time_ms / 1000.0

                    # Send T-code command
                    if wait_time > 0:
                        self.now_pos = self._scale_value(action['pos'])
                        tcode = f"L0{self.now_pos}I{int(wait_time_ms)}\n"
                    else:
                        continue
                    # print(tcode)
                    try:
                        sender(tcode)
                    except Exception as e:
                        pass
                    
                    # Segment waiting to improve responsiveness
                    while wait_time > 0:
                        if self.stop_event.is_set():
                            break
                        sleep_time = min(0.001, wait_time)  # Wait at most 1ms
                        time.sleep(sleep_time)
                        current_time_ms = (time.perf_counter() * 1000) - start_timestamp
                        wait_time = (target_time_ms - current_time_ms) / 1000.0

                    if self.stop_event.is_set():
                        break
                
            # Close resources
            if self.current_mode == "udp":
                sock.close()      
        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            # Clean up resources
            if self.current_mode == "serial" and self.serial_conn:
                try:
                    if self.serial_conn.is_open:
                        self.serial_conn.close()
                except Exception as e:
                    print(f"Failed to close serial connection: {e}")
                finally:
                    self.serial_conn = None
            self.is_playing = False

    def _scale_value(self, v, i_min=0, i_max=100, o_min=0, o_max=9999):
        if i_min >= i_max or o_min >= o_max:
            raise ValueError("Invalid range")
        return round((max(i_min, min(v, i_max)) - i_min) * (o_max - o_min) / (i_max - i_min) + o_min)
    
    def check_actions(self, data_list: List[Dict[str, Any]]) -> bool:
        """Check if actions conform to format requirements"""
        if not isinstance(data_list, list):
            return False
        for item in data_list:
            if not isinstance(item, dict):
                return False
            keys = set(item.keys())
            required_keys = {'at', 'pos'}
            if keys != required_keys:
                return False
        return True

    def generate_actions(self, max_pos=100, min_pos=0, freq=1, decline_ratio=0.5, start_pos=None, loop_count=100, custom_actions=None):
        """Generate actions"""
        if custom_actions:
            if not self.check_actions(custom_actions):
                raise ValueError("Invalid custom_actions format")
            if loop_count <= 1 or len(custom_actions) < 3:
                return custom_actions
            sorted_actions = sorted(custom_actions, key=lambda x: x.get('at', 0))
            start_action = sorted_actions[0]
            aligned_actions = []
            for action in sorted_actions:
                new_action = action.copy()
                new_action['at'] = action['at'] - start_action['at']
                aligned_actions.append(new_action)
            actions = []
            last_at = aligned_actions[-1]['at']
            actions.extend(aligned_actions.copy())
            for i in range(1, loop_count):
                time_offset = i * last_at
                for j in range(1, len(aligned_actions)):
                    frame = aligned_actions[j]
                    new_frame = {
                        'at': frame['at'] + time_offset,
                        'pos': frame['pos']
                    }
                    actions.append(new_frame)
        else:
            max_pos = int(min(100, max(0, max_pos)))
            min_pos = int(min(100, max(0, min_pos)))
            if min_pos > max_pos:
                min_pos, max_pos = max_pos, min_pos
            freq = min(2.5, max(0.01, freq))
            decline_ratio = min(0.7, max(0.3, decline_ratio))
            start_pos = start_pos if start_pos is not None else max_pos  # Starting position
            actions = [{"at": 0, "pos": start_pos}]  # Action list
            if loop_count <= 0:
                return actions
            cycle_time_ms = int(1000 / freq)  # Cycle time
            decline_time = int(cycle_time_ms * decline_ratio)  # Decline time
            rise_time = int(cycle_time_ms * (1 - decline_ratio))  # Rise time
            current_time = 0  # Current time
            next_pos = min_pos
            if start_pos < (max_pos + min_pos) / 2:
                next_pos = max_pos
            if next_pos == min_pos:
                for _ in range(loop_count):
                    actions.extend([
                        {"at": round(current_time + decline_time), "pos": min_pos},
                        {"at": round(current_time + cycle_time_ms), "pos": max_pos}
                    ])
                    current_time += cycle_time_ms
            else:
                for _ in range(loop_count):
                    actions.extend([
                        {"at": round(current_time + rise_time), "pos": max_pos},
                        {"at": round(current_time + cycle_time_ms), "pos": min_pos}
                    ])
                    current_time += cycle_time_ms
        return actions
    
    def custom_play(self, range=100, inverted=False, max_pos=100, min_pos=0, freq=1, decline_ratio=0.5, start_pos=None, loop_count=100, custom_actions=None):
        try:
            custom_funscript = {
                "range": range,
                "inverted": inverted,
                "actions": self.generate_actions(max_pos=max_pos, min_pos=min_pos, freq=freq, decline_ratio=decline_ratio, start_pos=start_pos, loop_count=loop_count, custom_actions=custom_actions)
            }
            self.stop()
            time.sleep(0.5)
            self.load_script(custom_funscript)
            self.play(0, False)
        except Exception as e:
            print(f"Failed to load custom script: {e}")
            raise e

if __name__ == "__main__":
    pass