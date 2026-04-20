import os
import time
import threading
import requests
from kubernetes import client, config

# 配置
TARGETS = ['amf', 'smf', 'upf']          # 攻击目标列表
THRESHOLD = 3                            # 连续成功阈值
INTERVAL = 1                             # 攻击间隔（秒）

config.load_incluster_config()
core_v1 = client.CoreV1Api()

# 每个目标的状态
class TargetState:
    def __init__(self, name):
        self.name = name
        self.consecutive_success = 0
        self.last_pod = None
        self.compromised = False

    def set_compromised(self, status):
        self.compromised = status
        cm_name = f"{self.name}-status"
        try:
            cm = core_v1.read_namespaced_config_map(cm_name, "default")
            cm.data["compromised"] = str(status)
            core_v1.patch_namespaced_config_map(cm_name, "default", cm)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                cm = client.V1ConfigMap(
                    metadata=client.V1ObjectMeta(name=cm_name),
                    data={"compromised": str(status)}
                )
                core_v1.create_namespaced_config_map("default", cm)
            else:
                raise

    def get_current_pod(self):
        pods = core_v1.list_namespaced_pod("default", label_selector=f"app={self.name}")
        if pods.items:
            return pods.items[0].metadata.name
        return None

    def attack_loop(self):
        """单个目标的攻击循环"""
        while True:
            current_pod = self.get_current_pod()
            if current_pod != self.last_pod:
                self.consecutive_success = 0
                self.set_compromised(False)
                print(f"[{time.time()}] {self.name}: Pod changed ({self.last_pod} -> {current_pod}), resetting")
                self.last_pod = current_pod

            try:
                headers = {"X-Attack-Target": self.name}
                url = f"http://{self.name}.default.svc.cluster.local"
                resp = requests.get(url, timeout=2, headers=headers)
                if resp.status_code == 200:
                    self.consecutive_success += 1
                    print(f"[{time.time()}] {self.name}: Success {self.consecutive_success}/{THRESHOLD}")
                    if self.consecutive_success >= THRESHOLD and not self.compromised:
                        print(f"[{time.time()}] *** {self.name.upper()} COMPROMISED ***")
                        self.set_compromised(True)
                elif resp.status_code == 503:
                    print(f"[{time.time()}] {self.name}: Blocked (503), resetting")
                    self.consecutive_success = 0
                else:
                    print(f"[{time.time()}] {self.name}: Unexpected status {resp.status_code}")
            except Exception as e:
                print(f"[{time.time()}] {self.name}: Error - {e}")

            time.sleep(INTERVAL)

def main():
    states = [TargetState(name) for name in TARGETS]
    threads = []
    for state in states:
        t = threading.Thread(target=state.attack_loop, daemon=True)
        t.start()
        threads.append(t)
    # 保持主线程运行
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()