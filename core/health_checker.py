import threading
import time
from typing import Callable, Dict, Any

class QPSMonitor:
    def __init__(self, window_sec=60):
        self.window_sec = window_sec
        self.model_stats = {}  # model_name -> [timestamps]
        self.lock = threading.Lock()

    def record(self, model_name: str):
        now = time.time()
        with self.lock:
            if model_name not in self.model_stats:
                self.model_stats[model_name] = []
            self.model_stats[model_name].append(now)
            # 清理过期
            self.model_stats[model_name] = [t for t in self.model_stats[model_name] if now - t <= self.window_sec]

    def get_qps(self, model_name: str) -> float:
        now = time.time()
        with self.lock:
            times = self.model_stats.get(model_name, [])
            times = [t for t in times if now - t <= self.window_sec]
            return len(times) / self.window_sec if self.window_sec > 0 else 0.0

    def is_limited(self, model_name: str, max_qps: float) -> bool:
        return self.get_qps(model_name) > max_qps if max_qps > 0 else False

class HealthChecker:
    def __init__(self, get_models: Callable[[], list], update_model_meta: Callable[[str, Dict[str, Any]], None], check_func: Callable[[Dict[str, Any]], bool], min_interval=10, max_interval=600):
        """
        get_models: 返回模型列表的函数
        update_model_meta: (model_name, meta_dict) -> None
        check_func: (model_dict) -> bool, 返回健康与否
        min_interval/max_interval: 健康检查最小/最大间隔（秒）
        """
        self.get_models = get_models
        self.update_model_meta = update_model_meta
        self.check_func = check_func
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.model_next_check = {}  # model_name -> next_check_time
        self.model_interval = {}    # model_name -> interval
        self.model_last_active = {} # model_name -> last_active_time
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def notify_model_active(self, model_name: str):
        with self.lock:
            self.model_last_active[model_name] = time.time()

    def adjust_interval(self, model_name: str, qps: float):
        # QPS高则频率高，QPS低则频率低
        if qps > 5:
            interval = self.min_interval
        elif qps > 1:
            interval = 30
        elif model_name in self.model_last_active and time.time() - self.model_last_active[model_name] > 3600:
            interval = self.max_interval
        else:
            interval = 120
        self.model_interval[model_name] = max(self.min_interval, min(interval, self.max_interval))
        self.model_next_check[model_name] = time.time() + self.model_interval[model_name]

    def start(self, qps_monitor: QPSMonitor):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, args=(qps_monitor,), daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _run(self, qps_monitor: QPSMonitor):
        while self.running:
            now = time.time()
            models = self.get_models()
            for model in models:
                name = model["name"]
                interval = self.model_interval.get(name, 60)
                next_check = self.model_next_check.get(name, 0)
                qps = qps_monitor.get_qps(name)
                if now >= next_check:
                    healthy = False
                    try:
                        healthy = self.check_func(model)
                    except Exception as e:
                        healthy = False
                    meta = {
                        "health": "healthy" if healthy else "unhealthy",
                        "status": "可用" if healthy else "下线"
                    }
                    self.update_model_meta(name, meta)
                    self.adjust_interval(name, qps)
            time.sleep(2)

# API友好接口示例
# qps_monitor = QPSMonitor()
# health_checker = HealthChecker(get_models, update_model_meta, check_func)
# health_checker.start(qps_monitor)
# 在模型调用时：qps_monitor.record(model_name); health_checker.notify_model_active(model_name)
# 查询QPS：qps_monitor.get_qps(model_name)
# 查询限流：qps_monitor.is_limited(model_name, max_qps) 