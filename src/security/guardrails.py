"""Guardrails - 输入/输出过滤和安全防护

功能：
1. 输入过滤（敏感词检测、Prompt 注入防护）
2. 输出过滤（个人信息脱敏、有害内容拦截）
3. 行为边界设定（禁止危险操作）
"""
import re
from typing import Optional, Tuple
from pydantic import BaseModel, Field


def _is_luhn_valid(number_str: str) -> bool:
    """Luhn 算法校验：银行卡号必须通过此校验"""
    digits = [int(d) for d in number_str]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10 == 0


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
        # 个人隐私（使用边界约束避免匹配更长数字串）
        r"(?<!\d)\d{18}(?!\d)",  # 身份证号（恰好 18 位，前后不是数字）
        r"(?<!\d)1[3-9]\d{9}(?!\d)",  # 手机号（恰好 11 位，前后不是数字）
        # 密码相关
        r"(?i)(password|密码|口令)",
        # 其他
        r"(?i)(admin|root|administrator)",
    ]

    # 银行卡上下文关键词（Luhn 通过 + 命中任一 → 拦截）
    BANK_CONTEXT_WORDS = ["银行卡", "卡号", "bank", "credit card", "debit card"]

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
        # 1. 先检查 SQL 危险操作（行为护栏优先于 PII）
        sql_safe, sql_reason = behavior_guardrail.check_sql(user_input)
        if not sql_safe:
            return GuardrailResult(
                passed=False,
                reason=sql_reason,
                severity="error",
            )

        # 2. 检查敏感词（身份证、手机号、密码词、管理员词）
        for pattern in self.sensitive_patterns:
            if pattern.search(user_input):
                return GuardrailResult(
                    passed=False,
                    reason="检测到敏感信息，请避免输入个人隐私数据",
                    severity="error",
                )

        # 3. 银行卡号检测：Luhn 校验 + 上下文关键词
        bank_numbers = re.findall(r"(?<!\d)\d{16,19}(?!\d)", user_input)
        for num in bank_numbers:
            if _is_luhn_valid(num):
                has_context = any(
                    kw in user_input.lower()
                    for kw in self.BANK_CONTEXT_WORDS
                )
                if has_context:
                    return GuardrailResult(
                        passed=False,
                        reason="检测到银行卡号，请避免输入金融隐私数据",
                        severity="error",
                    )

        # 4. 检查 Prompt 注入
        for pattern in self.injection_patterns:
            if pattern.search(user_input):
                return GuardrailResult(
                    passed=False,
                    reason="检测到潜在的 Prompt 注入攻击",
                    severity="warning",
                )

        # 5. 长度检查
        if len(user_input) > 10000:
            return GuardrailResult(
                passed=False,
                reason="输入过长，请限制在 10000 字符以内",
                severity="warning",
            )

        return GuardrailResult(passed=True)


class OutputGuardrail:
    """输出过滤器"""

    # 个人信息模式（银行卡号改用 Luhn 校验，见 filter 方法）
    PII_PATTERNS = [
        (r"(?<!\d)\d{18}(?!\d)", "***"),  # 身份证号（恰好 18 位）
        (r"(?<!\d)1[3-9]\d{9}(?!\d)", "***"),  # 手机号（恰好 11 位）
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

        # 银行卡脱敏：仅对通过 Luhn 校验的 16-19 位数字脱敏
        def luhn_replace(match):
            return "***" if _is_luhn_valid(match.group()) else match.group()
        modified = re.sub(r"(?<!\d)\d{16,19}(?!\d)", luhn_replace, modified)

        # 其他 PII 脱敏
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
