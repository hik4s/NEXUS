import pytest

from app.services.order_import_parser import OrderImportFormatError, parse_order_csv

HEADER = b'external_order_id,sku,quantity\n'


def test_bom_grouping_trim_and_case_sensitive_identity():
    parsed = parse_order_csv(b'\xef\xbb\xbf' + HEADER + b' A , SKU ,2\nA,sku,1\na,SKU,3\n')
    assert [o.external_order_id for o in parsed.orders] == ['A', 'a']
    assert [i.sku for i in parsed.orders[0].items] == ['SKU', 'sku']
    assert parsed.orders[0].source_lines == [2, 3]
    assert not parsed.orders[0].errors


@pytest.mark.parametrize('content', [b'', b'\xff', b'a,b,c\n', HEADER + b'A,SKU,1,extra\n',
    b'external_order_id,sku,sku\n', b'external_order_id,sku\n',
    b'external_order_id,sku,quantity,price\n', HEADER + b'A,"unterminated,1\n'])
def test_structural_errors_reject_whole_file(content):
    with pytest.raises(OrderImportFormatError):
        parse_order_csv(content)


@pytest.mark.parametrize('quantity', ['0', '-1', '1.5', '1000001', 'NaN', '١', ''])
def test_bad_quantity_invalidates_the_whole_group(quantity):
    result = parse_order_csv(HEADER + f'A,SKU-1,1\nA,SKU-2,{quantity}\nB,SKU-3,1\n'.encode())
    assert result.orders[0].errors[0].code == 'invalid_quantity'
    assert not result.orders[1].errors


def test_duplicates_and_unassigned_errors():
    parsed = parse_order_csv(HEADER + b'A,SKU,1\nA,SKU,2\n,SKU,1\n')
    assert parsed.orders[0].errors[0].code == 'duplicate_sku'
    assert parsed.unassigned_errors[0].row == 4
    assert parsed.unassigned_errors[0].field == 'external_order_id'


def test_exact_byte_limit():
    prefix = HEADER + b'A,SKU,"'
    content = prefix + b' ' * (1048576 - len(prefix) - 3) + b'1"\n'
    assert len(content) == 1048576
    assert parse_order_csv(content).orders[0].items[0].quantity == 1
    with pytest.raises(OrderImportFormatError) as error:
        parse_order_csv(content + b'\n')
    assert error.value.code == 'file_too_large'


@pytest.mark.parametrize('count,accepted', [(500, True), (501, False)])
def test_row_limit(count, accepted):
    content = HEADER + b''.join(f'O{i//5},SKU{i},1\n'.encode() for i in range(count))
    if accepted:
        assert len(parse_order_csv(content).orders) == 100
    else:
        with pytest.raises(OrderImportFormatError):
            parse_order_csv(content)


@pytest.mark.parametrize('count,accepted', [(100, True), (101, False)])
def test_order_limit(count, accepted):
    content = HEADER + b''.join(f'O{i},SKU,1\n'.encode() for i in range(count))
    if accepted:
        assert len(parse_order_csv(content).orders) == count
    else:
        with pytest.raises(OrderImportFormatError):
            parse_order_csv(content)


@pytest.mark.parametrize('count,accepted', [(200, True), (201, False)])
def test_item_limit(count, accepted):
    content = HEADER + b''.join(f'O,SKU{i},1000000\n'.encode() for i in range(count))
    if accepted:
        assert len(parse_order_csv(content).orders[0].items) == count
    else:
        with pytest.raises(OrderImportFormatError):
            parse_order_csv(content)


@pytest.mark.parametrize('row', ['X'*81 + ',SKU,1', 'A,' + 'X'*81 + ',1'])
def test_names_are_never_truncated(row):
    parsed = parse_order_csv(HEADER + (row + '\n').encode())
    assert parsed.unassigned_errors or parsed.orders[0].errors
