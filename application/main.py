import argparse
import yaml
from video_model.models import Project
from timeline_resolver.resolver import Resolver
from video_renderer.renderer import Renderer

def run_pipeline(yaml_path: str, output_path: str):
    """Orquestra o processo completo de geração de vídeo."""
    print(f"🎬 Iniciando pipeline para '{yaml_path}'...")
    
    try:
        print("1. Carregando e validando o arquivo YAML...")
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        raw_project = Project.from_dict(data['video'])

        print("2. Resolvendo a timeline e expressões dinâmicas...")
        resolver = Resolver(raw_project)
        resolved_project = resolver.resolve()

        print(f"3. Renderizando vídeo para '{output_path}'...")
        renderer = Renderer(resolved_project)
        renderer.render_video(output_path)
        
        print(f"✅ Vídeo gerado com sucesso em: {output_path}")

    except Exception as e:
        print(f"❌ Ocorreu um erro: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de Vídeo a partir de um arquivo YAML.")
    parser.add_argument("yaml_file", help="Caminho para o arquivo de configuração YAML de entrada.")
    parser.add_argument("-o", "--output", default="output.mp4", help="Caminho para o arquivo de vídeo de saída.")
    
    args = parser.parse_args()
    run_pipeline(args.yaml_file, args.output)