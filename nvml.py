from pynvml import *
import logging

logger = logging.getLogger(__name__)
nvml_initialized = False

try:
    nvmlInit()
    nvml_initialized = True
except NVMLError_LibraryNotFound:
    logger.warn("Couldn't initialize NVML library. Will not report GPU stats.")


def call(func, *args, **kwargs):
  try:
      return func(*args, **kwargs)
  except NVMLError_NotSupported:
      pass
  except NVMLError:
      pass


def get_versions():
    versions = {}
    if nvml_initialized:
        try:
            versions = {
                'driver_version': call(nvmlSystemGetDriverVersion).decode(),
                'nvml_version': call(nvmlSystemGetNVMLVersion).decode()
            }
        except NVMLError_Uninitialized:
            pass
    return versions


# from https://github.com/NVIDIA/nvidia-docker/wiki/GPU-isolation
# "If the device minor number is N, the device file is simply /dev/nvidiaN"
def get_devices():
    devices = {}
    try:
        num_devices = nvmlDeviceGetCount()
    except NVMLError_Uninitialized:
        num_devices = 0
    for i in range(num_devices):
        handle = nvmlDeviceGetHandleByIndex(i)
        pci = call(nvmlDeviceGetPciInfo, handle)
        minor = int(call(nvmlDeviceGetMinorNumber, handle))
        serial = call(nvmlDeviceGetSerial, handle).decode()
        name = call(nvmlDeviceGetName, handle).decode()
        mem = call(nvmlDeviceGetMemoryInfo, handle)
        devices['/dev/nvidia' + str(minor)] = {'minor': minor, 
                                               'name': name, 
                                               'handle': handle, 
                                               'serial': serial, 
                                               'mem_total': int(mem.total)}
    return devices


def get_power_stats(handle):
    power_draw = None
    power_limit = None
    try:
        nvmlDeviceGetPowerManagementMode(handle)
        power_draw = int(call(nvmlDeviceGetPowerUsage, handle) / 1000)
        power_limit = int(call(nvmlDeviceGetPowerManagementLimit, handle) / 1000)
    except NVMLError:
        pass
    return {'draw': power_draw, 'limit': power_limit}


def get_device_stats(handle):
    util = call(nvmlDeviceGetUtilizationRates, handle)
    mem = call(nvmlDeviceGetMemoryInfo, handle)
    power = get_power_stats(handle)
    return {
            'temperature': call(nvmlDeviceGetTemperature, handle, NVML_TEMPERATURE_GPU),
            'gpu_utilization': util.gpu,
            'mem_free': mem.free,
            'power_draw': power['draw'],
            'power_limit': power['limit'],
            'mem_total': mem.total,
            'mem_used': mem.used,
            'mem_utilization': util.memory,
            'fan_speed': call(nvmlDeviceGetFanSpeed, handle),
            'host_device': int(call(nvmlDeviceGetMinorNumber, handle))
            }