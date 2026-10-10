"""Сериализация/десериализация банка в JSON и XML."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET

from models import Bank, Client, Transaction, account_from_dict


class BankStorage:
    # ---------- общее ----------
    @staticmethod
    def to_dict(bank: Bank) -> dict:
        return {
            "bank": {
                "name": bank.name,
                "clients": [c.to_dict() for c in bank.clients],
                "accounts": [a.to_dict() for a in bank.accounts],
                "transactions": [t.to_dict() for t in bank.transactions],
            }
        }

    @staticmethod
    def from_dict(data: dict) -> Bank:
        bank_data = data["bank"]
        bank = Bank(bank_data["name"])

        for c_data in bank_data.get("clients", []):
            bank.add_client(Client.from_dict(c_data))

        clients = {c.client_id: c for c in bank.clients}
        for a_data in bank_data.get("accounts", []):
            bank.open_account(account_from_dict(a_data, clients))

        for t_data in bank_data.get("transactions", []):
            bank._transactions.append(Transaction.from_dict(t_data))

        return bank

    # ---------- JSON ----------
    @classmethod
    def save_json(cls, bank: Bank, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cls.to_dict(bank), f, ensure_ascii=False, indent=4)

    @classmethod
    def load_json(cls, path: str) -> Bank:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    # ---------- XML ----------
    @classmethod
    def save_xml(cls, bank: Bank, path: str) -> None:
        root = ET.Element("bank", {"name": bank.name})

        clients_el = ET.SubElement(root, "clients")
        for c in bank.clients:
            c_el = ET.SubElement(clients_el, "client", {"id": c.client_id})
            ET.SubElement(c_el, "full_name").text = c.full_name
            ET.SubElement(c_el, "passport").text = c.passport
            ET.SubElement(c_el, "phone").text = c.phone

        accounts_el = ET.SubElement(root, "accounts")
        for a in bank.accounts:
            acc_el = ET.SubElement(accounts_el, "account", {
                "number": a.number,
                "type": a.account_type,
                "currency": a.currency.value,
                "status": a.status.value,
                "owner_id": a.owner.client_id if a.owner else "",
            })
            ET.SubElement(acc_el, "balance").text = str(a.balance)
            for k, v in a._extra_dict().items():
                ET.SubElement(acc_el, k).text = str(v)

        txs_el = ET.SubElement(root, "transactions")
        for t in bank.transactions:
            t_el = ET.SubElement(txs_el, "transaction", {
                "id": t.tx_id,
                "type": t.tx_type.value,
                "currency": t.currency.value,
                "status": t.status,
            })
            ET.SubElement(t_el, "amount").text = str(t.amount)
            ET.SubElement(t_el, "timestamp").text = t.timestamp
            if t.source:
                ET.SubElement(t_el, "source").text = t.source
            if t.target:
                ET.SubElement(t_el, "target").text = t.target

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")  # Python 3.9+
        tree.write(path, encoding="utf-8", xml_declaration=True)

    @classmethod
    def load_xml(cls, path: str) -> Bank:
        root = ET.parse(path).getroot()
        bank = Bank(root.get("name", "Bank"))

        for c_el in root.findall("./clients/client"):
            bank.add_client(Client(
                client_id=c_el.get("id"),
                full_name=c_el.findtext("full_name", ""),
                passport=c_el.findtext("passport", ""),
                phone=c_el.findtext("phone", ""),
            ))
        clients = {c.client_id: c for c in bank.clients}

        for acc_el in root.findall("./accounts/account"):
            data = {
                "type": acc_el.get("type"),
                "number": acc_el.get("number"),
                "owner_id": acc_el.get("owner_id"),
                "currency": acc_el.get("currency"),
                "balance": acc_el.findtext("balance", "0"),
                "status": acc_el.get("status", "ACTIVE"),
            }
            for child in acc_el:
                if child.tag != "balance":
                    data[child.tag] = child.text
            bank.open_account(account_from_dict(data, clients))

        for t_el in root.findall("./transactions/transaction"):
            bank._transactions.append(Transaction(
                tx_type=t_el.get("type"),
                amount=t_el.findtext("amount", "0"),
                currency=t_el.get("currency"),
                source=t_el.findtext("source"),
                target=t_el.findtext("target"),
                tx_id=t_el.get("id"),
                timestamp=t_el.findtext("timestamp"),
                status=t_el.get("status", "SUCCESS"),
            ))
        return bank