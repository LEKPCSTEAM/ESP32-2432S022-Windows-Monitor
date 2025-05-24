import psutil
import serial
import time
import GPUtil
import serial.tools.list_ports


def find_esp32_port():
    """ค้นหา USB Serial ที่เชื่อมต่อกับ ESP32"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "USB" in port.description or "CP210" in port.description or "CH340" in port.description:
            return port.device
    return None


def get_gpu_info():
    """คืนค่าการใช้งาน GPU ถ้ามี"""
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            return gpus[0].load * 100
    except Exception as e:
        print("No GPU or error:", e)
    return -1


def get_temp_info():
    """คืนค่าอุณหภูมิ CPU ถ้าใช้ Linux หรือ Windows + HWMonitor"""
    try:
        temps = psutil.sensors_temperatures()
        for name, entries in temps.items():
            for entry in entries:
                if "cpu" in entry.label.lower() or "package" in entry.label.lower():
                    return entry.current
    except Exception as e:
        pass
    return -1


def main():
    port = find_esp32_port()
    if not port:
        print("ESP32 not found.")
        return

    print(f"Connecting to {port}")
    ser = serial.Serial(port, 115200, timeout=1)
    time.sleep(2)  # รอ ESP32 รีเซต

    while True:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("C:/").percent  # ✅ เปลี่ยนเป็นไดรฟ์ที่คุณใช้จริง
        temp = get_temp_info()
        gpu = get_gpu_info()

        # ตรวจสอบว่า temp/gpu ถูกหรือไม่
        temp = round(temp, 1) if temp >= 0 else 0
        gpu = round(gpu, 1) if gpu >= 0 else 0

        payload = f"{cpu:.1f},{ram:.1f},{disk:.1f},{temp:.1f},{gpu:.1f}\n"
        print("Send:", payload.strip())
        ser.write(payload.encode())
        time.sleep(0.5)


if __name__ == "__main__":
    main()
