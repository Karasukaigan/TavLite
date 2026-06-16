import socket
from zeroconf import Zeroconf, ServiceInfo
from src import state
from src.logger import get_runtime_logger

_log = get_runtime_logger("mdns")

_zeroconf = None


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def start_mdns():
    global _zeroconf
    try:
        local_ip = get_local_ip()
        _zeroconf = Zeroconf()
        service_info = ServiceInfo(
            type_="_http._tcp.local.",
            name="tavlite._http._tcp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=state.PORT,
            properties={},
            server="tavlite.local.",
        )
        _zeroconf.register_service(service_info)
        _log.info("mDNS service registered: tavlite.local -> %s:%d", local_ip, state.PORT)
    except Exception as e:
        _log.error("Failed to register mDNS service: %s", e)


def stop_mdns():
    global _zeroconf
    if _zeroconf:
        try:
            _zeroconf.unregister_all_services()
            _zeroconf.close()
        except Exception as e:
            _log.error("Failed to stop mDNS service: %s", e)
        _zeroconf = None
