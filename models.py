
"""Доменная модель банка: клиенты, счета, транзакции."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum

from exceptions import (
    AccountClosedError,
    AccountFrozenError,
    AccountNotFoundError,
    BankError,
    ClientNotFoundError,
    CurrencyMismatchError,
    DuplicateClientError,
    InsufficientFundsError,
    InvalidAmountError,
)


# ---------- Перечисления ----------
class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class TransactionType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    TRANSFER = "TRANSFER"


# ---------- Клиент ----------
class Client:
    def __init__(self, client_id: str, full_name: str, passport: str, phone: str):
        self.client_id = client_id
        self.full_name = full_name
        self.passport = passport
        self.phone = phone
        self._accounts: list[Account] = []

    @property
    def accounts(self) -> list["Account"]:
        return list(self._accounts)

    def add_account(self, account: "Account") -> None:
        if account not in self._accounts:
            self._accounts.append(account)
            account.owner = self

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "full_name": self.full_name,
            "passport": self.passport,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Client":
        return cls(data["client_id"], data["full_name"],
                   data["passport"], data["phone"])

    def __repr__(self) -> str:
        return f"Client({self.client_id!r}, {self.full_name!r})"


# ---------- Счета ----------
class Account(ABC):
    account_type: str = "BASE"

    def __init__(self, number: str, owner: Client, currency,
                 balance=Decimal("0"), status=AccountStatus.ACTIVE):
        self.number = number
        self.owner = owner
        self.currency = Currency(currency)
        self._balance = Decimal(str(balance))
        self.status = AccountStatus(status)
        self._history: list[Transaction] = []

    # --- свойства ---
    @property
    def balance(self) -> Decimal:
        return self._balance

    @property
    def history(self) -> list["Transaction"]:
        return list(self._history)

    @property
    @abstractmethod
    def available_amount(self) -> Decimal:
        """Сумма, доступная к снятию."""

    # --- служебные методы ---
    def _check_operation(self, amount: Decimal) -> None:
        if self.status == AccountStatus.CLOSED:
            raise AccountClosedError(self.number)
        if self.status == AccountStatus.FROZEN:
            raise AccountFrozenError(self.number)
        if amount is None or amount <= 0:
            raise InvalidAmountError(amount)

    # --- операции ---
    def deposit(self, amount) -> Decimal:
        try:
            amount = Decimal(str(amount))
        except Exception:
            raise InvalidAmountError(amount) from None
        self._check_operation(amount)
        self._balance += amount
        return self._balance

    def withdraw(self, amount) -> Decimal:
        try:
            amount = Decimal(str(amount))
        except Exception:
            raise InvalidAmountError(amount) from None
        self._check_operation(amount)
        if amount > self.available_amount:
            raise InsufficientFundsError(self.number, amount, self.available_amount)
        self._balance -= amount
        return self._balance

    def close(self) -> None:
        if self._balance != 0:
            raise BankError(
                f"Нельзя закрыть счёт {self.number} с ненулевым балансом"
            )
        self.status = AccountStatus.CLOSED

    def add_transaction(self, tx: "Transaction") -> None:
        self._history.append(tx)

    # --- сериализация ---
    def to_dict(self) -> dict:
        return {
            "type": self.account_type,
            "number": self.number,
            "owner_id": self.owner.client_id if self.owner else None,
            "currency": self.currency.value,
            "balance": str(self._balance),
            "status": self.status.value,
            **self._extra_dict(),
        }

    def _extra_dict(self) -> dict:
        return {}

    def __repr__(self) -> str:
        return (f"{self.account_type}({self.number}, "
                f"{self._balance} {self.currency.value})")


class DebitAccount(Account):
    account_type = "DEBIT"

    @property
    def available_amount(self) -> Decimal:
        return self._balance


class CreditAccount(Account):
    account_type = "CREDIT"

    def __init__(self, number, owner, currency, balance=Decimal("0"),
                 status=AccountStatus.ACTIVE, credit_limit=Decimal("0")):
        super().__init__(number, owner, currency, balance, status)
        self.credit_limit = Decimal(str(credit_limit))

    @property
    def available_amount(self) -> Decimal:
        return self._balance + self.credit_limit

    def _extra_dict(self) -> dict:
        return {"credit_limit": str(self.credit_limit)}


class DepositAccount(Account):
    account_type = "DEPOSIT"

    def __init__(self, number, owner, currency, balance=Decimal("0"),
                 status=AccountStatus.ACTIVE,
                 interest_rate=Decimal("0"), term_months: int = 12,
                 opened_at: str | None = None):
        super().__init__(number, owner, currency, balance, status)
        self.interest_rate = Decimal(str(interest_rate))
        self.term_months = int(term_months)
        self.opened_at = opened_at or datetime.now().strftime("%Y-%m-%d")

    @property
    def available_amount(self) -> Decimal:
        return self._balance

    def _is_matured(self) -> bool:
        opened = datetime.strptime(self.opened_at, "%Y-%m-%d")
        now = datetime.now()
        months = (now.year - opened.year) * 12 + (now.month - opened.month)
        return months >= self.term_months

    def withdraw(self, amount) -> Decimal:
        if not self._is_matured():
            raise BankError(
                f"Срок депозита на счёте {self.number} ещё не истёк"
            )
        return super().withdraw(amount)

    def _extra_dict(self) -> dict:
        return {
            "interest_rate": str(self.interest_rate),
            "term_months": self.term_months,
            "opened_at": self.opened_at,
        }


def account_from_dict(data: dict, clients_by_id: dict[str, Client]) -> Account:
    """Фабрика счетов: восстанавливает объект нужного подкласса."""
    acc_type = data.get("type")
    owner = clients_by_id.get(data.get("owner_id"))
    if owner is None:
        raise ClientNotFoundError(str(data.get("owner_id")))

    common = dict(
        number=data["number"],
        owner=owner,
        currency=data["currency"],
        balance=data.get("balance", "0"),
        status=data.get("status", AccountStatus.ACTIVE.value),
    )

    if acc_type == "DEBIT":
        return DebitAccount(**common)
    if acc_type == "CREDIT":
        return CreditAccount(credit_limit=data.get("credit_limit", "0"), **common)
    if acc_type == "DEPOSIT":
        return DepositAccount(
            interest_rate=data.get("interest_rate", "0"),
            term_months=int(data.get("term_months", 12)),
            opened_at=data.get("opened_at"),
            **common,
        )
    raise BankError(f"Неизвестный тип счёта: {acc_type!r}")


# ---------- Транзакция ----------
class Transaction:
    _counter = 0

    def __init__(self, tx_type, amount, currency,
                 source: str | None = None, target: str | None = None,
                 tx_id: str | None = None, timestamp: str | None = None,
                 status: str = "SUCCESS"):
        Transaction._counter += 1
        self.tx_id = tx_id or f"TX{Transaction._counter:06d}"
        self.tx_type = TransactionType(tx_type)
        self.amount = Decimal(str(amount))
        self.currency = Currency(currency)
        self.source = source
        self.target = target
        self.timestamp = timestamp or datetime.now().isoformat(timespec="seconds")
        self.status = status

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "type": self.tx_type.value,
            "amount": str(self.amount),
            "currency": self.currency.value,
            "source": self.source,
            "target": self.target,
            "timestamp": self.timestamp,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            tx_type=data["type"],
            amount=data["amount"],
            currency=data["currency"],
            source=data.get("source"),
            target=data.get("target"),
            tx_id=data["tx_id"],
            timestamp=data["timestamp"],
            status=data.get("status", "SUCCESS"),
        )

    def __repr__(self) -> str:
        return (f"Transaction({self.tx_id}, {self.tx_type.value}, "
                f"{self.amount} {self.currency.value})")


# ---------- Банк ----------
class Bank:
    def __init__(self, name: str):
        self.name = name
        self._clients: dict[str, Client] = {}
        self._accounts: dict[str, Account] = {}
        self._transactions: list[Transaction] = []

    @property
    def clients(self) -> list[Client]:
        return list(self._clients.values())

    @property
    def accounts(self) -> list[Account]:
        return list(self._accounts.values())

    @property
    def transactions(self) -> list[Transaction]:
        return list(self._transactions)

    # --- клиенты ---
    def add_client(self, client: Client) -> None:
        if client.client_id in self._clients:
            raise DuplicateClientError(client.client_id)
        self._clients[client.client_id] = client

    def get_client(self, client_id: str) -> Client:
        try:
            return self._clients[client_id]
        except KeyError:
            raise ClientNotFoundError(client_id) from None

    # --- счета ---
    def open_account(self, account: Account) -> Account:
        if account.owner is None:
            raise BankError("У счёта не указан владелец")
        if account.number in self._accounts:
            raise BankError(f"Счёт {account.number} уже открыт")
        self._accounts[account.number] = account
        if account not in account.owner.accounts:
            account.owner.add_account(account)
        return account

    def get_account(self, number: str) -> Account:
        try:
            return self._accounts[number]
        except KeyError:
            raise AccountNotFoundError(number) from None

    # --- операции ---
    def deposit(self, account_number: str, amount) -> Transaction:
        acc = self.get_account(account_number)
        acc.deposit(amount)
        tx = Transaction(TransactionType.DEPOSIT, amount, acc.currency.value,
                         target=account_number)
        self._transactions.append(tx)
        acc.add_transaction(tx)
        return tx

    def withdraw(self, account_number: str, amount) -> Transaction:
        acc = self.get_account(account_number)
        acc.withdraw(amount)
        tx = Transaction(TransactionType.WITHDRAW, amount, acc.currency.value,
                         source=account_number)
        self._transactions.append(tx)
        acc.add_transaction(tx)
        return tx

    def transfer(self, src_number: str, dst_number: str, amount) -> Transaction:
        src = self.get_account(src_number)
        dst = self.get_account(dst_number)
        if src.currency != dst.currency:
            raise CurrencyMismatchError(src.currency.value, dst.currency.value)

        src.withdraw(amount)
        try:
            dst.deposit(amount)
        except BankError:
            # откат, если зачисление не удалось
            src.deposit(amount)
            raise

        tx = Transaction(TransactionType.TRANSFER, amount, src.currency.value,
                         source=src_number, target=dst_number)
        self._transactions.append(tx)
        src.add_transaction(tx)
        dst.add_transaction(tx)
        return tx