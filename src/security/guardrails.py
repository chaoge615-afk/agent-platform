"""Guardrails - 输入/输出过滤和安全防护

功能：
1. 输入过滤（敏感词检测、Prompt 注入防护）
2. 输出过滤（个人信息脱敏、有害内容拦截）
3. 行为边界设定（禁止危险操作）
"""
import re
from typing import Optional, Tuple
from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    """Guardrail 检查结果"""
    passed: bool = Field(..., description="是否通过检查")
    reason: Optional[str] = Field(None, description="失败原因")
    severity: str = Field(default="info", description="严重程度: info/warning/error")
    modified_input: Optional[str] = Field(None, description="修改后的输入")
    modified_output: Optional[str] = Field(None, description="修改后的输出")


class InputGuardrail:
    """输入过滤器"""

    # 敏感词列表
    SENSITIVE_WORDS = [
        # 个人隐私
        r"\d{18}",  # 身份证号
        r"\d{16,19}",  # 银行卡号
        r"1[3-9]\d{9}",  # 手机号
        # 密码相关
        r"(?i)(password|密码|口令)",
        # 其他
        r"(?i)(admin|root|administrator)",
    ]

    # Prompt 注入检测
    INJECTION_PATTERNS = [
        r"(?i)(ignore previous|忽略之前|忘记指令)",
        r"(?i)(you are now|你现在是|扮演)",
        r"(?i)(system prompt|系统提示)",
        r"(?i)(jailbreak|越狱)",
        r"(?i)(DAN|do anything now)",
    ]

    def __init__(self):
        self.sensitive_patterns = [
            re.compile(pattern) for pattern in self.SENSITIVE_WORDS
        ]
        self.injection_patterns = [
            re.compile(pattern) for pattern in self.INJECTION_PATTERNS
        ]

    def check(self, user_input: str) -> GuardrailResult:
        """检查输入"""
        # 检查敏感词
        for pattern in self.sensitive_patterns:
            if pattern.search(user_input):
                return GuardrailResult(
                    passed=False,
                    reason="检测到敏感信息，请避免输入个人隐私数据",
                    severity="error",
                )

        # 检查 Prompt 注入
        for pattern in self.injection_patterns:
            if pattern.search(user_input):
                return GuardrailResult(
                    passed=False,
                    reason="检测到潜在的 Prompt 注入攻击",
                    severity="warning",
                )

        # 长度检查
        if len(user_input) > 10000:
            return GuardrailResult(
                passed=False,
                reason="输入过长，请限制在 10000 字符以内",
                severity="warning",
            )

        return GuardrailResult(passed=True)


class OutputGuardrail:
    """输出过滤器"""

    # 个人信息模式
    PII_PATTERNS = [
        (r"\d{18}", "***"),  # 身份证号
        (r"\d{16,19}", "***"),  # 银行卡号
        (r"1[3-9]\d{9}", "***"),  # 手机号
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]"),  # 邮箱
    ]

    def __init__(self):
        self.pii_patterns = [
            (re.compile(pattern), replacement)
            for pattern, replacement in self.PII_PATTERNS
        ]

    def filter(self, output: str) -> GuardrailResult:
        """过滤输出"""
        modified = output

        # 脱敏个人信息
        for pattern, replacement in self.pii_patterns:
            modified = pattern.sub(replacement, modified)

        if modified != output:
            return GuardrailResult(
                passed=True,
                reason="已脱敏个人信息",
                severity="info",
                modified_output=modified,
            )

        return GuardrailResult(passed=True, modified_output=output)


class BehaviorGuardrail:
    """行为边界"""

    # 危险 SQL 操作
    DANGEROUS_SQL_PATTERNS = [
        r"(?i)\bDELETE\b",
        r"(?i)\bUPDATE\b",
        r"(?i)\bDROP\b",
        r"(?i)\bTRUNCATE\b",
        r"(?i)\bALTER\b",
        r"(?i)\bCREATE\b",
        r"(?i)\bGRANT\b",
        r"(?i)\bREVOKE\b",
    ]

    def __init__(self):
        self.dangerous_patterns = [
            re.compile(pattern) for pattern in self.DANGEROUS_SQL_PATTERNS
        ]

    def check_sql(self, sql: str) -> Tuple[bool, str]:
        """检查 SQL 是否安全

        Returns:
            (is_safe, reason)
        """
        for pattern in self.dangerous_patterns:
            if pattern.search(sql):
                return False, f"检测到危险 SQL 操作: {pattern.pattern}"

        return True, "SQL 安全"


# 全局实例
input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()
behavior_guardrail = BehaviorGuardrail()


def check_input(user_input: str) -> GuardrailResult:
    """检查输入（便捷函数）"""
    return input_guardrail.check(user_input)


def filter_output(output: str) -> GuardrailResult:
    """过滤输出（便捷函数）"""
    return output_guardrail.filter(output)


def check_sql(sql: str) -> Tuple[bool, str]:
    """检查 SQL（便捷函数）"""
    return behavior_guardrail.check_sql(sql)
