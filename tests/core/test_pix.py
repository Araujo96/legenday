from legenday.core.pix import crc16, payload


def test_crc16_matches_the_standard_check_value():
    assert crc16("123456789") == "29B1"            # valor de conferência do CRC-16/CCITT-FALSE


def test_payload_matches_the_central_bank_example():
    # exemplo do manual do BR Code (Banco Central)
    assert payload("123e4567-e12b-12d1-a456-426655440000", "Fulano de Tal", "BRASILIA") == (
        "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-4266554400005204000053039865802BR"
        "5913Fulano de Tal6008BRASILIA62070503***63041D3D")


def test_name_and_city_lose_accents_and_are_cut_to_the_limit():
    code = payload("a@b.com", "Lucas Araújo da Silva Sauro Junior", "São José dos Campos")
    assert "5925Lucas Araujo da Silva Sau" in code
    assert "6015Sao Jose dos Ca6207" in code
    assert code[-8:-4] == "6304" and code[-4:] == crc16(code[:-4])
