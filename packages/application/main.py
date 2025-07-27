# application/main.py
import argparse
import yaml
import logging
from utils.logger import setup_logger

# Importações dos pacotes do projeto
from video_model.models import Project
from timeline_resolver.resolver import Resolver
from video_renderer.renderer import Renderer

def run_pipeline(yaml_path: str, output_path: str, verbose: bool):
    """Orquestra o processo completo de geração de vídeo."""
    setup_logger(verbose)

    logging.info(f"🎬 Iniciando pipeline para '{yaml_path}'...")
    
    try:
        logging.info("1. Carregando e validando o arquivo YAML...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        raw_project = Project.from_dict(data['video'])
        logging.debug("Arquivo YAML carregado para os modelos de dados.")

        logging.info("2. Resolvendo a timeline e expressões dinâmicas...")
        resolver = Resolver(raw_project)
        resolved_project = resolver.resolve()
        logging.debug("Timeline resolvida com sucesso.")

        logging.info(f"3. Renderizando vídeo para '{output_path}'...")
        renderer = Renderer(resolved_project)
        renderer.render_video(output_path)
        
        logging.info(f"✅ Vídeo gerado com sucesso em: {output_path}")

    except Exception as e:
        logging.error(f"❌ Ocorreu um erro fatal no pipeline.", exc_info=True)
        # exc_info=True adiciona o traceback completo ao log do erro.

def main():
    parser = argparse.ArgumentParser(description="Gerador de Vídeo a partir de um arquivo YAML.")
    parser.add_argument("yaml_file", help="Caminho para o arquivo de configuração YAML de entrada.")
    parser.add_argument("-o", "--output", default="output.mp4", help="Caminho para o arquivo de vídeo de saída.")
    # Novo argumento para o modo detalhado
    parser.add_argument("-v", "--verbose", action="store_true", help="Ativa o modo de log detalhado (DEBUG).")
    
    args = parser.parse_args()
    run_pipeline(args.yaml_file, args.output, args.verbose)

if __name__ == "__main__":
    main()
