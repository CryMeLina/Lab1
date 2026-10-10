"""Пользовательские исключения банковской системы."""


class BankError(Exception):
    """Базовое исключение для всех ошибок банковской системы."""

    def __init__(self, message: str = "Ошибка банковской операции"):
        self.message = message
        super().__init__(self.message)


class ClientNotFoundError(BankError):
    def __init__(self, client_id: str):
        super().__init__(f"Клиент с идентификатором '{client_id}' не найден")
        self.client_id = client_id


class DuplicateClientError(BankError):
    def __init__(self, client_id: str):
        super().__init__(f"Клиент с идентификатором '{client_id}' уже существует")
        self.client_id = client_id


class AccountNotFoundError(BankError):
    def __init__(self, account_number: str):
        super().__init__(f"Счёт '{account_number}' не найден")
        self.account_number = account_number


class AccountClosedError(BankError):
    def __init__(self, account_number: str):
        super().__init__(f"Счёт '{account_number}' закрыт, операция невозможна")
        self.account_number = account_number


class AccountFrozenError(BankError):
    def __init__(self, account_number: str):
        super().__init__(f"Счёт '{account_number}' заморожен, операция невозможна")
        self.account_number = account_number


class InvalidAmountError(BankError):
    def __init__(self, amount):
        super().__init__(
            f"Недопустимая сумма операции: {amount!r}. Сумма должна быть > 0"
        )
        self.amount = amount


class InsufficientFundsError(BankError):
    def __init__(self, account_number: str, required, available):
        super().__init__(
            f"Недостаточно средств на счёте {account_number}: "
            f"требуется {required}, доступно {available}"
        )
        self.account_number = account_number
        self.required = required
        self.available = available


class CurrencyMismatchError(BankError):
    def __init__(self, currency_from: str, currency_to: str):
        super().__init__(
            f"Несовпадение валют операции: {currency_from} → {currency_to}"
        )
        self.currency_from = currency_from
        self.currency_to = currency_to