"""Bounded, deterministic CSV parsing with no database or filesystem access."""
import csv
import io
import re

from app.schemas.order_imports import ImportIssue, ParsedOrder, ParsedOrderFile, ParsedOrderItem

MAX_BYTES = 1024 * 1024
HEADER = ['external_order_id', 'sku', 'quantity']
# A field may contain whitespace up to the content limit; csv's default is 128 KiB.
csv.field_size_limit(max(csv.field_size_limit(), MAX_BYTES))


class OrderImportFormatError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def parse_order_csv(content: bytes) -> ParsedOrderFile:
    if len(content) > MAX_BYTES:
        raise OrderImportFormatError('file_too_large', 'O arquivo excede 1 MiB.')
    try:
        decoded = content.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise OrderImportFormatError('invalid_encoding', 'Use um arquivo UTF-8.') from error
    reader = csv.reader(io.StringIO(decoded, newline=''), strict=True)
    result = ParsedOrderFile()
    groups: dict[str, ParsedOrder] = {}
    seen: dict[str, set[str]] = {}
    try:
        if next(reader, None) != HEADER:
            raise OrderImportFormatError('invalid_header', 'Cabeçalho esperado: external_order_id,sku,quantity.')
        previous_line = reader.line_num
        row_count = 0
        for row_count, row in enumerate(reader, 1):
            row_number = previous_line + 1
            previous_line = reader.line_num
            if row_count > 500:
                raise OrderImportFormatError('too_many_rows', 'Use no máximo 500 linhas de dados.')
            if not row:
                row = ['', '', '']
            if len(row) != 3:
                raise OrderImportFormatError('invalid_columns', 'Cada linha deve conter três colunas.')
            external_id, sku, raw_quantity = [value.strip() for value in row]
            if not external_id or len(external_id) > 80 or '\x00' in external_id:
                result.unassigned_errors.append(ImportIssue(row=row_number, field='external_order_id',
                    code='invalid_external_order_id', message='Referência deve ter de 1 a 80 caracteres.'))
                continue
            if external_id not in groups:
                if len(groups) >= 100:
                    raise OrderImportFormatError('too_many_orders', 'Use no máximo 100 pedidos.')
                groups[external_id] = ParsedOrder(external_order_id=external_id)
                seen[external_id] = set()
            order = groups[external_id]
            order.source_lines.append(row_number)
            if len(order.source_lines) > 200:
                raise OrderImportFormatError('too_many_items', 'Use no máximo 200 itens por pedido.')
            if not sku or len(sku) > 80 or '\x00' in sku:
                order.errors.append(ImportIssue(row=row_number, field='sku', code='invalid_sku',
                    message='SKU deve ter de 1 a 80 caracteres.'))
            elif sku in seen[external_id]:
                order.errors.append(ImportIssue(row=row_number, field='sku', code='duplicate_sku',
                    message='SKU repetido no mesmo pedido.'))
            seen[external_id].add(sku)
            normalized_quantity = raw_quantity.lstrip('0') or '0'
            if not re.fullmatch(r'[0-9]+', raw_quantity) or len(normalized_quantity) > 7 or not 1 <= int(normalized_quantity) <= 1_000_000:
                order.errors.append(ImportIssue(row=row_number, field='quantity', code='invalid_quantity',
                    message='Quantidade deve ser um inteiro de 1 a 1000000.'))
                quantity = 0
            else:
                quantity = int(normalized_quantity)
            # Preserve every normalized row even when the whole order is invalid.
            order.items.append(ParsedOrderItem(sku=sku, quantity=quantity))
        if row_count == 0:
            raise OrderImportFormatError('empty_file', 'O arquivo não contém pedidos.')
    except csv.Error as error:
        raise OrderImportFormatError('invalid_csv', 'Estrutura CSV inválida.') from error
    result.orders = list(groups.values())
    return result
