import psutil
from collections import deque
import threading
import time


class SystemMonitor:
    """Monitor and collect system metrics for real-time display."""

    def __init__(self, max_history=60):
        """
        Initialize system monitor.
        
        Args:
            max_history: Maximum number of data points to keep per metric
        """
        self.max_history = max_history
        self.cpu_history = deque(maxlen=max_history)
        self.memory_history = deque(maxlen=max_history)
        self.disk_history = deque(maxlen=max_history)
        self.net_io_history = deque(maxlen=max_history)
        
        self.current_metrics = {
            'cpu': 0,
            'memory': 0,
            'disk': 0,
            'net_in': 0,
            'net_out': 0,
            'temp': 0
        }
        
        self.running = True
        self.lock = threading.Lock()
        self.last_net_io = None
    
    def get_cpu_usage(self):
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)
    
    def get_memory_usage(self):
        """Get current memory usage percentage."""
        return psutil.virtual_memory().percent
    
    def get_disk_usage(self):
        """Get disk usage percentage for the system drive."""
        try:
            return psutil.disk_usage('/').percent
        except Exception:
            try:
                return psutil.disk_usage('C:\\').percent
            except Exception:
                return 0
    
    def get_network_info(self):
        """Get network I/O stats (bytes per second)."""
        try:
            net_io = psutil.net_io_counters()
            if self.last_net_io:
                time_delta = 1  # Assuming 1 second between calls
                bytes_in = (net_io.bytes_recv - self.last_net_io.bytes_recv) / time_delta
                bytes_out = (net_io.bytes_sent - self.last_net_io.bytes_sent) / time_delta
                self.last_net_io = net_io
                return bytes_in, bytes_out
            else:
                self.last_net_io = net_io
                return 0, 0
        except Exception:
            return 0, 0
    
    def get_cpu_temp(self):
        """Get CPU temperature if available."""
        try:
            temps = psutil.sensors_temperatures()
            if temps and 'coretemp' in temps:
                return temps['coretemp'][0].current
            elif temps:
                first_key = list(temps.keys())[0]
                return temps[first_key][0].current
        except Exception:
            pass
        return 0
    
    def update_metrics(self):
        """Collect current metrics."""
        with self.lock:
            self.current_metrics['cpu'] = self.get_cpu_usage()
            self.current_metrics['memory'] = self.get_memory_usage()
            self.current_metrics['disk'] = self.get_disk_usage()
            net_in, net_out = self.get_network_info()
            self.current_metrics['net_in'] = net_in
            self.current_metrics['net_out'] = net_out
            self.current_metrics['temp'] = self.get_cpu_temp()
            
            # Add to history
            self.cpu_history.append(self.current_metrics['cpu'])
            self.memory_history.append(self.current_metrics['memory'])
            self.disk_history.append(self.current_metrics['disk'])
            self.net_io_history.append((net_in, net_out))
    
    def get_metrics(self):
        """Get a copy of current metrics."""
        with self.lock:
            return self.current_metrics.copy()
    
    def get_history(self, metric_name):
        """Get history for a specific metric."""
        with self.lock:
            if metric_name == 'cpu':
                return list(self.cpu_history)
            elif metric_name == 'memory':
                return list(self.memory_history)
            elif metric_name == 'disk':
                return list(self.disk_history)
            elif metric_name == 'net':
                return list(self.net_io_history)
        return []
