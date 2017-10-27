# RiseML Kubernetes Monitor

This component runs as a daemonset POD on each node and reports utilization stats of experimetnrs to RiseML.
Using the NVML library it reports detailed GPU statistics like temperature but also additional information like the used NVIDIA driver version and exact model and serial number of installed GPUs.
