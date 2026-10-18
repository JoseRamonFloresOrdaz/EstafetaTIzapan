from conexiones.conexion_postgres import ConexionPostgres
from conexiones.conexion_sqlserver import ConexionSqlServer

def main():
    sql_server = ConexionSqlServer()
    postgres = ConexionPostgres()


if __name__== '__main__':
    main()
