import hashlib
import hmac
import json
import secrets
from abc import ABC, abstractmethod
from modelos import *
from typing import Any, Callable, List, Optional, Union


# ============================================================
#                       DIALECTOS SQL
# ============================================================
class IDialectoSql(ABC):
    @abstractmethod
    def retornar_id(self, sql: str, nombre_id: str) -> str:
        """Modifica un INSERT para que devuelva el id generado."""


class DialectoPostgres(IDialectoSql):
    def retornar_id(self, sql: str, nombre_id: str) -> str:
        return f"{sql} RETURNING {nombre_id};"


class DialectoSqlServer(IDialectoSql):
    def retornar_id(self, sql: str, nombre_id: str) -> str:
        return sql.replace("VALUES", f"OUTPUT INSERTED.{nombre_id} VALUES", 1)


# ============================================================
#                    REPOSITORIO BASE (CRUD)
# ============================================================
class RepositorioError(Exception):
    """Error al ejecutar una operacion en la base de datos."""


def _num(valor: Any) -> Optional[float]:
    return float(valor) if valor is not None else None


class RepositorioBase:
    TABLA: str = ""
    COL_ID: str = ""
    COLUMNAS: tuple = ()      # columnas insertables/actualizables (sin el id)
    _PREFIJO: str = ""        # alias de tabla cuando el SELECT usa JOIN

    def __init__(self, conexion, dialecto: IDialectoSql):
        self._db = conexion
        self._dialecto = dialecto

    # ---------- a implementar en cada repositorio ----------
    def _params(self, entidad) -> dict:
        raise NotImplementedError

    def _mapear(self, fila: dict):
        """fila llega con las llaves en minusculas."""
        raise NotImplementedError

    # ---------- utilidades internas ----------
    def _ejecutar(self, sql: str, params: Optional[dict] = None) -> dict:
        crudo = self._db.consulta(sql, params) if params is not None else self._db.consulta(sql)
        res = json.loads(crudo)
        if not res.get('estado'):
            detalle = res.get('error') or res.get('mensaje')
            raise RepositorioError(f"Error en la base de datos ({self.TABLA}): {detalle}")
        return res

    def _consulta(self, condicion: str = "") -> str:
        return f"SELECT * FROM {self.TABLA} {condicion};"

    def _filas(self, condicion: str = "", params: Optional[dict] = None) -> list:
        res = self._ejecutar(self._consulta(condicion), params)
        return [
            self._mapear({k.lower(): v for k, v in fila.items()})
            for fila in res['registros']
        ]

    def _obtener_por(self, columna: str, valor: Any) -> list:
        return self._filas(f"WHERE {self._PREFIJO}{columna}=%(valor)s", {'valor': valor})

    # ---------- CRUD ----------
    def crear(self, entidad):
        columnas = ", ".join(self.COLUMNAS)
        marcas = ", ".join(f"%({c})s" for c in self.COLUMNAS)
        sql = self._dialecto.retornar_id(
            f"INSERT INTO {self.TABLA}({columnas}) VALUES ({marcas})", self.COL_ID
        )
        res = self._ejecutar(sql, self._params(entidad))
        setattr(entidad, self.COL_ID, res['indice'])
        return entidad

    def obtener_todos(self) -> list:
        return self._filas()

    def obtener_por_id(self, id_: int):
        filas = self._filas(f"WHERE {self._PREFIJO}{self.COL_ID}=%(id)s", {'id': id_})
        return filas[0] if filas else None

    def actualizar(self, entidad):
        asignaciones = ", ".join(f"{c}=%({c})s" for c in self.COLUMNAS)
        params = self._params(entidad)
        id_ = getattr(entidad, self.COL_ID)
        params['id'] = id_
        sql = f"UPDATE {self.TABLA} SET {asignaciones} WHERE {self.COL_ID}=%(id)s;"
        self._ejecutar(sql, params)
        return self.obtener_por_id(id_)

    def eliminar(self, id_: int) -> bool:
        self._ejecutar(f"DELETE FROM {self.TABLA} WHERE {self.COL_ID}=%(id)s;", {'id': id_})
        return True


# ============================================================
#              PERMISOS Y AUTENTICACION
# ============================================================
class RolSQL(RepositorioBase):
    TABLA = "Roles"
    COL_ID = "idRol"
    COLUMNAS = ("nombre", "activo")

    def _params(self, e: Rol):
        return {'nombre': e.nombre, 'activo': e.activo}

    def _mapear(self, f):
        return Rol(f['idrol'], f['nombre'], f['activo'])

    def obtener_por_nombre(self, nombre: str) -> Optional[Rol]:
        r = self._obtener_por("nombre", nombre)
        return r[0] if r else None


class PermisoSQL(RepositorioBase):
    TABLA = "Permisos"
    COL_ID = "idPermiso"
    COLUMNAS = ("nombre", "activo")

    def _params(self, e: Permiso):
        return {'nombre': e.nombre, 'activo': e.activo}

    def _mapear(self, f):
        return Permiso(f['idpermiso'], f['nombre'], f['activo'])

    def obtener_por_nombre(self, nombre: str) -> Optional[Permiso]:
        r = self._obtener_por("nombre", nombre)
        return r[0] if r else None


class RolPermisoSQL(RepositorioBase):
    TABLA = "RolesPermisos"
    COL_ID = "idRolPermiso"
    COLUMNAS = ("idRol", "idPermiso")

    def _params(self, e: RolPermiso):
        return {'idRol': e.idRol, 'idPermiso': e.idPermiso}

    def _mapear(self, f):
        return RolPermiso(f['idrolpermiso'], f['idrol'], f['idpermiso'])

    def obtener_por_rol(self, idRol: int) -> List[RolPermiso]:
        return self._obtener_por("idRol", idRol)

    def obtener_por_permiso(self, idPermiso: int) -> List[RolPermiso]:
        return self._obtener_por("idPermiso", idPermiso)


class DispositivoSQL(RepositorioBase):
    TABLA = "Dispositivos"
    COL_ID = "idDispositivo"
    COLUMNAS = ("nombreDispositivo", "direccionMac", "tipoDispositivo", "activo")

    def _params(self, e: Dispositivo):
        return {
            'nombreDispositivo': e.nombreDispositivo,
            'direccionMac': e.direccionMac,
            'tipoDispositivo': e.tipoDispositivo,
            'activo': e.activo,
        }

    def _mapear(self, f):
        return Dispositivo(
            f['iddispositivo'], f['nombredispositivo'], f['direccionmac'],
            f['tipodispositivo'], f['activo']
        )

    def obtener_por_mac(self, direccionMac: str) -> Optional[Dispositivo]:
        r = self._obtener_por("direccionMac", direccionMac)
        return r[0] if r else None


class UsuarioSQL(RepositorioBase):
    TABLA = "Usuarios"
    COL_ID = "idUsuario"
    COLUMNAS = ("idRol", "nombre", "apellido", "correo", "contraseña", "activo")
    _PREFIJO = "u."

    def _consulta(self, condicion: str = "") -> str:
        return f"""
            SELECT
                u.idusuario,
                u.nombre,
                u.apellido,
                u.correo,
                u.contraseña,
                u.activo AS usuario_activo,
                r.idrol AS rol_id,
                r.nombre AS rol_nombre,
                r.activo AS rol_activo
            FROM Usuarios u
            INNER JOIN Roles r ON u.idrol = r.idrol {condicion};
        """

    def _params(self, e: Usuario):
        return {
            'idRol': e.rol.idRol,
            'nombre': e.nombre,
            'apellido': e.apellido,
            'correo': e.correo,
            'contraseña': e.contraseña,
            'activo': e.activo,
        }

    def _mapear(self, f):
        rol = Rol(f['rol_id'], f['rol_nombre'], f['rol_activo'])
        return Usuario(
            idUsuario=f['idusuario'],
            nombre=f['nombre'],
            apellido=f['apellido'],
            correo=f['correo'],
            rol=rol,
            contraseña=f['contraseña'],
            activo=f['usuario_activo'],
        )

    def obtener_por_correo(self, correo: str) -> Optional[Usuario]:
        r = self._obtener_por("correo", correo)
        return r[0] if r else None


class SesionSQL(RepositorioBase):
    TABLA = "Sesiones"
    COL_ID = "idSesion"
    COLUMNAS = ("idUsuario", "idDispositivo", "horaInicio", "horaFin", "fecha", "activa")

    def _params(self, e: Sesion):
        return {
            'idUsuario': e.idUsuario,
            'idDispositivo': e.idDispositivo,
            'horaInicio': e.horaInicio,
            'horaFin': e.horaFin,
            'fecha': e.fecha,
            'activa': e.activa,
        }

    def _mapear(self, f):
        return Sesion(
            f['idsesion'], f['idusuario'], f['iddispositivo'],
            f['horainicio'], f['horafin'], f['fecha'], f['activa']
        )

    def obtener_por_usuario(self, idUsuario: int) -> List[Sesion]:
        return self._obtener_por("idUsuario", idUsuario)

    def obtener_activas_por_usuario(self, idUsuario: int) -> List[Sesion]:
        return self._filas(
            "WHERE idUsuario=%(idUsuario)s AND activa=TRUE", {'idUsuario': idUsuario}
        )


# ============================================================
#                          ENCARGOS
# ============================================================
class ServicioSQL(RepositorioBase):
    TABLA = "Servicios"
    COL_ID = "idServicio"
    COLUMNAS = ("nombre", "descripcion", "activo", "precio")

    def _params(self, e: Servicio):
        return {
            'nombre': e.nombre,
            'descripcion': e.descripcion,
            'activo': e.activo,
            'precio': e.precio,
        }

    def _mapear(self, f):
        return Servicio(
            f['idservicio'], f['nombre'], f['descripcion'], _num(f['precio']), f['activo']
        )

    def obtener_activos(self) -> List[Servicio]:
        return self._filas("WHERE activo=TRUE")


class ClienteSQL(RepositorioBase):
    TABLA = "Clientes"
    COL_ID = "idCliente"
    COLUMNAS = ("nombre", "apellido", "telefono")

    def _params(self, e: Cliente):
        return {'nombre': e.nombre, 'apellido': e.apellido, 'telefono': e.telefono}

    def _mapear(self, f):
        return Cliente(f['idcliente'], f['nombre'], f['apellido'], f['telefono'])

    def obtener_por_telefono(self, telefono: str) -> Optional[Cliente]:
        r = self._obtener_por("telefono", telefono)
        return r[0] if r else None


class EncargoSQL(RepositorioBase):
    TABLA = "Encargos"
    COL_ID = "idEncargo"
    COLUMNAS = ("idCliente", "idSesion", "fecha", "subtotal", "descuento", "total", "pagado")

    def _params(self, e: Encargo):
        return {
            'idCliente': e.idCliente,
            'idSesion': e.idSesion,
            'fecha': e.fecha,
            'subtotal': e.subtotal,
            'descuento': e.descuento,
            'total': e.total,
            'pagado': e.pagado,
        }

    def _mapear(self, f):
        return Encargo(
            f['idencargo'], f['idcliente'], f['idsesion'], f['fecha'],
            _num(f['subtotal']), _num(f['descuento']), _num(f['total']), f['pagado']
        )

    def obtener_por_cliente(self, idCliente: int) -> List[Encargo]:
        return self._obtener_por("idCliente", idCliente)

    def obtener_por_sesion(self, idSesion: int) -> List[Encargo]:
        return self._obtener_por("idSesion", idSesion)

    def obtener_pendientes_de_pago(self) -> List[Encargo]:
        return self._filas("WHERE pagado=FALSE")


class ServicioEncargoSQL(RepositorioBase):
    TABLA = "ServiciosEncargos"
    COL_ID = "idServicioEncargo"
    COLUMNAS = ("idServicio", "idEncargo", "subtotal")

    def _params(self, e: ServicioEncargo):
        return {'idServicio': e.idServicio, 'idEncargo': e.idEncargo, 'subtotal': e.subtotal}

    def _mapear(self, f):
        return ServicioEncargo(
            f['idservicioencargo'], f['idservicio'], f['idencargo'], _num(f['subtotal'])
        )

    def obtener_por_encargo(self, idEncargo: int) -> List[ServicioEncargo]:
        return self._obtener_por("idEncargo", idEncargo)


class MaterialSQL(RepositorioBase):
    TABLA = "Materiales"
    COL_ID = "idMaterial"
    COLUMNAS = ("idServicioEncargo", "RutaImagenReferencia", "fechaIngreso", "fechaSalida", "entregado")

    def _params(self, e: Material):
        return {
            'idServicioEncargo': e.idServicioEncargo,
            'RutaImagenReferencia': e.rutaImagenReferencia,
            'fechaIngreso': e.fechaIngreso,
            'fechaSalida': e.fechaSalida,
            'entregado': e.entregado,
        }

    def _mapear(self, f):
        return Material(
            f['idmaterial'], f['idservicioencargo'], f['rutaimagenreferencia'],
            f['fechaingreso'], f['fechasalida'], f['entregado']
        )

    def obtener_por_servicio_encargo(self, idServicioEncargo: int) -> List[Material]:
        return self._obtener_por("idServicioEncargo", idServicioEncargo)

    def obtener_no_entregados(self) -> List[Material]:
        return self._filas("WHERE entregado=FALSE")


# ============================================================
#                         PAQUETERIA
# ============================================================
class DireccionSQL(RepositorioBase):
    TABLA = "Direcciones"
    COL_ID = "idDireccion"
    COLUMNAS = (
        "nombreCompleto", "calle", "numero_exterior", "numero_interior",
        "ciudad", "CP", "telefono",
    )

    def _params(self, e: Direccion):
        return {
            'nombreCompleto': e.nombreCompleto,
            'calle': e.calle,
            'numero_exterior': e.numero_exterior,
            'numero_interior': e.numero_interior,
            'ciudad': e.ciudad,
            'CP': e.cp,
            'telefono': e.telefono,
        }

    def _mapear(self, f):
        return Direccion(
            f['iddireccion'], f['nombrecompleto'], f['calle'], f['numero_exterior'],
            f['numero_interior'], f['ciudad'], f['cp'], f['telefono']
        )

    def obtener_por_telefono(self, telefono: str) -> Optional[Direccion]:
        r = self._obtener_por("telefono", telefono)
        return r[0] if r else None


class PaqueteSQL(RepositorioBase):
    TABLA = "Paquetes"
    COL_ID = "idPaquete"
    COLUMNAS = ("idDireccionRemitente", "idDireccionDestinatario", "codigoRastreo", "fecha")

    def _params(self, e: Paquete):
        return {
            'idDireccionRemitente': e.idDireccionRemitente,
            'idDireccionDestinatario': e.idDireccionDestinatario,
            'codigoRastreo': e.codigoRastreo,
            'fecha': e.fecha,
        }

    def _mapear(self, f):
        return Paquete(
            f['idpaquete'], f['iddireccionremitente'], f['iddirecciondestinatario'],
            f['codigorastreo'], f['fecha']
        )

    def obtener_por_codigo_rastreo(self, codigo: str) -> Optional[Paquete]:
        r = self._obtener_por("codigoRastreo", codigo)
        return r[0] if r else None


class SalidaPaqueteSQL(RepositorioBase):
    TABLA = "SalidasPaquetes"
    COL_ID = "idSalidaPaquete"
    COLUMNAS = ("idPaquete", "idSesion", "fechaEntrada", "fechaRecoleccion")

    def _params(self, e: SalidaPaquete):
        return {
            'idPaquete': e.idPaquete,
            'idSesion': e.idSesion,
            'fechaEntrada': e.fechaEntrada,
            'fechaRecoleccion': e.fechaRecoleccion,
        }

    def _mapear(self, f):
        return SalidaPaquete(
            f['idsalidapaquete'], f['idpaquete'], f['idsesion'],
            f['fechaentrada'], f['fecharecoleccion']
        )

    def obtener_por_paquete(self, idPaquete: int) -> List[SalidaPaquete]:
        return self._obtener_por("idPaquete", idPaquete)

    def obtener_pendientes_de_recoleccion(self) -> List[SalidaPaquete]:
        return self._filas("WHERE fechaRecoleccion IS NULL")


class EntradaPaqueteSQL(RepositorioBase):
    TABLA = "EntradasPaquetes"
    COL_ID = "idEntradaPaquete"
    COLUMNAS = ("idPaquete", "idSesion", "fechaLlegada", "fechaRecogido", "estado", "rutaImagenFirma")

    def _params(self, e: EntradaPaquete):
        return {
            'idPaquete': e.idPaquete,
            'idSesion': e.idSesion,
            'fechaLlegada': e.fechaLlegada,
            'fechaRecogido': e.fechaRecogido,
            'estado': e.estado,
            'rutaImagenFirma': e.rutaImagenFirma,
        }

    def _mapear(self, f):
        return EntradaPaquete(
            f['identradapaquete'], f['idpaquete'], f['idsesion'], f['fechallegada'],
            f['fecharecogido'], f['estado'], f['rutaimagenfirma']
        )

    def obtener_por_paquete(self, idPaquete: int) -> List[EntradaPaquete]:
        return self._obtener_por("idPaquete", idPaquete)

    def obtener_no_recogidos(self) -> List[EntradaPaquete]:
        return self._filas("WHERE estado=FALSE")

class ServicioError(Exception):
    """Error de regla de negocio."""
 
 
class AutenticacionError(ServicioError):
    """Credenciales o dispositivo invalidos."""
 
 
class AutorizacionError(ServicioError):
    """El usuario no tiene el permiso requerido."""
 
 
class NoEncontradoError(ServicioError):
    """La entidad solicitada no existe."""
 
 
# ============================================================
#                         UTILIDADES
# ============================================================
_ITERACIONES = 200_000
 
 
def hashear_contraseña(contraseña: str) -> str:
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", contraseña.encode(), bytes.fromhex(sal), _ITERACIONES)
    return f"pbkdf2${_ITERACIONES}${sal}${h.hex()}"
 
 
def verificar_contraseña(contraseña: str, almacenada: str) -> bool:
    try:
        _, iteraciones, sal, esperado = almacenada.split("$")
        h = hashlib.pbkdf2_hmac(
            "sha256", contraseña.encode(), bytes.fromhex(sal), int(iteraciones)
        )
        return hmac.compare_digest(h.hex(), esperado)
    except (ValueError, AttributeError):
        return False  # formato invalido (p. ej. contraseña en texto plano)
 
 
def _requerir(entidad, mensaje: str):
    if entidad is None:
        raise NoEncontradoError(mensaje)
    return entidad
 
 