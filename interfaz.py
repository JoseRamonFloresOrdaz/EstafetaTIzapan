"""Interfaz grafica (PyQt6) para administrar las entidades de los repositorios."""
import os
import sys
import types
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, time
from typing import Any, Callable, Optional, Union, get_args, get_origin, get_type_hints

# repositorios.py hace `from modelos import *`, por lo que mappeo debe estar en el path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mappeo'))

from PyQt6.QtCore import QDate, QDateTime, Qt, QTime
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDateEdit, QDateTimeEdit,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QTimeEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

import estilo
import modelos as m
import repositorios as r


# ============================================================
#                   CONFIGURACION DE ENTIDADES
# ============================================================
@dataclass
class Entidad:
    grupo: str
    titulo: str
    repositorio: type
    modelo: type
    describir: Callable[[Any], str]


ENTIDADES = [
    Entidad("Permisos y autenticación", "Roles", r.RolSQL, m.Rol, lambda e: e.nombre),
    Entidad("Permisos y autenticación", "Permisos", r.PermisoSQL, m.Permiso, lambda e: e.nombre),
    Entidad("Permisos y autenticación", "Roles - Permisos", r.RolPermisoSQL, m.RolPermiso,
            lambda e: f"Rol {e.idRol} / Permiso {e.idPermiso}"),
    Entidad("Permisos y autenticación", "Dispositivos", r.DispositivoSQL, m.Dispositivo,
            lambda e: e.nombreDispositivo),
    Entidad("Permisos y autenticación", "Usuarios", r.UsuarioSQL, m.Usuario,
            lambda e: f"{e.nombre} {e.apellido}"),
    Entidad("Permisos y autenticación", "Sesiones", r.SesionSQL, m.Sesion,
            lambda e: f"Sesión {e.fecha or ''} (usuario {e.idUsuario})"),
    Entidad("Encargos", "Servicios", r.ServicioSQL, m.Servicio, lambda e: e.nombre),
    Entidad("Encargos", "Clientes", r.ClienteSQL, m.Cliente,
            lambda e: f"{e.nombre} {e.apellido}"),
    Entidad("Encargos", "Encargos", r.EncargoSQL, m.Encargo,
            lambda e: f"Encargo {e.fecha} (${e.total:,.2f})"),
    Entidad("Encargos", "Servicios por encargo", r.ServicioEncargoSQL, m.ServicioEncargo,
            lambda e: f"Encargo {e.idEncargo} / Servicio {e.idServicio}"),
    Entidad("Encargos", "Materiales", r.MaterialSQL, m.Material,
            lambda e: os.path.basename(e.rutaImagenReferencia or "")),
    Entidad("Paquetería", "Direcciones", r.DireccionSQL, m.Direccion,
            lambda e: f"{e.nombreCompleto}, {e.ciudad}"),
    Entidad("Paquetería", "Paquetes", r.PaqueteSQL, m.Paquete,
            lambda e: e.codigoRastreo or "Sin código"),
    Entidad("Paquetería", "Salidas de paquetes", r.SalidaPaqueteSQL, m.SalidaPaquete,
            lambda e: f"Paquete {e.idPaquete}"),
    Entidad("Paquetería", "Entradas de paquetes", r.EntradaPaqueteSQL, m.EntradaPaquete,
            lambda e: f"Paquete {e.idPaquete}"),
]

_POR_MODELO = {e.modelo: e for e in ENTIDADES}

# campo -> modelo al que hace referencia
LLAVES_FORANEAS = {
    'idRol': m.Rol,
    'idPermiso': m.Permiso,
    'idUsuario': m.Usuario,
    'idDispositivo': m.Dispositivo,
    'idSesion': m.Sesion,
    'idCliente': m.Cliente,
    'idServicio': m.Servicio,
    'idEncargo': m.Encargo,
    'idServicioEncargo': m.ServicioEncargo,
    'idPaquete': m.Paquete,
    'idDireccionRemitente': m.Direccion,
    'idDireccionDestinatario': m.Direccion,
}

OPCIONES_FIJAS = {'tipoDispositivo': ('MOVIL', 'COMPUTADORA')}

DIALECTOS = {
    'postgres': ("PostgreSQL", r.DialectoPostgres),
    'sql_server': ("SQL Server", r.DialectoSqlServer),
}


# ============================================================
#                         UTILIDADES
# ============================================================
def _etiqueta(nombre: str) -> str:
    """idDireccionRemitente -> 'Id direccion remitente'."""
    texto = nombre.replace('_', ' ')
    texto = ''.join(f" {c.lower()}" if c.isupper() else c for c in texto)
    return texto.strip().capitalize()


def _analizar_tipo(tipo) -> tuple:
    """Devuelve (tipo_base, es_opcional) de una anotacion del modelo."""
    if get_origin(tipo) in (Union, types.UnionType):
        args = get_args(tipo)
    else:
        args = (tipo,)
    opcional = type(None) in args
    args = [a for a in args if a is not type(None)]
    for base in (datetime, date, time, bool, float, int, str):
        if base in args:
            return base, opcional
    return args[0], opcional


def _a_python(valor, base):
    """Convierte fechas/horas que llegan como texto desde la base de datos."""
    if valor is None or not isinstance(valor, str):
        return valor
    if base is datetime:
        return datetime.fromisoformat(valor)
    if base is date:
        return date.fromisoformat(valor[:10])
    if base is time:
        return time.fromisoformat(valor)
    return valor


def _id_de(entidad) -> Optional[int]:
    repo = _POR_MODELO[type(entidad)].repositorio
    return getattr(entidad, repo.COL_ID)


def _texto_celda(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, float):
        return f"{valor:,.2f}"
    if isinstance(valor, (date, time)):
        return valor.isoformat(sep=' ', timespec='minutes') if isinstance(valor, datetime) \
            else valor.isoformat()
    if is_dataclass(valor):
        return _POR_MODELO[type(valor)].describir(valor)
    return str(valor)


class Contexto:
    """Mantiene un repositorio por modelo sobre una misma conexion."""

    def __init__(self, nombre: str, conexion, dialecto: r.IDialectoSql):
        self.nombre = nombre
        self.conexion = conexion
        self._repos = {e.modelo: e.repositorio(conexion, dialecto) for e in ENTIDADES}

    def repo(self, modelo) -> r.RepositorioBase:
        return self._repos[modelo]


# ============================================================
#                      FORMULARIO GENERICO
# ============================================================
class DialogoFormulario(QDialog):
    def __init__(self, ctx: Contexto, entidad: Entidad, registro=None, parent=None):
        super().__init__(parent)
        self._ctx = ctx
        self._entidad = entidad
        self._registro = registro
        self._repo = ctx.repo(entidad.modelo)
        self._campos = {}  # nombre -> (obtener, asignar)
        self._widgets = {}

        accion = "Editar" if registro else "Nuevo"
        self.setWindowTitle(f"{accion} - {entidad.titulo}")
        self.setMinimumWidth(480)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hints = get_type_hints(entidad.modelo)
        for campo in fields(entidad.modelo):
            if campo.name == self._repo.COL_ID:
                continue
            widget, obtener, asignar = self._crear_editor(campo.name, hints[campo.name])
            form.addRow(_etiqueta(campo.name) + ":", widget)
            self._campos[campo.name] = (obtener, asignar)
            self._widgets[campo.name] = widget
            if registro is not None:
                asignar(getattr(registro, campo.name))

        self._conectar_total()

        botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        botones.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        botones.button(QDialogButtonBox.StandardButton.Save).setObjectName("primario")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")

        titulo = QLabel(f"{accion} · {entidad.titulo}", objectName="titulo")
        panel = estilo.PanelVidrio()
        contenido = QVBoxLayout(panel)
        contenido.setSpacing(14)
        contenido.addWidget(titulo)
        if registro is not None:
            contenido.addWidget(QLabel(
                f"{_etiqueta(self._repo.COL_ID)}: {_id_de(registro)}", objectName="subtitulo"
            ))
        contenido.addLayout(form)
        contenido.addSpacing(6)
        contenido.addWidget(botones)

        fondo = estilo.Fondo()
        QVBoxLayout(fondo).addWidget(panel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(fondo)

    # ---------- editores ----------
    def _crear_editor(self, nombre: str, tipo):
        base, opcional = _analizar_tipo(tipo)

        if nombre in LLAVES_FORANEAS or is_dataclass(base):
            return self._editor_relacion(nombre, LLAVES_FORANEAS.get(nombre, base), base, opcional)
        if nombre in OPCIONES_FIJAS:
            combo = QComboBox()
            combo.addItems(OPCIONES_FIJAS[nombre])
            return combo, combo.currentText, lambda v: combo.setCurrentText(v or "")
        if nombre == 'contraseña':
            return self._editor_contraseña()
        if base is bool:
            caja = estilo.Interruptor()
            caja.setChecked(nombre in ('activo', 'activa'))
            return caja, caja.isChecked, lambda v: caja.setChecked(bool(v))
        if base is float:
            num = QDoubleSpinBox()
            num.setRange(0, 1_000_000_000)
            num.setDecimals(2)
            num.setPrefix("$ ")
            return num, num.value, lambda v: num.setValue(float(v or 0))
        if base is int:
            num = QSpinBox()
            num.setRange(0, 2_147_483_647)
            return num, num.value, lambda v: num.setValue(int(v or 0))
        if base in (datetime, date, time):
            return self._editor_fecha(base, opcional)
        if nombre.lower().startswith('ruta'):
            return self._editor_ruta(nombre, opcional)
        return self._editor_texto(nombre, opcional)

    def _editor_texto(self, nombre, opcional):
        linea = QLineEdit()
        if opcional:
            linea.setPlaceholderText("Opcional")

        def obtener():
            texto = linea.text().strip()
            if not texto:
                if opcional:
                    return None
                raise ValueError(f"El campo '{_etiqueta(nombre)}' es obligatorio.")
            return texto

        return linea, obtener, lambda v: linea.setText("" if v is None else str(v))

    def _editor_ruta(self, nombre, opcional):
        contenedor = QWidget()
        fila = QHBoxLayout(contenedor)
        fila.setContentsMargins(0, 0, 0, 0)
        linea = QLineEdit()
        boton = QPushButton("Examinar…")
        fila.addWidget(linea)
        fila.addWidget(boton)

        def examinar():
            ruta, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar imagen", "", "Imágenes (*.png *.jpg *.jpeg *.bmp);;Todos (*)"
            )
            if ruta:
                linea.setText(ruta)

        boton.clicked.connect(examinar)

        def obtener_ruta():
            texto = linea.text().strip()
            if not texto and not opcional:
                raise ValueError(f"El campo '{_etiqueta(nombre)}' es obligatorio.")
            return texto or None

        return contenedor, obtener_ruta, lambda v: linea.setText(v or "")

    def _editor_contraseña(self):
        linea = QLineEdit()
        linea.setEchoMode(QLineEdit.EchoMode.Password)
        if self._registro is not None:
            linea.setPlaceholderText("Dejar vacío para conservar la actual")

        def obtener():
            if linea.text():
                return r.hashear_contraseña(linea.text())
            if self._registro is not None:
                return self._registro.contraseña
            raise ValueError("La contraseña es obligatoria.")

        return linea, obtener, lambda v: None  # nunca se muestra el hash

    def _editor_fecha(self, base, opcional):
        if base is datetime:
            editor = QDateTimeEdit(QDateTime.currentDateTime())
            editor.setDisplayFormat("yyyy-MM-dd HH:mm")
            editor.setCalendarPopup(True)
            leer = lambda: editor.dateTime().toPyDateTime()
            escribir = lambda v: editor.setDateTime(QDateTime(
                QDate(v.year, v.month, v.day), QTime(v.hour, v.minute, v.second)))
        elif base is date:
            editor = QDateEdit(QDate.currentDate())
            editor.setDisplayFormat("yyyy-MM-dd")
            editor.setCalendarPopup(True)
            leer = lambda: editor.date().toPyDate()
            escribir = lambda v: editor.setDate(QDate(v.year, v.month, v.day))
        else:
            editor = QTimeEdit(QTime.currentTime())
            editor.setDisplayFormat("HH:mm:ss")
            leer = lambda: editor.time().toPyTime()
            escribir = lambda v: editor.setTime(QTime(v.hour, v.minute, v.second))

        if not opcional:
            return editor, leer, lambda v: v is not None and escribir(_a_python(v, base))

        contenedor = QWidget()
        fila = QHBoxLayout(contenedor)
        fila.setContentsMargins(0, 0, 0, 0)
        asignada = estilo.Interruptor()
        asignada.toggled.connect(editor.setEnabled)
        editor.setEnabled(False)
        fila.addWidget(asignada)
        fila.addWidget(editor, 1)

        def asignar(v):
            asignada.setChecked(v is not None)
            if v is not None:
                escribir(_a_python(v, base))

        return contenedor, lambda: leer() if asignada.isChecked() else None, asignar

    def _editor_relacion(self, nombre, modelo_rel, base, opcional):
        entidad_rel = _POR_MODELO[modelo_rel]
        combo = QComboBox()
        if opcional:
            combo.addItem("(ninguno)", None)
        for e in self._ctx.repo(modelo_rel).obtener_todos():
            combo.addItem(f"{_id_de(e)} - {entidad_rel.describir(e)}", e)

        def obtener():
            e = combo.currentData()
            if e is None:
                if opcional:
                    return None
                raise ValueError(
                    f"Seleccione un valor para '{_etiqueta(nombre)}'. "
                    f"Si no hay opciones, registre primero en '{entidad_rel.titulo}'."
                )
            return _id_de(e) if base is int else e

        def asignar(v):
            id_ = _id_de(v) if is_dataclass(v) else v
            for i in range(combo.count()):
                e = combo.itemData(i)
                if e is not None and _id_de(e) == id_:
                    combo.setCurrentIndex(i)
                    return

        return combo, obtener, asignar

    def _conectar_total(self):
        """En encargos el total se calcula a partir del subtotal y el descuento."""
        if not {'subtotal', 'descuento', 'total'} <= self._widgets.keys():
            return
        subtotal, descuento, total = (self._widgets[n] for n in ('subtotal', 'descuento', 'total'))

        def recalcular():
            total.setValue(max(subtotal.value() - descuento.value(), 0))

        subtotal.valueChanged.connect(recalcular)
        descuento.valueChanged.connect(recalcular)

    # ---------- guardado ----------
    def _guardar(self):
        try:
            valores = {nombre: obtener() for nombre, (obtener, _) in self._campos.items()}
            valores[self._repo.COL_ID] = _id_de(self._registro) if self._registro else None
            entidad = self._entidad.modelo(**valores)
            if self._registro is None:
                self._repo.crear(entidad)
            else:
                self._repo.actualizar(entidad)
        except ValueError as e:
            QMessageBox.warning(self, "Datos incompletos", str(e))
            return
        except (r.RepositorioError, r.ServicioError) as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.accept()


# ============================================================
#                    PANEL DE UNA ENTIDAD
# ============================================================
class PanelEntidad(QWidget):
    def __init__(self, ctx: Contexto, entidad: Entidad, ventana: "VentanaPrincipal"):
        super().__init__()
        self._ctx = ctx
        self._entidad = entidad
        self._ventana = ventana
        self._repo = ctx.repo(entidad.modelo)
        self._columnas = [f.name for f in fields(entidad.modelo)]
        self._registros = []

        titulo = QLabel(entidad.titulo, objectName="titulo")
        self._contador = QLabel(objectName="subtitulo")
        encabezado = QVBoxLayout()
        encabezado.setSpacing(0)
        encabezado.addWidget(titulo)
        encabezado.addWidget(self._contador)

        self._buscar = QLineEdit(objectName="buscar")
        self._buscar.setPlaceholderText("Buscar")
        self._buscar.setClearButtonEnabled(True)
        self._buscar.setFixedWidth(240)
        self._buscar.textChanged.connect(self._filtrar)

        barra = QHBoxLayout()
        barra.setSpacing(8)
        barra.addLayout(encabezado)
        barra.addStretch(1)
        barra.addWidget(self._buscar)
        for texto, accion, nombre in (
            ("Refrescar", self.refrescar, ""), ("Eliminar", self.eliminar, "peligro"),
            ("Editar", self.editar, ""), ("Nuevo", self.nuevo, "primario"),
        ):
            boton = QPushButton(texto, objectName=nombre)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.clicked.connect(accion)
            barra.addWidget(boton)

        self._tabla = QTableWidget(0, len(self._columnas))
        self._tabla.setShowGrid(False)
        self._tabla.setFrameShape(QFrame.Shape.NoFrame)
        self._tabla.verticalHeader().setDefaultSectionSize(36)
        self._tabla.horizontalHeader().setHighlightSections(False)
        self._tabla.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._tabla.setHorizontalHeaderLabels([_etiqueta(c) for c in self._columnas])
        self._tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setSortingEnabled(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._tabla.horizontalHeader().setStretchLastSection(True)
        self._tabla.doubleClicked.connect(self.editar)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addLayout(barra)
        layout.addWidget(self._tabla)

    def _descripciones_foraneas(self) -> dict:
        """columna -> {id: descripcion} para mostrar texto en lugar de solo el id."""
        resultado = {}
        for columna in self._columnas:
            modelo_rel = LLAVES_FORANEAS.get(columna)
            if modelo_rel is None or columna == self._repo.COL_ID:
                continue
            describir = _POR_MODELO[modelo_rel].describir
            try:
                resultado[columna] = {
                    _id_de(e): describir(e) for e in self._ctx.repo(modelo_rel).obtener_todos()
                }
            except r.RepositorioError:
                resultado[columna] = {}
        return resultado

    def refrescar(self):
        try:
            self._registros = self._repo.obtener_todos()
            foraneas = self._descripciones_foraneas()
        except r.RepositorioError as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self._tabla.setSortingEnabled(False)
        self._tabla.setRowCount(len(self._registros))
        for fila, registro in enumerate(self._registros):
            for col, nombre in enumerate(self._columnas):
                valor = getattr(registro, nombre)
                if nombre == 'contraseña':
                    texto = "••••••"
                elif nombre in foraneas and valor in foraneas[nombre]:
                    texto = f"{valor} - {foraneas[nombre][valor]}"
                else:
                    texto = _texto_celda(valor)
                item = QTableWidgetItem(texto)
                if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                    if nombre not in foraneas:
                        item.setData(Qt.ItemDataRole.EditRole, valor)  # ordenar numericamente
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item.setData(Qt.ItemDataRole.UserRole, fila)
                self._tabla.setItem(fila, col, item)
        self._tabla.setSortingEnabled(True)
        self._tabla.resizeColumnsToContents()
        self._filtrar(self._buscar.text())
        total = len(self._registros)
        self._contador.setText(f"{total} registro{'s' if total != 1 else ''}")

    def _filtrar(self, texto: str):
        texto = texto.strip().lower()
        for fila in range(self._tabla.rowCount()):
            visible = not texto or any(
                texto in (self._tabla.item(fila, c).text().lower())
                for c in range(self._tabla.columnCount())
            )
            self._tabla.setRowHidden(fila, not visible)

    def _seleccionado(self):
        filas = self._tabla.selectionModel().selectedRows()
        if not filas:
            QMessageBox.information(self, self._entidad.titulo, "Seleccione un registro.")
            return None
        indice = self._tabla.item(filas[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        return self._registros[indice]

    def _abrir_formulario(self, registro=None):
        try:
            dialogo = DialogoFormulario(self._ctx, self._entidad, registro, self)
        except r.RepositorioError as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.refrescar()

    def nuevo(self):
        self._abrir_formulario()

    def editar(self):
        registro = self._seleccionado()
        if registro is not None:
            self._abrir_formulario(registro)

    def eliminar(self):
        registro = self._seleccionado()
        if registro is None:
            return
        respuesta = QMessageBox.question(
            self, "Eliminar",
            f"¿Eliminar '{self._entidad.describir(registro)}' "
            f"({_etiqueta(self._repo.COL_ID)} {_id_de(registro)})?",
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return
        try:
            self._repo.eliminar(_id_de(registro))
        except r.RepositorioError as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.refrescar()


# ============================================================
#                      VENTANA PRINCIPAL
# ============================================================
class VentanaPrincipal(QMainWindow):
    def __init__(self, ctx: Contexto):
        super().__init__()
        self._ctx = ctx
        self._paneles = {}
        self.setWindowTitle(f"Estafeta - {ctx.nombre}")
        self.resize(1200, 720)

        self._arbol = QTreeWidget()
        self._arbol.setHeaderHidden(True)
        self._arbol.setRootIsDecorated(False)
        self._arbol.setIndentation(0)
        self._arbol.setItemsExpandable(False)
        self._arbol.setCursor(Qt.CursorShape.PointingHandCursor)
        fuente_grupo = self._arbol.font()
        fuente_grupo.setPointSizeF(fuente_grupo.pointSizeF() * 0.85)
        fuente_grupo.setBold(True)
        grupos = {}
        for entidad in ENTIDADES:
            if entidad.grupo not in grupos:
                grupo = QTreeWidgetItem(self._arbol, [entidad.grupo.upper()])
                grupo.setFlags(Qt.ItemFlag.ItemIsEnabled)
                grupo.setFont(0, fuente_grupo)
                grupo.setForeground(0, estilo.QColor(110, 110, 115))
                grupos[entidad.grupo] = grupo
            hoja = QTreeWidgetItem(grupos[entidad.grupo], [entidad.titulo])
            hoja.setData(0, Qt.ItemDataRole.UserRole, entidad)
        self._arbol.expandAll()
        self._arbol.currentItemChanged.connect(self._seleccionar)

        self._estado = QLabel(objectName="estado")

        lateral = estilo.PanelVidrio()
        lateral.setFixedWidth(290)
        columna = QVBoxLayout(lateral)
        columna.setSpacing(10)
        columna.addWidget(QLabel("Estafeta", objectName="marca"))
        columna.addWidget(self._arbol, 1)
        columna.addWidget(self._estado)

        self._pila = QStackedWidget()
        self._pila.addWidget(QLabel(
            "Seleccione una entidad en el menú de la izquierda.",
            alignment=Qt.AlignmentFlag.AlignCenter, objectName="vacio",
        ))
        principal = estilo.PanelVidrio()
        QVBoxLayout(principal).addWidget(self._pila)

        fondo = estilo.Fondo()
        fila = QHBoxLayout(fondo)
        fila.setContentsMargins(10, 10, 10, 10)
        fila.setSpacing(0)
        fila.addWidget(lateral)
        fila.addWidget(principal, 1)
        self.setCentralWidget(fondo)

        QShortcut(QKeySequence.StandardKey.Refresh, self, self._refrescar_actual)
        QShortcut(QKeySequence.StandardKey.Quit, self, self.close)

        self.estado(f"●  Conectado a {ctx.nombre}")

    def estado(self, mensaje: str):
        self._estado.setText(mensaje)

    def _seleccionar(self, item, _anterior=None):
        entidad = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        if entidad is None:
            return
        panel = self._paneles.get(entidad.titulo)
        if panel is None:
            panel = PanelEntidad(self._ctx, entidad, self)
            self._paneles[entidad.titulo] = panel
            self._pila.addWidget(panel)
            panel.refrescar()
        self._pila.setCurrentWidget(panel)

    def _refrescar_actual(self):
        panel = self._pila.currentWidget()
        if isinstance(panel, PanelEntidad):
            panel.refrescar()


# ============================================================
#                        PUNTO DE ENTRADA
# ============================================================
def iniciar_ui(**conexiones) -> int:
    """Abre la interfaz. Recibe las conexiones por nombre: postgres=..., sql_server=...

    Si se proporciona mas de una, se pregunta con cual trabajar.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    estilo.aplicar(app)

    disponibles = {DIALECTOS[clave][0]: (cnx, DIALECTOS[clave][1]()) for clave, cnx in conexiones.items()}
    if not disponibles:
        raise ValueError("Se requiere al menos una conexion (postgres=... o sql_server=...)")

    nombre = next(iter(disponibles))
    if len(disponibles) > 1:
        nombre, ok = QInputDialog.getItem(
            None, "Base de datos", "Seleccione la base de datos:", list(disponibles), 0, False
        )
        if not ok:
            return 0

    conexion, dialecto = disponibles[nombre]
    ventana = VentanaPrincipal(Contexto(nombre, conexion, dialecto))
    ventana.show()
    try:
        return app.exec()
    finally:
        conexion.cerrar_conexion()
