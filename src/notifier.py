import time
from src.logger import get_logger

log = get_logger("Notifier")

class Notifier:
    def __init__(self, channel: str):
        self.channel = channel

    def __call__(self, message: str) -> bool:
        return self.send(message)

    def send(self, message: str) -> bool:
        try:
            time.sleep(0.5) # 模拟网络延迟
            log.info(f"🚨 【{self.channel}】告警已发送: {message}")
            return True
        except Exception as e:
            log.error(f"❌ 【{self.channel}】告警发送失败: {e}")
            return False