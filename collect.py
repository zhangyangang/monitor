import json
from pynvml import *

nvmlInit()

def call(func, *args, **kwargs):
  try:
    return func(*args, **kwargs)
  except NVMLError_NotSupported:
    pass

result = {
  'driver_version': call(nvmlSystemGetDriverVersion),
  'nvml_version': call(nvmlSystemGetNVMLVersion),
  'devices': [],
}

deviceCount = nvmlDeviceGetCount()
for i in range(deviceCount):
  handle = nvmlDeviceGetHandleByIndex(i)

  util = call(nvmlDeviceGetUtilizationRates, handle)
  mem = call(nvmlDeviceGetMemoryInfo, handle)

  result['devices'].append({
    'model': call(nvmlDeviceGetName, handle),
    'memory': {
      'free': mem.free,
      'total': mem.total,
      'used': mem.used,
      'utilization': util.memory,
    },
    'temperature': call(nvmlDeviceGetTemperature, handle, NVML_TEMPERATURE_GPU),
    'gpu_utilization': util.gpu,
    'fan_speed': call(nvmlDeviceGetFanSpeed, handle),
  })

print(json.dumps(result))
