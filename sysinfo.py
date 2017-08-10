

def get_cpu_info():
    nprocs = 0
    model_name = 'unknown'
    with open('/proc/cpuinfo') as f:
        for line in f:
            if not line.strip():
                nprocs = nprocs + 1
            else:
                if line.startswith('model name'):
                    model_name = line.split(':')[1].strip()
    return nprocs, model_name


def get_mem_total():
    meminfo = {}
    with open('/proc/meminfo') as f:
        for line in f:
            meminfo[line.split(':')[0]] = line.split(':')[1].strip().split(' ')[0]
    mem_total = int(meminfo['MemTotal']) * 1000
    return mem_total


def get_system_info():
    n_cores, cpu_model = get_cpu_info()
    mem_total = get_mem_total()
    return {'num_cores': n_cores,
            'cpu_model': cpu_model,
            'mem_total': mem_total}


if __name__ == '__main__':
    print(get_system_info())