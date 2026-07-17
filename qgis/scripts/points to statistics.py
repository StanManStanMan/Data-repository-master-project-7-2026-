from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox
)
from qgis.core import QgsProject, QgsMapLayer, QgsVectorLayer, QgsCoordinateReferenceSystem
import processing

# ── 1. Dialog: pick point layer + raster layers ──────────────────────────────

class LayerPickerDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Layers")
        self.setMinimumWidth(350)
        layout = QVBoxLayout()

        # Collect all vector layers (for point layer picker)
        self.vector_layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.VectorLayer
        ]
        vector_names = [l.name() for l in self.vector_layers]

        if not self.vector_layers:
            QMessageBox.critical(None, "Error",
                "No vector layers found in the project.")
            self.reject()
            return

        # Collect all raster layers
        self.raster_layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.RasterLayer
        ]
        raster_names = [l.name() for l in self.raster_layers]

        if len(self.raster_layers) < 3:
            QMessageBox.critical(None, "Error",
                "At least 3 raster layers must be loaded in the project.")
            self.reject()
            return

        # ── Point layer picker ───────────────────────────────────────────────
        layout.addWidget(QLabel("Point layer (will be reprojected to EPSG:3035\nand buffered at 30m):"))
        self.combo_points = QComboBox()
        self.combo_points.addItems(vector_names)
        layout.addWidget(self.combo_points)

        # ── Raster pickers ───────────────────────────────────────────────────
        self.combos = []
        for i in range(1, 4):
            layout.addWidget(QLabel(f"Raster layer {i} (zonal statistics – mean):"))
            combo = QComboBox()
            combo.addItems(raster_names)
            if i - 1 < len(raster_names):
                combo.setCurrentIndex(i - 1)
            layout.addWidget(combo)
            self.combos.append(combo)

        # ── Histogram raster picker ──────────────────────────────────────────
        layout.addWidget(QLabel("Raster layer for zonal histogram (sum):"))
        self.combo_hist = QComboBox()
        self.combo_hist.addItems(raster_names)
        layout.addWidget(self.combo_hist)

        # ── Run button ───────────────────────────────────────────────────────
        btn = QPushButton("Run")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self.setLayout(layout)

    def get_selections(self):
        point_layer = self.vector_layers[self.combo_points.currentIndex()]
        rasters = [
            self.raster_layers[c.currentIndex()] for c in self.combos
        ]
        hist_raster = self.raster_layers[self.combo_hist.currentIndex()]
        return point_layer, rasters, hist_raster


# ── 2. Show dialog ───────────────────────────────────────────────────────────

dlg = LayerPickerDialog()
if not dlg.exec_():
    raise SystemExit("Cancelled.")

point_layer, raster_layers, hist_raster = dlg.get_selections()

# ── 3. Reproject point layer to EPSG:3035 ────────────────────────────────────

print(f"Reprojecting '{point_layer.name()}' to EPSG:3035...")

reproject_result = processing.run("native:reprojectlayer", {
    'INPUT':       point_layer,
    'TARGET_CRS':  QgsCoordinateReferenceSystem('EPSG:3035'),
    'OUTPUT':      'memory:'
})

reprojected_layer = reproject_result['OUTPUT']
print("Reprojection done.")

# ── 4. Buffer the reprojected point layer at 30m ─────────────────────────────

print("Buffering reprojected points at 30m...")

buffer_result = processing.run("native:buffer", {
    'INPUT':         reprojected_layer,
    'DISTANCE':      30,
    'SEGMENTS':      5,
    'END_CAP_STYLE': 0,
    'JOIN_STYLE':    0,
    'MITER_LIMIT':   2,
    'DISSOLVE':      False,
    'OUTPUT':        'memory:'
})

# This is the starting zone layer; results will be chained into it
current_layer = buffer_result['OUTPUT']
print("Buffer created.")

# ── 5. Track existing layer IDs before any results are loaded ────────────────

existing_ids = set(QgsProject.instance().mapLayers().keys())

# ── 6. Chain zonal statistics (mean) through all 3 rasters ───────────────────
# Each result becomes the input for the next step, accumulating all columns.

for raster in raster_layers:
    prefix = raster.name().replace(" ", "_") + "_"
    print(f"Running zonal statistics for: {raster.name()} → prefix '{prefix}'")

    result = processing.run("native:zonalstatisticsfb", {
        'INPUT':         current_layer,
        'INPUT_RASTER':  raster,
        'RASTER_BAND':   1,
        'COLUMN_PREFIX': prefix,
        'STATISTICS':    [2],       # 2 = Mean
        'OUTPUT':        'memory:'
    })

    current_layer = result['OUTPUT']  # Pass result forward to next step

print("Zonal statistics done.")

# ── 7. Chain zonal histogram (sum) on top of the accumulated result ───────────

hist_prefix = hist_raster.name().replace(" ", "_") + "_"
print(f"Running zonal histogram for: {hist_raster.name()} → prefix '{hist_prefix}'")

result = processing.run("native:zonalhistogram", {
    'INPUT_VECTOR':  current_layer,
    'INPUT_RASTER':  hist_raster,
    'RASTER_BAND':   1,
    'COLUMN_PREFIX': hist_prefix,
    'OUTPUT':        'memory:'
})

current_layer = result['OUTPUT']
print("Zonal histogram done.")

# ── 8. Load only the final combined result into the Layers panel ──────────────

current_layer.setName("Zonal Statistics Results")
QgsProject.instance().addMapLayer(current_layer)

# Remove any other temporary layers that may have been added unintentionally
new_ids = set(QgsProject.instance().mapLayers().keys()) - existing_ids
new_ids.discard(current_layer.id())

if new_ids:
    QgsProject.instance().removeMapLayers(list(new_ids))
    print(f"Removed {len(new_ids)} intermediate temporary layer(s).")

print("All calculations complete. Final results loaded as 'Zonal Statistics Results'.")
