from fastapi import APIRouter
import serial.tools.list_ports
from src import state

router = APIRouter(tags=["system"])


@router.get("/api/version")
async def get_version():
    return {"version": state.version_info}


@router.get("/api/host/ip")
async def get_host_ip():
    ip = state.get_host_ip_address()
    return {"ip": ip}


@router.get("/api/devices/serial")
async def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    usb_ports = []
    for port in ports:
        port_info = {
            "device": port.device,
            "description": port.description,
            "hwid": port.hwid,
            "is_usb": "USB" in port.hwid or "USB" in port.description
        }
        usb_ports.append(port_info)
    return {"serial_ports": usb_ports}
