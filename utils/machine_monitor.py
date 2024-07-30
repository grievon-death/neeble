import psutil


class Monitor:
    """
    Show utils information about run machine.
    """
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk_usage = psutil.disk_usage('/')
    net_tcp_connections = psutil.net_connections('tcp')
    net_io_counters = psutil.net_io_counters(pernic=True)
    net_if_addrs = psutil.net_if_addrs()
    net_if_stats = psutil.net_if_stats()
    tempetatures = psutil.sensors_temperatures()

    @staticmethod
    def show_five_top_process() -> list:
        """
        Return ten top process.
        """
        _pids = psutil.pids()
        _processes = [psutil.Process(_pid) for _pid in _pids]
        _processes = sorted(_processes, key=lambda k: k._create_time, reverse=True)

        return _processes
