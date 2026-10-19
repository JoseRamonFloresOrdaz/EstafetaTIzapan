from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Callable, List, Optional, Union


__all__ = ('Rol','Permiso','RolPermiso','Dispositivo','Usuario','Sesion','Cliente')


Fecha = Union[date, str]
Hora = Union[time, str]
FechaHora = Union[datetime, str]


# ============================================================
#                          MODELOS
# ============================================================
@dataclass
class Rol:
    idRol: Optional[int]
    nombre: str
    activo: bool

@dataclass
class Permiso:
    idPermiso: Optional[int]
    nombre: str
    activo: bool

@dataclass
class RolPermiso:
    idRolPermiso: Optional[int]
    idRol: int
    idPermiso: int

@dataclass
class Dispositivo:
    idDispositivo: Optional[int]
    nombreDispositivo: str
    direccionMac: str
    tipoDispositivo: str  # 'MOVIL' | 'COMPUTADORA'
    activo: bool


@dataclass
class Usuario:
    idUsuario: Optional[int]
    nombre: str
    apellido: str
    correo: str
    rol: Rol
    contraseña: str
    activo: bool


@dataclass
class Sesion:
    idSesion: Optional[int]
    idUsuario: int
    idDispositivo: int
    horaInicio: Optional[Hora]
    horaFin: Optional[Hora]
    fecha: Optional[Fecha]
    activa: bool

@dataclass
class Servicio:
    idServicio: Optional[int]
    nombre: str
    descripcion: str
    precio: float
    activo: bool

@dataclass
class Cliente:
    idCliente: Optional[int]
    nombre: str
    apellido: str
    telefono: str

@dataclass
class Encargo:
    idEncargo: Optional[int]
    idCliente: int
    idSesion: int
    fecha: Fecha
    subtotal: float
    descuento: float
    total: float
    pagado: bool

@dataclass
class ServicioEncargo:
    idServicioEncargo: Optional[int]
    idServicio: int
    idEncargo: int
    subtotal: float

@dataclass
class Material:
    idMaterial: Optional[int]
    idServicioEncargo: int
    rutaImagenReferencia: str
    fechaIngreso: Fecha
    fechaSalida: Optional[Fecha]
    entregado: bool


@dataclass
class Direccion:
    idDireccion: Optional[int]
    nombreCompleto: str
    calle: str
    numero_exterior: str
    numero_interior: Optional[str]
    ciudad: str
    cp: str
    telefono: str

@dataclass
class Paquete:
    idPaquete: Optional[int]
    idDireccionRemitente: int
    idDireccionDestinatario: int
    codigoRastreo: Optional[str]
    fecha: Optional[Fecha]

@dataclass
class SalidaPaquete:
    idSalidaPaquete: Optional[int]
    idPaquete: int
    idSesion: int
    fechaEntrada: FechaHora
    fechaRecoleccion: Optional[FechaHora]

@dataclass
class EntradaPaquete:
    idEntradaPaquete: Optional[int]
    idPaquete: int
    idSesion: int
    fechaLlegada: Optional[Fecha]
    fechaRecogido: Optional[Fecha]
    estado: bool
    rutaImagenFirma: Optional[str]
