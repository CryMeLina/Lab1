"""Демонстрация работы банковской системы."""
import json
import xml.etree.ElementTree as ET
from datetime import datetime

from exceptions import BankError
from models import (
    AccountStatus, Bank, Client,
    CreditAccount, DebitAccount, DepositAccount,
)
from storage import BankStorage


def build_demo_bank() -> Bank:
    bank = Bank("ПАО «Пример-Банк»")

    ivanov = Client("C001", "Иванов Иван Иванович", "4509 123456", "+7-900-111-22-33")
    petrova = Client("C002", "Петрова Анна Сергеевна", "4510 654321", "+7-900-444-55-66")
    bank.add_client(ivanov)
    bank.add_client(petrova)

    acc_rub_1 = DebitAccount("40817810000000000001", ivanov, "RUB", "10000")
    acc_rub_2 = DebitAccount("40817810000000000002", petrova, "RUB", "5000")
    acc_credit = CreditAccount("40817810000000000003", petrova, "RUB", "0",
                               credit_limit="50000")
    acc_deposit = DepositAccount("42307810000000000004", ivanov, "RUB", "100000",
                                 interest_rate="7.5", term_months=12,
                                 opened_at=datetime.now().strftime("%Y-%m-%d"))
    acc_usd = DebitAccount("40817840800000000005", ivanov, "USD", "500")

    for acc in (acc_rub_1, acc_rub_2, acc_credit, acc_deposit, acc_usd):
        bank.open_account(acc)

    return bank


def demo_operations(bank: Bank) -> None:
    print("=== Успешные операции ===")
    bank.deposit("40817810000000000001", "5000")
    bank.withdraw("40817810000000000002", "1000")
    bank.transfer("40817810000000000001", "40817810000000000002", "2000")
    print("Операции выполнены успешно\n")


def demo_errors(bank: Bank) -> None:
    print("=== Демонстрация обработки исключений ===")
    scenarios = [
        ("Снятие суммы больше доступной",
         lambda: bank.withdraw("40817810000000000002", "999999")),
        ("Отрицательная сумма",
         lambda: bank.deposit("40817810000000000001", "-100")),
        ("Несуществующий счёт",
         lambda: bank.get_account("00000000000000000000")),
        ("Несуществующий клиент",
         lambda: bank.get_client("C999")),
        ("Перевод между разными валютами",
         lambda: bank.transfer("40817810000000000001",
                               "40817840800000000005", "100")),
        ("Снятие с депозита до истечения срока",
         lambda: bank.withdraw("42307810000000000004", "1000")),
        ("Повторное добавление клиента",
         lambda: bank.add_client(bank.get_client("C001"))),
    ]
    for title, action in scenarios:
        try:
            action()
            print(f"  {title}: операция выполнена")
        except BankError as e:
            print(f"  {title}: [{type(e).__name__}] {e}")
        except Exception as e:  # страховка на случай неожиданных ошибок
            print(f"  {title}: [НЕПРЕДВИДЕННАЯ {type(e).__name__}] {e}")
    print()


def demo_storage(bank: Bank) -> None:
    print("=== Сохранение/загрузка JSON и XML ===")

    # --- JSON ---
    try:
        BankStorage.save_json(bank, "bank.json")
        print("  JSON сохранён: bank.json")
    except (OSError, TypeError) as e:
        print(f"  Ошибка сохранения JSON: {type(e).__name__}: {e}")

    try:
        bank_json = BankStorage.load_json("bank.json")
        print(f"  JSON загружен: клиентов={len(bank_json.clients)}, "
              f"счетов={len(bank_json.accounts)}, "
              f"транзакций={len(bank_json.transactions)}")
    except FileNotFoundError:
        print("  Файл bank.json не найден")
    except json.JSONDecodeError as e:
        print(f"  Некорректный JSON: {e}")
    except (KeyError, BankError) as e:
        print(f"  Ошибка структуры данных: {type(e).__name__}: {e}")

    # --- XML ---
    try:
        BankStorage.save_xml(bank, "bank.xml")
        print("  XML сохранён: bank.xml")
    except OSError as e:
        print(f"  Ошибка сохранения XML: {e}")

    try:
        bank_xml = BankStorage.load_xml("bank.xml")
        print(f"  XML загружен: клиентов={len(bank_xml.clients)}, "
              f"счетов={len(bank_xml.accounts)}, "
              f"транзакций={len(bank_xml.transactions)}")
    except FileNotFoundError:
        print("  Файл bank.xml не найден")
    except ET.ParseError as e:
        print(f"  Некорректный XML: {e}")
    except (KeyError, BankError) as e:
        print(f"  Ошибка структуры данных: {type(e).__name__}: {e}")


def main() -> None:
    try:
        bank = build_demo_bank()
        demo_operations(bank)
        demo_errors(bank)
        demo_storage(bank)
    except BankError as e:
        print(f"Критическая ошибка банка: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка: {type(e).__name__}: {e}")
    finally:
        print("\nРабота программы завершена.")


if __name__ == "__main__":
    main()