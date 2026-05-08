import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    member = "member"


class EntityType(str, enum.Enum):
    bank = "bank"
    merchant = "merchant"
    issuer = "issuer"
    person = "person"
    other = "other"


class PatternSource(str, enum.Enum):
    auto_detected = "auto_detected"
    user_added = "user_added"
    ai_suggested = "ai_suggested"


class AccountType(str, enum.Enum):
    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    loan = "loan"
    other = "other"


class Currency(str, enum.Enum):
    CRC = "CRC"
    USD = "USD"


class TransactionDirection(str, enum.Enum):
    debit = "debit"
    credit = "credit"


class MatchType(str, enum.Enum):
    any = "any"
    contains = "contains"
    exact = "exact"
    regex = "regex"


class RuleSource(str, enum.Enum):
    user_confirmed = "user_confirmed"
    ai_suggested = "ai_suggested"


class CategorySource(str, enum.Enum):
    rule = "rule"
    ai_suggested = "ai_suggested"
    user_set = "user_set"


class EmailStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    skipped = "skipped"


class DocType(str, enum.Enum):
    pdf = "pdf"
    html_body = "html_body"
    plain_text = "plain_text"


class ReconciliationStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    not_applicable = "not_applicable"
