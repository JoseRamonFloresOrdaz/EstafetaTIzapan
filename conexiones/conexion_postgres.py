from psycopg2.extensions import connection
from psycopg2.errors import IntegrityError,ProgrammingError,Error
from psycopg2 import connect
from dotenv import load_dotenv
from decimal import Decimal
import os
import json
class ConexionPostgres:
    def __init__(self):
        load_dotenv()
        self.__host = os.getenv('POSTGRES_SERVER')
        self.__port = os.getenv('POSTGRES_PORT')
        self.__dbname = os.getenv('POSTGRES_DBNAME')
        self.__user = os.getenv('POSTGRES_USER')
        self.__password = os.getenv('POSTGRES_PASSWORD')
        self.__cnx = None
        self.__cursor = None

    def crear_conexion(self) -> connection:
        try:
            self.__cnx = connect(
                database=self.__dbname,
                user=self.__user,
                password=self.__password,
                host=self.__host,
                port=self.__port)
            self.__cursor = self.__cnx.cursor()

        except Error as e:
            print('No se puede conectar a la base de datos.')
            print(e)
        return self.__cnx

    def consulta(self,sql:str,parametros:dict|None=None)-> str:
        try:
            if self.__cursor is None:
                if self.crear_conexion() is None:
                    return json.dumps({
                       'estado':False,
                       'mensaje':'No fue posible establecer la conexion'
                   },
                   ensure_ascii = False
                   )
            if parametros:
                self.__cursor.execute(sql,parametros)
            else:
                self.__cursor.execute(sql) 
            tipo = sql.split()[0].strip().upper()
            if tipo == 'SELECT':
                columnas = []
                for columna in self.__cursor.description:
                    columnas.append(columna[0])
                registros = self.__cursor.fetchall()
                resultados = []
                for registro in registros:
                    fila = {}
                    for i,valor in enumerate(registro):
                        if isinstance(valor, Decimal): 
                            fila[columnas[i]] = str(valor)
                        else:
                            fila[columnas[i]] = valor
                    resultados.append(fila)
                return json.dumps({
                    'estado':True,
                    'tipo':'select',
                    'registros': resultados
                })
            elif tipo == "INSERT":
                filas = self.__cursor.rowcount # Obtine el numero de rgistros afectados
                indice = self.__cursor.fetchone()[0]
                self.__cnx.commit() # Comete la transacción
                return json.dumps(
                    {
                    "estado": True,
                    "tipo": "INSERT",
                    'indice':indice,
                    "mensaje": "Registro insertado correctamente",
                    "filas_afectadas": filas
                    },
                    ensure_ascii=False
                    )
            # UPDATE
            elif tipo == "UPDATE":
                filas = self.__cursor.rowcount
                self.__cnx.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "UPDATE",
                        "mensaje": "Registro actualizado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                    )
            # DELETE
            elif tipo == "DELETE":
                filas = self.__cursor.rowcount
                self.__cnx.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": "DELETE",
                        "mensaje": "Registro eliminado correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # OTRAS OPERACIONES
            else:
                filas = self.cursor.rowcount
                self.__cnx.commit()
                return json.dumps(
                    {
                        "estado": True,
                        "tipo": tipo,
                        "mensaje": "Consulta ejecutada correctamente",
                        "filas_afectadas": filas
                    },
                    ensure_ascii=False
                )
            # ERROR DE INTEGRIDAD
        except IntegrityError as e:
            if self.__cnx:
                    self.__cnx.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "IntegrityError",
                    "mensaje": "Violación de integridad en la base de datos",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR DE PROGRAMACIÓN SQL
        except ProgrammingError as e:
            if self.__cnx:
                self.__cnx.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "ProgrammingError",
                    "mensaje": "Error en la consulta SQL",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR GENERAL
        except Error as e:
            if self.__cnx:
                self.__cnx.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "DatabaseError",
                    "mensaje": "Error en la base de datos",
                    "error": str(e)
                },
                ensure_ascii=False
            )
        # ERROR DE PYTHON
        except Exception as e:
            if self.__cnx:
                self.__cnx.rollback()
            return json.dumps(
                {
                    "estado": False,
                    "tipo": "Error",
                    "mensaje": "Error inesperado",
                    "error": str(e)
                },
                ensure_ascii=False
            )
   
        except Error as e:
            print("Error al ejecutar la consulta en la base de datos")
            print(e)
                   
    
    def cerrar_conexion(self) -> bool:
        ban = False
        try:
            if self.__cursor:
                 self.__cursor.close()
                 self.__cursor = None
            if self.__cnx:
                self.__cnx = None
            ban = True
            print("se ha cerrado la conexion")
        except Error as e:
            print("Error al desconectarse de la base de datos")
            print(e)
        return ban

"""
def main():
    con = ConexionPostgres()
    #print(con.crear_conexion())
    #print(con.consulta("INSERT INTO Categoria(id_categoria,nombre) VALUES(%s,%s);",(1,'Alimentos')))
    #print(con.consulta("INSERT INTO Categoria(id_categoria,nombre) VALUES(%s,%s);",(2,'Alimentos')))
    #print(con.consulta("INSERT INTO Categoria(id_categoria,nombre) VALUES(%s,%s);",(3,'Alimentos')))
    #print(con.consulta("INSERT INTO Producto(id_producto,nombre,existencia,descuento,costo,precio) VALUES(%s,%s,%s,%s,%s,%s);",[1,"Jamon de pavo FOD 4KG",20,Decimal('0.0'),Decimal('130.00'),Decimal('130.00')]))
    #print(con.consulta('SELECT * FROM Producto;'))
    #print(con.consulta("SELECT * FROM Categoria;"))
    #print(con.consulta("UPDATE Categoria SET nombre=%s WHERE id_categoria = %s",['Electrodomesticos',2]))
    #print(con.consulta("UPDATE Producto SET precio=%s WHERE id_producto=%s",[Decimal('150.00'),1]))
    #print(con.consulta("DELETE FROM Categoria WHERE id_categoria=%s;",[3]))
    #print(con.consulta('SELECT * FROM Producto;'))
    result = json.loads(con.consulta("SELECT C.company_name, O.order_id,P.product_name ,((OD.unit_price * OD.quantity) - (OD.unit_price * OD.quantity * OD.discount)) AS subtotal from customers C inner join orders O on C.customer_id = O.customer_id inner join order_details OD ON O.order_id = OD.order_id inner join products P on OD.product_id = P.product_id WHERE O.order_id = %(order_id)s;",{"order_id":10248}))
    for r in result['registros']:
        print(r)
    print(con.cerrar_conexion())



if __name__ == '__main__':
    obc = ConexionPostgres()
    print(obc.crear_conexion())
    sql = "INSERT INTO Roles(nombre) VALUES (%(nombre)s) RETURNING idRol;"
    res = json.loads(obc.consulta(sql,{'nombre':'Administrador'}))
    print(res)

"""