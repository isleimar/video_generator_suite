import logging
import sys

def setup_logger(verbose: bool = False):
    """Configura o logger raiz para o projeto."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Define o formato da mensagem
    log_format = logging.Formatter('[%(levelname)s] %(message)s')
    
    # Configura um manipulador que imprime no console
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(log_format)
    
    # Pega o logger raiz e aplica as configurações
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Evita adicionar manipuladores duplicados se a função for chamada mais de uma vez
    if not root_logger.handlers:
        root_logger.addHandler(handler)