import os
from werkzeug.utils import secure_filename

# Dizemos exatamente o que é permitido entrar
EXTENSOES_MAPA = {'xml', 'json'}
EXTENSOES_LOG = {'json', 'csv'}

def arquivo_permitido(nome_arquivo, extensoes_permitidas):
    """Verifica se o ficheiro tem extensão e se ela está na lista de permitidas."""
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in extensoes_permitidas

def salvar_arquivo_seguro(arquivo, subpasta, config_upload_folder):
    """
    Limpa o nome do ficheiro (tira espaços e caracteres perigosos), 
    salva na pasta correta e devolve o caminho relativo.
    """
    # secure_filename transforma "Meu Mapa@!.xml" em "Meu_Mapa.xml"
    nome_seguro = secure_filename(arquivo.filename)
    
    # Cria o caminho completo: ex: C:/api-om/uploads/mapas/Meu_Mapa.xml
    caminho_completo = os.path.join(config_upload_folder, subpasta, nome_seguro)
    
    # Salva fisicamente o arquivo no disco
    arquivo.save(caminho_completo)
    
    # Devolve o caminho "limpo" que vai ser gravado no banco de dados
    return f"/{subpasta}/{nome_seguro}"