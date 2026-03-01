from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
import json
import csv
import os
import uuid
import tempfile

STORAGE_FILE = "estoque.json"


@dataclass
class Item:
    id: str
    nome: str
    sku: Optional[str]
    quantidade: int
    preco: float
    estoque_minimo: int = 0
    local: Optional[str] = None
    descricao: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


class Inventory:
    def __init__(self, storage_file: str = STORAGE_FILE):
        self.storage_file = storage_file
        self.items: Dict[str, Item] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.storage_file):
            self._save()  # cria arquivo vazio
            return
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item_data in data.get("items", []):
                item = Item(**item_data)
                self.items[item.id] = item
        except (json.JSONDecodeError, FileNotFoundError):
            self.items = {}
            self._save()

    def _save(self):
        # salva de forma atômica
        data = {"items": [it.to_dict() for it in self.items.values()]}
        dirn = os.path.dirname(os.path.abspath(self.storage_file)) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dirn, prefix="tmp_estoque_", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmpf:
                json.dump(data, tmpf, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.storage_file)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def add_item(self, nome: str, quantidade: int, preco: float,
                 sku: Optional[str] = None, estoque_minimo: int = 0,
                 local: Optional[str] = None, descricao: Optional[str] = None) -> Item:
        new_id = str(uuid.uuid4())
        item = Item(id=new_id, nome=nome.strip(), sku=sku, quantidade=int(quantidade),
                    preco=float(preco), estoque_minimo=int(estoque_minimo),
                    local=local, descricao=descricao)
        self.items[item.id] = item
        self._save()
        return item

    def remove_item(self, item_id: str) -> bool:
        if item_id in self.items:
            del self.items[item_id]
            self._save()
            return True
        return False

    def update_quantity(self, item_id: str, delta: int) -> Optional[Item]:
        item = self.items.get(item_id)
        if not item:
            return None
        item.quantidade = int(item.quantidade) + int(delta)
        if item.quantidade < 0:
            item.quantidade = 0
        self._save()
        return item

    def set_quantity(self, item_id: str, quantidade: int) -> Optional[Item]:
        item = self.items.get(item_id)
        if not item:
            return None
        item.quantidade = int(quantidade)
        self._save()
        return item

    def set_price(self, item_id: str, preco: float) -> Optional[Item]:
        item = self.items.get(item_id)
        if not item:
            return None
        item.preco = float(preco)
        self._save()
        return item

    def get_item(self, item_id: str) -> Optional[Item]:
        return self.items.get(item_id)

    def search(self, term: str) -> List[Item]:
        term_l = term.lower()
        results = []
        for it in self.items.values():
            if term_l in it.nome.lower() or (it.sku and term_l in it.sku.lower()) or (it.descricao and term_l in it.descricao.lower()):
                results.append(it)
        return results

    def list_items(self) -> List[Item]:
        return list(self.items.values())

    def low_stock(self) -> List[Item]:
        return [it for it in self.items.values() if it.quantidade <= it.estoque_minimo]

    def export_csv(self, path: str) -> None:
        fieldnames = ["id", "nome", "sku", "quantidade", "preco", "estoque_minimo", "local", "descricao"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for it in self.items.values():
                writer.writerow({
                    "id": it.id,
                    "nome": it.nome,
                    "sku": it.sku or "",
                    "quantidade": it.quantidade,
                    "preco": it.preco,
                    "estoque_minimo": it.estoque_minimo,
                    "local": it.local or "",
                    "descricao": it.descricao or ""
                })

    def import_csv(self, path: str, skip_existing_by_sku: bool = True) -> int:
        """Importa itens CSV. Se skip_existing_by_sku=True evitará duplicar SKUs existentes.
        Retorna número de itens adicionados."""
        added = 0
        existing_skus = {it.sku for it in self.items.values() if it.sku}
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row.get("sku") or None
                if skip_existing_by_sku and sku and sku in existing_skus:
                    continue
                try:
                    nome = row.get("nome") or "SEM_NOME"
                    quantidade = int(row.get("quantidade") or 0)
                    preco = float(row.get("preco") or 0.0)
                    estoque_minimo = int(row.get("estoque_minimo") or 0)
                except ValueError:
                    continue
                self.add_item(nome=nome, quantidade=quantidade, preco=preco, sku=sku,
                              estoque_minimo=estoque_minimo,
                              local=row.get("local"), descricao=row.get("descricao"))
                added += 1
        return added


def print_item(it: Item):
    print(f"[{it.id}] {it.nome} | SKU: {it.sku or '-'} | Qtd: {it.quantidade} | Preço: {it.preco:.2f} | Min: {it.estoque_minimo} | Local: {it.local or '-'}")


def main_loop():
    inv = Inventory()
    menu = """
==== Sistema de Estoque ====
Comandos:
 1 - Listar itens
 2 - Adicionar item
 3 - Remover item (por id)
 4 - Atualizar quantidade (entrada/saida)
 5 - Definir quantidade
 6 - Buscar (nome/sku)
 7 - Baixo estoque
 8 - Exportar CSV
 9 - Importar CSV
 0 - Sair
===========================
"""
    while True:
        print(menu)
        opc = input("Escolha uma opção: ").strip()
        if opc == "1":
            itens = inv.list_items()
            if not itens:
                print("Sem itens no estoque.")
            else:
                for it in itens:
                    print_item(it)
        elif opc == "2":
            nome = input("Nome: ").strip()
            sku = input("SKU (opcional): ").strip() or None
            quantidade = input("Quantidade (inteiro): ").strip() or "0"
            preco = input("Preço (ex: 19.90): ").strip() or "0.0"
            estoque_minimo = input("Estoque mínimo (inteiro, opcional): ").strip() or "0"
            local = input("Local (opcional): ").strip() or None
            descricao = input("Descrição (opcional): ").strip() or None
            try:
                item = inv.add_item(nome=nome, quantidade=int(quantidade), preco=float(preco),
                                    sku=sku, estoque_minimo=int(estoque_minimo),
                                    local=local, descricao=descricao)
                print("Item adicionado:")
                print_item(item)
            except ValueError:
                print("Erro: verifique valores numéricos.")
        elif opc == "3":
            item_id = input("ID do item para remover: ").strip()
            if inv.remove_item(item_id):
                print("Removido com sucesso.")
            else:
                print("Item não encontrado.")
        elif opc == "4":
            item_id = input("ID do item: ").strip()
            delta = input("Delta (ex: 5 para entrada, -3 para saída): ").strip()
            try:
                d = int(delta)
                item = inv.update_quantity(item_id, d)
                if item:
                    print("Quantidade atualizada:")
                    print_item(item)
                else:
                    print("Item não encontrado.")
            except ValueError:
                print("Delta inválido.")
        elif opc == "5":
            item_id = input("ID do item: ").strip()
            q = input("Nova quantidade (inteiro): ").strip()
            try:
                n = int(q)
                item = inv.set_quantity(item_id, n)
                if item:
                    print("Quantidade definida:")
                    print_item(item)
                else:
                    print("Item não encontrado.")
            except ValueError:
                print("Quantidade inválida.")
        elif opc == "6":
            term = input("Termo de busca (nome/sku): ").strip()
            res = inv.search(term)
            if not res:
                print("Nenhum item encontrado.")
            else:
                for it in res:
                    print_item(it)
        elif opc == "7":
            low = inv.low_stock()
            if not low:
                print("Nenhum item abaixo do estoque mínimo.")
            else:
                print("Itens abaixo ou igual ao estoque mínimo:")
                for it in low:
                    print_item(it)
        elif opc == "8":
            path = input("Caminho do CSV de saída (ex: export.csv): ").strip() or "export.csv"
            try:
                inv.export_csv(path)
                print(f"Exportado para {path}")
            except Exception as e:
                print("Erro ao exportar:", e)
        elif opc == "9":
            path = input("Caminho do CSV para importar: ").strip()
            if not os.path.exists(path):
                print("Arquivo não encontrado.")
            else:
                added = inv.import_csv(path)
                print(f"Importação finalizada. Itens adicionados: {added}")
        elif opc == "0":
            print("Saindo. Até mais!")
            break
        else:
            print("Opção inválida. Tente novamente.")


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")