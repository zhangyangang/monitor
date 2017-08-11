from pynvml import *
import logging

logger = logging.getLogger(__name__)

try:
    nvmlInit()
except NVMLError_LibraryNotFound:
    logger.warn("Couldn't initialize NVML library")


def call(func, *args, **kwargs):
  try:
    return func(*args, **kwargs)
  except NVMLError_NotSupported:
    pass


def get_versions():
    versions = {}
    try:
      versions = {'driver_version': call(nvmlSystemGetDriverVersion).decode(),
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
        minor = call(nvmlDeviceGetMinorNumber, handle)
        serial = call(nvmlDeviceGetSerial, handle)
        name = call(nvmlDeviceGetName, handle).decode()
        mem = call(nvmlDeviceGetMemoryInfo, handle)
        devices['/dev/nvidia' + minor] = {'minor': minor, 
                                          'name': name, 
                                          'handle': handle, 
                                          'serial': serial, 
                                          'memory': mem.total}
    return devices


def get_device_stats(handle):
    util = call(nvmlDeviceGetUtilizationRates, handle)
    mem = call(nvmlDeviceGetMemoryInfo, handle)
    return {
            'temperature': call(nvmlDeviceGetTemperature, handle, NVML_TEMPERATURE_GPU),
            'gpu_utilization': util.gpu,
            'mem_free': mem.free,
            'mem_total': mem.total,
            'mem_used': mem.used,
            'mem_utilization': util.memory,
            'fan_speed': call(nvmlDeviceGetFanSpeed, handle),
            'host_device': int(call(nvmlDeviceGetMinorNumber, handle))
            }