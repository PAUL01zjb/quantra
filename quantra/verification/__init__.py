"""端到端验证：输入识别 → 输出合理性 → 数据库沉淀。"""

from quantra.verification.verify import VerificationRunner, run_verification

__all__ = ["VerificationRunner", "run_verification"]
