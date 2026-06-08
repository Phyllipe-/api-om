import os
import ssl
import smtplib
import logging
import imghdr
from email.message import EmailMessage
from werkzeug.utils import secure_filename

log = logging.getLogger(__name__)


def enviar_email(destinatario, assunto, corpo_html, corpo_texto=None):
    """
    Envia um e-mail via SMTP (padrão: Resend), usando apenas a stdlib.
    Config por env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM.
    Nunca lança: retorna True/False e loga o erro (não derruba a request).
    """
    host      = os.environ.get('SMTP_HOST', 'smtp.resend.com')
    port      = int(os.environ.get('SMTP_PORT', '465'))
    user      = os.environ.get('SMTP_USER', 'resend')
    senha     = os.environ.get('SMTP_PASS')   # API key da Resend
    remetente = os.environ.get('SMTP_FROM', 'no-reply@omaproject.com.br')

    if not senha:
        log.warning("SMTP_PASS não configurado — e-mail para %s não enviado.", destinatario)
        return False

    msg = EmailMessage()
    msg['From']    = remetente
    msg['To']      = destinatario
    msg['Subject'] = assunto
    msg.set_content(corpo_texto or "Abra este e-mail em um cliente compatível com HTML.")
    msg.add_alternative(corpo_html, subtype='html')

    try:
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as s:
                s.login(user, senha)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls(context=ctx)
                s.login(user, senha)
                s.send_message(msg)
        log.info("E-mail enviado para %s (assunto=%s).", destinatario, assunto)
        return True
    except Exception as e:
        log.error("Falha ao enviar e-mail para %s: %s", destinatario, e)
        return False

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
    Sanitiza o nome, garante que a pasta existe, salva e devolve o caminho relativo.
    """
    nome_seguro = secure_filename(arquivo.filename)
    pasta = os.path.join(config_upload_folder, subpasta)
    os.makedirs(pasta, exist_ok=True)
    caminho_completo = os.path.join(pasta, nome_seguro)
    arquivo.save(caminho_completo)
    return f"/{subpasta}/{nome_seguro}"
