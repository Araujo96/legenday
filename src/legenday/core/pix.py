"""Código PIX "copia e cola" (BR Code estático do Banco Central), o mesmo texto que vai dentro do QR Code.

Formato EMV: cada campo é ID (2 dígitos) + tamanho (2 dígitos) + valor; no fim vai um CRC16 de conferência.
Sem valor fixo: quem doa escolhe quanto, no app do banco.
"""
import unicodedata


def _field(fid: str, value: str) -> str:
    return f"{fid}{len(value):02d}{value}"


def _plain(text: str, limit: int) -> str:
    """Nome e cidade vão sem acento e com tamanho máximo, como pede a especificação."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return text.strip()[:limit]


def crc16(data: str) -> str:
    """CRC16-CCITT-FALSE (polinômio 0x1021, início 0xFFFF), em 4 dígitos hexadecimais maiúsculos."""
    crc = 0xFFFF
    for byte in data.encode():
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def payload(key: str, name: str, city: str, txid: str = "***") -> str:
    """Texto do PIX para a chave `key` (e-mail, celular +55..., CPF/CNPJ ou chave aleatória)."""
    account = _field("00", "br.gov.bcb.pix") + _field("01", key.strip())
    body = (_field("00", "01")                     # versão do formato
            + _field("26", account)               # conta PIX do recebedor
            + _field("52", "0000")                # categoria: não informada
            + _field("53", "986")                 # moeda: real
            + _field("58", "BR")
            + _field("59", _plain(name, 25))
            + _field("60", _plain(city, 15))
            + _field("62", _field("05", txid))    # identificador ("***" = sem identificador)
            + "6304")                             # o próprio campo do CRC entra na conta
    return body + crc16(body)
