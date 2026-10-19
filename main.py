import sys

from conexiones.conexion_postgres import ConexionPostgres
from conexiones.conexion_sqlserver import ConexionSqlServer
from interfaz import iniciar_ui

def main():
    sql_server = ConexionSqlServer()
    postgres = ConexionPostgres()
    sys.exit(iniciar_ui(postgres=postgres, sql_server=sql_server))


if __name__== '__main__':
    main()
