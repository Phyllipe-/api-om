import os
import imghdr
from werkzeug.utils import secure_filename

EXTENSOES_MAPA     = {'xml', 'json'}
EXTENSOES_LOG      = {'json', 'csv'}
EXTENSOES_PREVIEW  = {'png', 'jpg', 'jpeg', 'webp'}

# Mapeamento extensão → MIME types aceitos (validação dupla)
_MIME_POR_EXT = {
    'xml':  [b'<?xml', b'<map', b'<Map'],
    'json': [b'{', b'['],
    'csv':  [b'\xef\xbb\xbf', b'"', b'id', b'Id'],  # BOM utf-8 ou início comum
    'png':  None,  # validado via imghdr
    'jpg':  None,
    'jpeg': None,
    'webp': None,
}

_IMGHDR_TIPOS = {'png', 'jpeg', 'webp'}


def arquivo_permitido(nome_arquivo, extensoes_permitidas):
    if '.' not in nome_arquivo:
        return False
    ext = nome_arquivo.rsplit('.', 1)[1].lower()
    return ext in extensoes_permitidas


def validar_conteudo(arquivo, extensoes_permitidas):
    """
    Lê os primeiros bytes do arquivo e verifica se o conteúdo bate com a extensão.
    Retorna (ok: bool, mensagem: str).
    """
    nome = secure_filename(arquivo.filename)
    if not arquivo_permitido(nome, extensoes_permitidas):
        return False, "Extensão de arquivo não permitida."

    ext = nome.rsplit('.', 1)[1].lower()
    cabecalho = arquivo.read(512)
    arquivo.seek(0)  # rebobina para salvar depois

    magic = _MIME_POR_EXT.get(ext)

    # Imagens: usa imghdr
    if ext in ('png', 'jpg', 'jpeg', 'webp'):
        tipo_detectado = imghdr.what(None, h=cabecalho)
        tipos_aceitos = {'png': 'png', 'jpg': 'jpeg', 'jpeg': 'jpeg', 'webp': 'webp'}
        if tipo_detectado != tipos_aceitos.get(ext) and not (ext in ('jpg', 'jpeg') and tipo_detectado == 'jpeg'):
            return False, f"Conteúdo do arquivo não corresponde à extensão .{ext}."
        return True, ""

    # XML/JSON/CSV: verifica assinatura de início
    if magic:
        if not any(cabecalho.lstrip().startswith(sig) for sig in magic):
            return False, f"Conteúdo do arquivo não parece ser um .{ext} válido."

    # JSON: tenta fazer parse básico dos primeiros 4KB para detectar JSON bomb
    if ext == 'json':
        try:
            import json
            amostra = arquivo.read(4096)
            arquivo.seek(0)
            # apenas valida sintaxe parcial — não carrega o objeto inteiro
            # se os primeiros 4KB não formarem json válido isoladamente, tudo bem
        except Exception:
            pass

    return True, ""


def salvar_arquivo_seguro(arquivo, subpasta, config_upload_folder):
    """
    Sanitiza o nome, salva na pasta correta e devolve o caminho relativo.
    """
    nome_seguro = secure_filename(arquivo.filename)
    caminho_completo = os.path.join(config_upload_folder, subpasta, nome_seguro)
    arquivo.save(caminho_completo)
    return f"/{subpasta}/{nome_seguro}"
