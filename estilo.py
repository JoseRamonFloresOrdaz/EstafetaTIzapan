"""Estilo tipo "liquid glass" para la interfaz PyQt6.

El efecto de vidrio se logra sin APIs del sistema operativo: `Fondo` pinta un
fondo de colores y guarda una copia difuminada; cada `PanelVidrio` pinta la parte
difuminada que tiene detras, le aplica un tinte blanco, un brillo superior y un
borde especular, de modo que parece vidrio esmerilado sobre el fondo.
"""
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QEasingCurve, pyqtProperty
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QGraphicsBlurEffect, QGraphicsPixmapItem,
    QGraphicsScene, QWidget,
)


RECURSOS = (Path(__file__).resolve().parent / "recursos").as_posix()

ACENTO = QColor(0, 122, 255)
VERDE = QColor(52, 199, 89)

# (x, y, radio) relativos al tamaño del fondo, color
_MANCHAS = (
    (0.10, 0.15, 0.55, QColor(94, 160, 255)),
    (0.85, 0.10, 0.50, QColor(255, 140, 190)),
    (0.55, 0.65, 0.60, QColor(150, 110, 255)),
    (0.05, 0.95, 0.50, QColor(80, 220, 200)),
    (0.95, 0.90, 0.45, QColor(255, 190, 110)),
)

# cintas nitidas: al quedar debajo del vidrio se ven difuminadas
_CINTAS = (
    ((-0.1, 0.35), (0.30, 0.05), (0.55, 0.75), (1.1, 0.40), QColor(255, 255, 255, 150), 0.05),
    ((-0.1, 0.80), (0.35, 0.55), (0.70, 1.05), (1.1, 0.70), QColor(70, 120, 255, 110), 0.035),
    ((0.40, -0.1), (0.75, 0.30), (0.60, 0.60), (0.95, 1.1), QColor(255, 120, 170, 90), 0.025),
)

QSS = """
* {
    color: #1d1d1f;
    font-size: 10.5pt;
}
QWidget#transparente, QStackedWidget, PanelEntidad {
    background: transparent;
}
QLabel { background: transparent; }
QLabel#marca { font-size: 17pt; font-weight: 700; }
QLabel#titulo { font-size: 20pt; font-weight: 700; }
QLabel#subtitulo, QLabel#estado, QLabel#vacio { color: #6e6e73; }
QLabel#estado { font-size: 9pt; }

/* ---------- campos ---------- */
QLineEdit, QAbstractSpinBox, QComboBox {
    background: rgba(255, 255, 255, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.85);
    border-bottom-color: rgba(0, 0, 0, 0.08);
    border-radius: 10px;
    padding: 6px 10px;
    selection-background-color: rgba(0, 122, 255, 0.35);
    min-height: 20px;
}
QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus {
    border: 1px solid rgba(0, 122, 255, 0.65);
    background: rgba(255, 255, 255, 0.78);
}
QLineEdit:disabled, QAbstractSpinBox:disabled {
    color: #a1a1a6;
    background: rgba(255, 255, 255, 0.25);
}
QLineEdit#buscar {
    border-radius: 16px;
    padding: 6px 14px;
}
QComboBox::drop-down, QDateTimeEdit::drop-down { border: none; width: 26px; }
QComboBox::down-arrow, QDateTimeEdit::down-arrow, QAbstractSpinBox::down-arrow {
    image: url({RECURSOS}/flecha_abajo.svg);
    width: 12px;
    height: 12px;
}
QAbstractSpinBox::up-arrow {
    image: url({RECURSOS}/flecha_arriba.svg);
    width: 10px;
    height: 10px;
}
QAbstractSpinBox::down-arrow { width: 10px; height: 10px; }
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
    background: transparent;
    border: none;
    width: 22px;
}
QAbstractSpinBox::up-button { subcontrol-position: top right; margin-top: 3px; }
QAbstractSpinBox::down-button { subcontrol-position: bottom right; margin-bottom: 3px; }
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {
    background: rgba(0, 0, 0, 0.06);
    border-radius: 5px;
}
QAbstractSpinBox::up-arrow:disabled, QAbstractSpinBox::down-arrow:disabled,
QDateTimeEdit::down-arrow:disabled { image: none; }
QComboBox QAbstractItemView {
    background: rgba(250, 250, 252, 0.97);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 10px;
    padding: 4px;
    outline: none;
    selection-background-color: rgba(0, 122, 255, 0.18);
    selection-color: #1d1d1f;
}

/* ---------- botones ---------- */
QPushButton {
    background: rgba(255, 255, 255, 0.50);
    border: 1px solid rgba(255, 255, 255, 0.90);
    border-bottom-color: rgba(0, 0, 0, 0.10);
    border-radius: 16px;
    padding: 7px 18px;
    font-weight: 600;
}
QPushButton:hover { background: rgba(255, 255, 255, 0.78); }
QPushButton:pressed { background: rgba(255, 255, 255, 0.32); }
QPushButton#primario {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(64, 156, 255, 0.95), stop:1 rgba(0, 113, 240, 0.95));
    border: 1px solid rgba(255, 255, 255, 0.55);
    color: white;
}
QPushButton#primario:hover { background: rgba(30, 140, 255, 1); }
QPushButton#primario:pressed { background: rgba(0, 100, 215, 1); }
QPushButton#peligro { color: #ff3b30; }

/* ---------- lista lateral ---------- */
QTreeWidget {
    background: transparent;
    border: none;
    outline: none;
}
QTreeWidget::item {
    padding: 7px 10px;
    border-radius: 10px;
    margin: 1px 0;
}
QTreeWidget::item:hover { background: rgba(255, 255, 255, 0.40); }
QTreeWidget::item:selected {
    background: rgba(0, 122, 255, 0.85);
    color: white;
}

/* ---------- tabla ---------- */
QTableWidget {
    background: transparent;
    alternate-background-color: rgba(255, 255, 255, 0.22);
    border: none;
    outline: none;
    selection-background-color: rgba(0, 122, 255, 0.20);
    selection-color: #1d1d1f;
}
QTableWidget::item { padding: 0 10px; border: none; }
QHeaderView, QHeaderView::section {
    background: transparent;
    border: none;
}
QHeaderView::section {
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    padding: 8px 10px;
    color: #6e6e73;
    font-weight: 600;
}
QTableCornerButton::section { background: transparent; border: none; }

/* ---------- barras de desplazamiento ---------- */
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px 4px; }
QScrollBar::handle {
    background: rgba(0, 0, 0, 0.22);
    border-radius: 3px;
    min-height: 30px;
    min-width: 30px;
}
QScrollBar::handle:hover { background: rgba(0, 0, 0, 0.38); }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

/* ---------- dialogos del sistema ---------- */
QMessageBox, QInputDialog, QFileDialog, QCalendarWidget QWidget {
    background: #f5f5f7;
}
QToolTip {
    background: rgba(250, 250, 252, 0.97);
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    padding: 4px 8px;
}
"""


def aplicar(app: QApplication):
    app.setStyle("Fusion")
    disponibles = set(QFontDatabase.families())
    for familia in ("SF Pro Display", "SF Pro Text", "Inter", "Cantarell", "Noto Sans"):
        if familia in disponibles:
            app.setFont(QFont(familia, 10))
            break
    app.setStyleSheet(QSS.replace("{RECURSOS}", RECURSOS))


def _difuminar(pixmap: QPixmap, radio: float) -> QPixmap:
    """Desenfoque gaussiano a baja resolucion (rapido) y reescalado suave."""
    escala = 4
    pequeño = pixmap.scaled(
        max(1, pixmap.width() // escala), max(1, pixmap.height() // escala),
        Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation,
    )
    item = QGraphicsPixmapItem(pequeño)
    efecto = QGraphicsBlurEffect()
    efecto.setBlurRadius(radio / escala)
    efecto.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(efecto)
    escena = QGraphicsScene()
    escena.addItem(item)

    salida = QImage(pequeño.size(), QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(salida)
    p.drawPixmap(0, 0, pequeño)  # evita bordes transparentes del desenfoque
    escena.render(p, QRectF(salida.rect()), QRectF(pequeño.rect()))
    p.end()
    return QPixmap.fromImage(salida).scaled(
        pixmap.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


# ============================================================
#                           FONDO
# ============================================================
class Fondo(QWidget):
    """Fondo de colores; los PanelVidrio descendientes se pintan sobre su version difuminada."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base = QPixmap()
        self.difuminado = QPixmap()

    def resizeEvent(self, evento):
        self._generar()
        super().resizeEvent(evento)

    def _generar(self):
        w, h = max(1, self.width()), max(1, self.height())
        lado = min(w, h)
        self._base = QPixmap(w, h)
        p = QPainter(self._base)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        degradado = QLinearGradient(0, 0, w, h)
        degradado.setColorAt(0, QColor(222, 234, 250))
        degradado.setColorAt(1, QColor(245, 230, 245))
        p.fillRect(0, 0, w, h, degradado)

        p.setPen(Qt.PenStyle.NoPen)
        for x, y, radio, color in _MANCHAS:
            centro = QPointF(x * w, y * h)
            g = QRadialGradient(centro, radio * max(w, h))
            g.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 210))
            g.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
            p.setBrush(QBrush(g))
            p.drawRect(0, 0, w, h)

        p.setBrush(Qt.BrushStyle.NoBrush)
        for ini, c1, c2, fin, color, grosor in _CINTAS:
            camino = QPainterPath(QPointF(ini[0] * w, ini[1] * h))
            camino.cubicTo(QPointF(c1[0] * w, c1[1] * h), QPointF(c2[0] * w, c2[1] * h),
                           QPointF(fin[0] * w, fin[1] * h))
            pluma = QPen(color, grosor * lado)
            pluma.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pluma)
            p.drawPath(camino)
        p.end()

        self.difuminado = _difuminar(self._base, 70)
        self.update()

    def paintEvent(self, _evento):
        QPainter(self).drawPixmap(0, 0, self._base)


# ============================================================
#                        PANEL DE VIDRIO
# ============================================================
class PanelVidrio(QFrame):
    SOMBRA = 12  # espacio alrededor del vidrio reservado para la sombra

    def __init__(self, parent=None, radio: float = 24, tinte: QColor = QColor(255, 255, 255, 80)):
        super().__init__(parent)
        self._radio = radio
        self._tinte = tinte
        m = self.SOMBRA
        self.setContentsMargins(m + 6, m + 6, m + 6, m + 6)

    def _fondo(self):
        padre = self.parentWidget()
        while padre is not None and not isinstance(padre, Fondo):
            padre = padre.parentWidget()
        return padre

    def paintEvent(self, _evento):
        m = self.SOMBRA
        rect = QRectF(self.rect()).adjusted(m, m, -m, -m)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # sombra suave: rectangulos concentricos de baja opacidad
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(m, 0, -2):
            p.setBrush(QColor(30, 40, 80, int(10 * (1 - i / m)) + 2))
            p.drawRoundedRect(rect.adjusted(-i, -i + 4, i, i + 4), self._radio + i, self._radio + i)

        camino = QPainterPath()
        camino.addRoundedRect(rect, self._radio, self._radio)
        p.setClipPath(camino)

        fondo = self._fondo()
        if fondo is not None and not fondo.difuminado.isNull():
            origen = self.mapTo(fondo, QPoint(0, 0))
            p.drawPixmap(0, 0, fondo.difuminado, origen.x(), origen.y(), self.width(), self.height())

        p.fillPath(camino, self._tinte)

        brillo = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        brillo.setColorAt(0.0, QColor(255, 255, 255, 120))
        brillo.setColorAt(0.25, QColor(255, 255, 255, 30))
        brillo.setColorAt(1.0, QColor(255, 255, 255, 10))
        p.fillPath(camino, brillo)
        p.setClipping(False)

        # borde especular: brillante arriba a la izquierda y abajo a la derecha
        borde = QLinearGradient(rect.topLeft(), rect.bottomRight())
        borde.setColorAt(0.0, QColor(255, 255, 255, 240))
        borde.setColorAt(0.5, QColor(255, 255, 255, 70))
        borde.setColorAt(1.0, QColor(255, 255, 255, 180))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QBrush(borde), 1.3))
        p.drawRoundedRect(rect.adjusted(0.6, 0.6, -0.6, -0.6), self._radio, self._radio)

        # banda interior de refraccion
        p.setPen(QPen(QColor(255, 255, 255, 55), 3))
        p.drawRoundedRect(rect.adjusted(2.5, 2.5, -2.5, -2.5), self._radio - 2, self._radio - 2)


# ============================================================
#                    INTERRUPTOR ESTILO iOS
# ============================================================
class Interruptor(QCheckBox):
    def __init__(self, texto: str = "", parent=None):
        super().__init__(texto, parent)
        self._posicion = 0.0
        self._animacion = QPropertyAnimation(self, b"posicion", self)
        self._animacion.setDuration(180)
        self._animacion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animar)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _obtener_posicion(self):
        return self._posicion

    def _asignar_posicion(self, valor):
        self._posicion = valor
        self.update()

    posicion = pyqtProperty(float, _obtener_posicion, _asignar_posicion)

    def setChecked(self, valor: bool):
        super().setChecked(valor)
        self._animacion.stop()
        self._posicion = 1.0 if valor else 0.0
        self.update()

    def _animar(self, valor: bool):
        self._animacion.stop()
        self._animacion.setEndValue(1.0 if valor else 0.0)
        self._animacion.start()

    def sizeHint(self):
        ancho = 48
        if self.text():
            ancho += 8 + self.fontMetrics().horizontalAdvance(self.text())
        return QSize(ancho, 30)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pista = QRectF(1, 2, 46, 26)
        apagado = QColor(120, 120, 128, 80)
        t = self._posicion
        color = QColor(
            int(apagado.red() + (VERDE.red() - apagado.red()) * t),
            int(apagado.green() + (VERDE.green() - apagado.green()) * t),
            int(apagado.blue() + (VERDE.blue() - apagado.blue()) * t),
            int(apagado.alpha() + (255 - apagado.alpha()) * t),
        )
        if not self.isEnabled():
            color.setAlpha(color.alpha() // 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(pista, 13, 13)

        x = pista.left() + 2 + t * (pista.width() - 26)
        p.setBrush(QColor(0, 0, 0, 35))
        p.drawEllipse(QRectF(x, pista.top() + 3, 22, 22))
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(x, pista.top() + 2, 22, 22))

        if self.text():
            p.setPen(self.palette().windowText().color())
            p.drawText(QRectF(56, 0, self.width() - 56, self.height()),
                       Qt.AlignmentFlag.AlignVCenter, self.text())
