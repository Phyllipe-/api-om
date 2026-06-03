#!/usr/bin/env python3
"""
Script de manutenção: limpa todos os previews 3D do banco de dados.

Uso:
    python limpar_previews_3d.py [--confirmar]

Isso força o ENA a regenerar os previews 3D com nomes únicos na próxima vez
que cada mapa for aberto.
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from app.models import Mapa

def limpar_previews_3d(confirmar=False):
    """
    Remove o campo caminho_render_3d de todos os mapas e deleta os arquivos físicos.
    """
    app = create_app()

    with app.app_context():
        mapas = Mapa.query.all()

        print(f"\n{'='*60}")
        print(f"LIMPEZA DE PREVIEWS 3D")
        print(f"{'='*60}")
        print(f"Total de mapas encontrados: {len(mapas)}\n")

        mapas_com_preview = [m for m in mapas if m.caminho_render_3d]
        print(f"Mapas com preview 3D: {len(mapas_com_preview)}\n")

        if not mapas_com_preview:
            print("Nenhum mapa com preview 3D encontrado. Nada a fazer.")
            return

        print("Mapas que terão preview removido:")
        for m in mapas_com_preview:
            print(f"  - ID {m.id_mapa}: {m.nome_mapa}")
            print(f"    Arquivo: {m.caminho_render_3d}")

        print(f"\n{'='*60}")

        if not confirmar:
            print("\n⚠️  MODO DRY-RUN (simulação)")
            print("Para executar de fato, rode com: --confirmar")
            print("\nO que será feito:")
            print(f"  1. Limpar campo caminho_render_3d de {len(mapas_com_preview)} mapas")
            print(f"  2. Deletar arquivos físicos obsoletos")
            print(f"  3. ENA regerará previews automaticamente ao abrir cada mapa")
            return

        # Confirmação manual
        print("\n⚠️  ATENÇÃO: Esta operação vai:")
        print(f"  1. Limpar caminho_render_3d de {len(mapas_com_preview)} mapas")
        print(f"  2. Deletar arquivos físicos")
        print(f"  3. Forçar regeneração pelo ENA\n")

        resposta = input("Confirma a operação? (sim/não): ").strip().lower()
        if resposta != 'sim':
            print("\n❌ Operação cancelada pelo usuário.")
            return

        # Executar limpeza
        arquivos_deletados = 0
        upload_folder = app.config.get('UPLOAD_FOLDER', '/opt/api-om/uploads')

        for m in mapas_com_preview:
            # Deletar arquivo físico se existir
            if m.caminho_render_3d:
                caminho_completo = os.path.join(upload_folder, m.caminho_render_3d.lstrip('/'))
                if os.path.exists(caminho_completo):
                    try:
                        os.remove(caminho_completo)
                        arquivos_deletados += 1
                        print(f"  ✓ Deletado: {caminho_completo}")
                    except Exception as e:
                        print(f"  ✗ Erro ao deletar {caminho_completo}: {e}")

            # Limpar campo no banco
            m.caminho_render_3d = None

        # Commit das alterações
        db.session.commit()

        print(f"\n{'='*60}")
        print(f"✅ LIMPEZA CONCLUÍDA")
        print(f"{'='*60}")
        print(f"Mapas atualizados: {len(mapas_com_preview)}")
        print(f"Arquivos deletados: {arquivos_deletados}")
        print(f"\nPróximos passos:")
        print(f"  1. Abra cada mapa no ENA")
        print(f"  2. ENA gerará e enviará novo preview 3D automaticamente")
        print(f"  3. Cada mapa terá seu próprio arquivo: render3d_mapa_{{id}}.png")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    confirmar = '--confirmar' in sys.argv
    limpar_previews_3d(confirmar)
