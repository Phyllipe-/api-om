#!/usr/bin/env python3
"""
Script de manutenção: normaliza códigos nos XMLs dos mapas existentes.

Adiciona ".0" em códigos que não têm ponto decimal, corrigindo o mismatch
entre e3-react e ENA que causava objetos aparecerem trocados.

Uso:
    python normalizar_codigos_mapas.py [--confirmar]
"""

import sys
import os
import re
from xml.etree import ElementTree as ET

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.models import Mapa


def normalizar_codigo(codigo):
    """
    Normaliza um código adicionando .0 se não tiver ponto decimal.

    Exemplos:
        "2" -> "2.0"
        "2.0" -> "2.0"
        "-1" -> "-1"
    """
    codigo = codigo.strip()
    if codigo == "-1" or not codigo:
        return codigo

    if '.' not in codigo:
        return f"{codigo}.0"

    return codigo


def normalizar_layer_xml(layer_text):
    """
    Normaliza todos os códigos em um layer XML.

    Args:
        layer_text: String com os códigos separados por vírgula

    Returns:
        String com códigos normalizados
    """
    # Remove espaços em branco e quebras de linha
    layer_text = layer_text.strip()

    # Separa por vírgula
    codigos = layer_text.split(',')

    # Normaliza cada código
    codigos_normalizados = [normalizar_codigo(c) for c in codigos]

    # Junta de volta
    return ','.join(codigos_normalizados)


def processar_xml(caminho_arquivo):
    """
    Processa um arquivo XML normalizando todos os códigos.

    Args:
        caminho_arquivo: Caminho completo do arquivo XML

    Returns:
        Tuple (foi_modificado: bool, novo_conteudo: str)
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            conteudo_original = f.read()

        # Parse XML
        # Remove namespace para facilitar parsing
        conteudo_sem_ns = conteudo_original.replace('xmlns="http://www.w3.org/1999/xhtml"', '')
        root = ET.fromstring(conteudo_sem_ns)

        # Encontra todos os layers
        layers = root.findall('.//layer')

        modificado = False
        for layer in layers:
            conteudo_original_layer = layer.text
            if conteudo_original_layer:
                conteudo_normalizado = normalizar_layer_xml(conteudo_original_layer)

                if conteudo_normalizado != conteudo_original_layer.strip().replace('\n', '').replace(' ', ''):
                    modificado = True

                layer.text = f"\n            {conteudo_normalizado}\n        "

        if modificado:
            # Gera novo XML
            novo_xml = ET.tostring(root, encoding='unicode')

            # Adiciona namespace de volta
            novo_xml = novo_xml.replace('<root>', '<root xmlns="http://www.w3.org/1999/xhtml">')

            # Formata melhor (adiciona quebras de linha)
            novo_xml = novo_xml.replace('><', '>\n<')

            return True, novo_xml

        return False, conteudo_original

    except Exception as e:
        print(f"  ✗ Erro ao processar XML: {e}")
        return False, None


def normalizar_mapas(confirmar=False):
    """
    Normaliza códigos nos XMLs de todos os mapas.
    """
    app = create_app()

    with app.app_context():
        mapas = Mapa.query.all()

        print(f"\n{'='*60}")
        print(f"NORMALIZAÇÃO DE CÓDIGOS NOS MAPAS")
        print(f"{'='*60}")
        print(f"Total de mapas encontrados: {len(mapas)}\n")

        if not mapas:
            print("Nenhum mapa encontrado. Nada a fazer.")
            return

        upload_folder = app.config.get('UPLOAD_FOLDER', '/opt/api-om/uploads')

        mapas_processados = []
        mapas_com_erro = []

        # Primeiro, analisa todos os mapas
        for mapa in mapas:
            caminho_completo = os.path.join(upload_folder, mapa.caminho_arquivo_xml.lstrip('/'))

            if not os.path.exists(caminho_completo):
                print(f"⚠  Mapa {mapa.id_mapa} ({mapa.nome_mapa}): XML não encontrado")
                mapas_com_erro.append(mapa)
                continue

            modificado, novo_conteudo = processar_xml(caminho_completo)

            if modificado:
                mapas_processados.append({
                    'mapa': mapa,
                    'caminho': caminho_completo,
                    'novo_conteudo': novo_conteudo
                })
                print(f"✓  Mapa {mapa.id_mapa} ({mapa.nome_mapa}): códigos serão normalizados")
            else:
                print(f"→  Mapa {mapa.id_mapa} ({mapa.nome_mapa}): já normalizado, nenhuma mudança")

        print(f"\n{'='*60}")
        print(f"Mapas a processar: {len(mapas_processados)}")
        print(f"Mapas já normalizados: {len(mapas) - len(mapas_processados) - len(mapas_com_erro)}")
        print(f"Mapas com erro: {len(mapas_com_erro)}")
        print(f"{'='*60}\n")

        if not mapas_processados:
            print("Nenhum mapa precisa de normalização. Todos já estão corretos.")
            return

        if not confirmar:
            print("⚠️  MODO DRY-RUN (simulação)")
            print("Para executar de fato, rode com: --confirmar")
            print("\nO que será feito:")
            print(f"  1. Normalizar códigos em {len(mapas_processados)} mapas")
            print(f"  2. Backup dos XMLs originais (extensão .bak)")
            print(f"  3. Salvar XMLs normalizados")
            print(f"  4. Objetos aparecerão corretos no ENA ao abrir os mapas")
            return

        # Confirmação manual
        print("⚠️  ATENÇÃO: Esta operação vai:")
        print(f"  1. Criar backup dos XMLs originais (.bak)")
        print(f"  2. Normalizar códigos em {len(mapas_processados)} mapas")
        print(f"  3. Sobrescrever os arquivos XML\n")

        resposta = input("Confirma a operação? (sim/não): ").strip().lower()
        if resposta != 'sim':
            print("\n❌ Operação cancelada pelo usuário.")
            return

        # Executar normalização
        sucesso = 0
        falhas = 0

        for item in mapas_processados:
            mapa = item['mapa']
            caminho = item['caminho']
            novo_conteudo = item['novo_conteudo']

            try:
                # Backup do arquivo original
                caminho_backup = f"{caminho}.bak"
                with open(caminho, 'r', encoding='utf-8') as f:
                    conteudo_original = f.read()
                with open(caminho_backup, 'w', encoding='utf-8') as f:
                    f.write(conteudo_original)

                # Salva novo conteúdo
                with open(caminho, 'w', encoding='utf-8') as f:
                    f.write(novo_conteudo)

                sucesso += 1
                print(f"  ✓ Mapa {mapa.id_mapa} ({mapa.nome_mapa}): normalizado com sucesso")

            except Exception as e:
                falhas += 1
                print(f"  ✗ Mapa {mapa.id_mapa} ({mapa.nome_mapa}): erro ao salvar - {e}")

        print(f"\n{'='*60}")
        print(f"✅ NORMALIZAÇÃO CONCLUÍDA")
        print(f"{'='*60}")
        print(f"Mapas processados com sucesso: {sucesso}")
        print(f"Mapas com erro: {falhas}")
        print(f"\nPróximos passos:")
        print(f"  1. Abra os mapas no ENA")
        print(f"  2. Os objetos agora aparecerão corretamente")
        print(f"  3. Backups salvos em *.xml.bak (pode deletar depois de confirmar)")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    confirmar = '--confirmar' in sys.argv
    normalizar_mapas(confirmar)
