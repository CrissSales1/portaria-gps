import os
import sys

# Adiciona o diretório da aplicação ao path do Python
INTERP = os.path.expanduser("/home/USUARIO/virtualenv/portariagps/3.8/bin/python")
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Adiciona o diretório da aplicação ao path
sys.path.append(os.getcwd())

# Importa a aplicação Flask
from app import app as application
