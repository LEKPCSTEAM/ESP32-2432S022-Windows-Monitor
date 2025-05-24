import psutil
import serial
import time
import GPUtil
import serial.tools.list_ports
import platform
import os

def find_esp32_port():
    """
    Automatically find the COM port connected to the ESP32
    by checking common USB-to-serial chip names.
    """
    ports = serial.tools.list_ports.comports()
    esp32_keywords = ["USB", "CP210", "CH340", "FTDI", "Silicon Labs", "ESP32"]
    
    for port in ports:
        description = port.description.upper()
        manufacturer = getattr(port, 'manufacturer', '').upper() if hasattr(port, 'manufacturer') else ''
        
        for keyword in esp32_keywords:
            if keyword.upper() in description or keyword.upper() in manufacturer:
                print(f"Found potential ESP32 port: {port.device} - {port.description}")
                return port.device
    
    print("Available serial ports:")
    for port in ports:
        print(f"  {port.device} - {port.description}")
    
    return None

def get_gpu_info():
    """
    Return current GPU usage percentage using GPUtil.
    If no GPU or error, return -1.
    """
    try:
        gpus = GPUtil.getGPUs()
        if gpus and len(gpus) > 0:
            gpu_load = gpus[0].load * 100
            print(f"GPU Load: {gpu_load:.1f}%")
            return gpu_load
        else:
            print("No GPU detected")
            return -1
    except Exception as e:
        print(f"GPU error: {e}")
        return -1

def get_temp_info():
    """
    Try to read CPU temperature using different methods based on the platform.
    """
    try:
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            if temps:
                print("Available temperature sensors:")
                for name, entries in temps.items():
                    print(f"  Sensor: {name}")
                    for entry in entries:
                        label = entry.label if entry.label else "Unknown"
                        print(f"    {label}: {entry.current}°C")
                        
                        label_lower = label.lower()
                        name_lower = name.lower()
                        cpu_keywords = ['cpu', 'core', 'package', 'processor', 'thermal', 'temp']
                        
                        if any(keyword in label_lower or keyword in name_lower for keyword in cpu_keywords):
                            print(f"Using CPU Temperature: {entry.current}°C from {name}")
                            return entry.current
                        
                for name, entries in temps.items():
                    if entries and entries[0].current > 0:
                        print(f"Using first available temperature from {name}: {entries[0].current}°C")
                        return entries[0].current
        
        if platform.system() == "Windows":
            try:
                import wmi
                namespaces = ["root\\OpenHardwareMonitor", "root\\WMI", "root\\CIMV2"]
                
                for namespace in namespaces:
                    try:
                        print(f"Trying WMI namespace: {namespace}")
                        w = wmi.WMI(namespace=namespace)
                        if namespace == "root\\OpenHardwareMonitor":
                            sensors = w.Sensor()
                            for sensor in sensors:
                                if hasattr(sensor, 'SensorType') and sensor.SensorType == u'Temperature':
                                    if 'cpu' in sensor.Name.lower() or 'core' in sensor.Name.lower():
                                        print(f"CPU Temperature (OpenHardwareMonitor): {sensor.Value}°C")
                                        return float(sensor.Value)
                        
                        elif namespace in ["root\\WMI", "root\\CIMV2"]:
                            try:
                                thermal_zones = w.MSAcpi_ThermalZoneTemperature()
                                for zone in thermal_zones:
                                    temp_kelvin = zone.CurrentTemperature / 10
                                    temp_celsius = temp_kelvin - 273.15
                                    if 0 < temp_celsius < 150:  
                                        print(f"CPU Temperature (WMI Thermal Zone): {temp_celsius:.1f}°C")
                                        return temp_celsius
                            except:
                                pass
                            
                            try:
                                # Win32_TemperatureProbe
                                temp_probes = w.Win32_TemperatureProbe()
                                for probe in temp_probes:
                                    if probe.CurrentReading:
                                        temp_celsius = (probe.CurrentReading / 10) - 273.15
                                        if 0 < temp_celsius < 150:
                                            print(f"CPU Temperature (WMI Probe): {temp_celsius:.1f}°C")
                                            return temp_celsius
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"WMI namespace {namespace} error: {e}")
                        continue
                        
            except ImportError:
                print("WMI not available. Install with: pip install pywin32")
            except Exception as e:
                print(f"WMI temperature read error: {e}")
        
        # Method 3: Try to use LibreHardwareMonitor or HWiNFO via WMI
        if platform.system() == "Windows":
            try:
                import wmi
                print("Trying LibreHardwareMonitor...")
                w = wmi.WMI(namespace="root\\LibreHardwareMonitor")
                sensors = w.Sensor()
                for sensor in sensors:
                    if sensor.SensorType == "Temperature" and ("cpu" in sensor.Name.lower() or "core" in sensor.Name.lower()):
                        print(f"CPU Temperature (LibreHardwareMonitor): {sensor.Value}°C")
                        return float(sensor.Value)
            except:
                pass
        
        print("No temperature sensors available or accessible")
        print("Suggestions:")
        print("1. Install HWiNFO64 with shared memory enabled")
        print("2. Install LibreHardwareMonitor")
        print("3. Run as administrator for better sensor access")
        return -1
        
    except Exception as e:
        print(f"Temperature read error: {e}")
        return -1

def get_disk_usage():
    """
    Get disk usage for the appropriate drive based on the operating system.
    """
    try:
        if platform.system() == "Windows":
            # Try C: drive first, then the current drive
            drives_to_check = ["C:\\", os.getcwd()[:3]]
        else:
            # Unix-like systems
            drives_to_check = ["/", os.getcwd()]
        
        for drive in drives_to_check:
            try:
                if os.path.exists(drive):
                    disk_usage = psutil.disk_usage(drive)
                    usage_percent = (disk_usage.used / disk_usage.total) * 100
                    print(f"Disk usage for {drive}: {usage_percent:.1f}%")
                    return usage_percent
            except Exception as e:
                print(f"Could not read disk usage for {drive}: {e}")
                continue
        
        print("Could not read disk usage from any drive")
        return -1
        
    except Exception as e:
        print(f"Disk usage error: {e}")
        return -1

def test_system_info():
    """
    Test function to check if all system info can be retrieved.
    """
    print("=== System Information Test ===")
    
    # CPU
    cpu = psutil.cpu_percent(interval=1)
    print(f"CPU Usage: {cpu:.1f}%")
    
    # RAM
    ram = psutil.virtual_memory().percent
    print(f"RAM Usage: {ram:.1f}%")
    
    # Disk
    disk = get_disk_usage()
    
    # Temperature
    temp = get_temp_info()
    
    # GPU
    gpu = get_gpu_info()
    
    print("\n=== Summary ===")
    print(f"CPU: {cpu:.1f}%, RAM: {ram:.1f}%, Disk: {disk:.1f}%, Temp: {temp:.1f}°C, GPU: {gpu:.1f}%")
    
    return cpu, ram, disk, temp, gpu

def main():
    """
    Main loop:
    - Find ESP32 serial port
    - Read system resource usage (CPU, RAM, Disk, Temp, GPU)
    - Send formatted string to ESP32 over serial every 0.5s
    """
    print("=== ESP32 System Monitor ===")
    
    print("Testing system information retrieval...")
    test_system_info()
    
    # Find ESP32 port
    port = find_esp32_port()
    if not port:
        print("\nESP32 not found. Please check:")
        print("1. ESP32 is connected via USB")
        print("2. ESP32 drivers are installed")
        print("3. ESP32 is not being used by another program")
        return
    
    try:
        print(f"\nConnecting to {port}...")
        ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)
        print("Connected successfully!")
        
        print("\nStarting data transmission (Press Ctrl+C to stop)...")
        
        while True:
            try:
                cpu = psutil.cpu_percent(interval=0.1)  
                ram = psutil.virtual_memory().percent
                disk = get_disk_usage()
                temp = get_temp_info()
                gpu = get_gpu_info()
                
                cpu = round(cpu, 1) if cpu >= 0 else 0
                ram = round(ram, 1) if ram >= 0 else 0
                disk = round(disk, 1) if disk >= 0 else 0
                temp = round(temp, 1) if temp >= 0 else 0
                gpu = round(gpu, 1) if gpu >= 0 else 0
                
                # Create formatted string: <cpu>,<ram>,<disk>,<temp>,<gpu>\n
                payload = f"{cpu:.1f},{ram:.1f},{disk:.1f},{temp:.1f},{gpu:.1f}\n"
                print(f"Sending: {payload.strip()}")
                
                # Send to ESP32
                ser.write(payload.encode())
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                print("\nStopping...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(1)  # Wait a bit before retrying
                
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        print("Please check:")
        print("1. ESP32 is properly connected")
        print("2. Correct COM port")
        print("3. ESP32 is not being used by another program")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        try:
            ser.close()
            print("Serial connection closed.")
        except:
            pass

if __name__ == "__main__":
    main()
