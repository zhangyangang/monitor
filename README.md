# RiseML Kubernetes Monitor

This component monitors new PODs on a node and publishes utilization stats of PODs to a queue.
Using the NVML library it reports detailed GPU statistics like temperature and additional information like the used NVIDIA driver version and exact model and serial number of installed GPUs.

## Environment Variables

Please check [config.py](https://github.com/riseml/monitor/blob/master/monitor/config.py). It contains all environment variables used.

## Published Node Information

The following information is sent on startup:

```javascript
{  
   "name":"ip-172-31-30-80",
   "gpus":[  
      {  
         "name":"Tesla V100-SXM2-16GB",
         "mem":16936861696,
         "serial":"0322917092147",
         "device":"/dev/nvidia0"
      }
   ],
   "memory":62879860000,
   "cpus":4,
   "nvidia_driver":"384.90",
   "cpu_model":"Intel(R) Xeon(R) CPU E5-2686 v4 @ 2.30GHz"
}
```

## Utilization Stats

The following messages are sent while a POD is running:

**GPU utilization**:
```
{  
   "job_id":"0408f010-bb08-11e7-965a-0a580af4f059",
   "gpus":{  
      "/dev/nvidia0":{  
         "temperature":60,
         "power_limit":249,
         "memory_utilization":31,
         "gpu_utilization":67,
         "memory_free":520421376,
         "name":"Tesla V100-SXM2-16GB",
         "device_minor":0,
         "power_draw":107,
         "memory_total":16936861696,
         "device_bus_id":"0000:00:1E.0",
         "fan_speed":null,
         "memory_used":11475156992
      }
   },
   "timestamp":1509103012437
}
```

**CPU/memory utilization**:
```javascript
{  
   "job_id":"0408f010-bb08-11e7-965a-0a580af4f059",
   "percpu_percent":[  
      96.71262123755025,
      97.95838776488651,
      95.34449857171664,
      95.66360231475599
   ],
   "memory_limit":64388976640,
   "timestamp":1509103012109,
   "memory_used":1828540416,
   "cpu_percent":385.6786764857881
}
```
