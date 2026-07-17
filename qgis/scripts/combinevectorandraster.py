
# ══════════════════════════════════════════════════════════════════════════════
# VECTOR TO RASTER + MERGE PLUGIN
# Reprojects everything to EPSG:3035, rasterises the vector layer,
# then merges it with a chosen raster into a single 1-band output raster.
# Where the rasterised vector has valid data it takes priority;
# elsewhere the original raster value is used.
# ══════════════════════════════════════════════════════════════════════════════

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QMessageBox, QLineEdit, QSpinBox, QGroupBox,
    QFormLayout, QDialogButtonBox
)
from qgis.PyQt.QtCore import Qt
from qgis.core import (
    QgsProject, QgsMapLayer, QgsRasterLayer,
    QgsCoordinateReferenceSystem, QgsVectorLayer
)
from qgis.utils import iface
from osgeo import gdal, osr
import numpy as np
import processing
import tempfile, os

EPSG3035  = QgsCoordinateReferenceSystem('EPSG:3035')
NODATA    = -9999.0


# ── Dialog ─────────────────────────────────────────────────────────────────────
class MergeDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vector → Raster & Merge")
        self.setMinimumWidth(480)
        layout = QVBoxLayout()

        self.vector_layers = [
            l for l in QgsProject.instance().mapLayers().values()
            if l.type() == QgsMapLayer.VectorLayer
        ]
        self.raster_layers = [
            l for l in QgsProject.instance().mapLayers().values()
            if l.type() == QgsMapLayer.RasterLayer
        ]

        if not self.vector_layers:
            QMessageBox.critical(None, "Error", "No vector layers found in the project.")
            self.reject(); return
        if not self.raster_layers:
            QMessageBox.critical(None, "Error", "No raster layers found in the project.")
            self.reject(); return

        # ── Layer selection ────────────────────────────────────────────────
        layer_box  = QGroupBox("Select layers")
        layer_form = QFormLayout()

        self.combo_vector = QComboBox()
        self.combo_vector.addItems([l.name() for l in self.vector_layers])
        layer_form.addRow("Vector layer (to rasterise):", self.combo_vector)

        self.combo_field = QComboBox()
        self.combo_vector.currentIndexChanged.connect(self._update_fields)
        self._update_fields(0)
        layer_form.addRow("Field to burn as pixel value:", self.combo_field)

        self.combo_raster = QComboBox()
        self.combo_raster.addItems([l.name() for l in self.raster_layers])
        layer_form.addRow("Raster layer (to merge with):", self.combo_raster)

        layer_box.setLayout(layer_form)
        layout.addWidget(layer_box)

        # ── Resolution ────────────────────────────────────────────────────
        res_box    = QGroupBox("Output resolution")
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Pixel size (metres):"))
        self.spin_res = QSpinBox()
        self.spin_res.setRange(1, 1000)
        self.spin_res.setValue(10)
        self.spin_res.setSuffix(" m")
        res_layout.addWidget(self.spin_res)
        res_layout.addStretch()
        res_box.setLayout(res_layout)
        layout.addWidget(res_box)

        # ── Output name ───────────────────────────────────────────────────
        name_box    = QGroupBox("Output layer name")
        name_layout = QHBoxLayout()
        self.name_edit = QLineEdit("Merged Raster")
        name_layout.addWidget(self.name_edit)
        name_box.setLayout(name_layout)
        layout.addWidget(name_box)

        # ── Buttons ───────────────────────────────────────────────────────
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.setLayout(layout)

    def _update_fields(self, index):
        self.combo_field.clear()
        if index < 0 or index >= len(self.vector_layers):
            return
        fields = [f.name() for f in self.vector_layers[index].fields()]
        self.combo_field.addItems(fields if fields else ["(no fields)"])

    def get_params(self):
        return {
            'vector':     self.vector_layers[self.combo_vector.currentIndex()],
            'burn_field': self.combo_field.currentText(),
            'raster':     self.raster_layers[self.combo_raster.currentIndex()],
            'res':        self.spin_res.value(),
            'out_name':   self.name_edit.text().strip() or "Merged Raster",
        }


# ── Reproject vector to EPSG:3035 ─────────────────────────────────────────────
def reproject_vector(layer):
    print(f"Reprojecting vector '{layer.name()}' to EPSG:3035...")
    result = processing.run("native:reprojectlayer", {
        'INPUT':      layer,
        'TARGET_CRS': EPSG3035,
        'OUTPUT':     'memory:'
    })
    return result['OUTPUT']


# ── Reproject raster to EPSG:3035 ─────────────────────────────────────────────
def reproject_raster(layer, res):
    print(f"Reprojecting raster '{layer.name()}' to EPSG:3035...")
    tmp = tempfile.NamedTemporaryFile(suffix='_reproj.tif', delete=False).name
    processing.run("gdal:warpreproject", {
        'INPUT':             layer,
        'SOURCE_CRS':        layer.crs(),
        'TARGET_CRS':        EPSG3035,
        'RESAMPLING':        1,
        'TARGET_RESOLUTION': res,
        'NODATA':            NODATA,
        'OUTPUT':            tmp
    })
    return tmp


# ── Rasterise vector onto the same grid as the reference raster ───────────────
def rasterise_vector(vector_layer, burn_field, ref_raster_path, res):
    print(f"Rasterising vector using field '{burn_field}'...")
    ds   = gdal.Open(ref_raster_path)
    gt   = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    xmin = gt[0];  ymax = gt[3]
    xmax = xmin + w * gt[1]
    ymin = ymax + h * gt[5]
    ds   = None

    tmp = tempfile.NamedTemporaryFile(suffix='_rasterised.tif', delete=False).name
    processing.run("gdal:rasterize", {
        'INPUT':     vector_layer,
        'FIELD':     burn_field,
        'BURN':      0,
        'USE_Z':     False,
        'UNITS':     1,
        'WIDTH':     res,
        'HEIGHT':    res,
        'EXTENT':    f"{xmin},{xmax},{ymin},{ymax} [EPSG:3035]",
        'NODATA':    NODATA,
        'OPTIONS':   'COMPRESS=LZW',
        'DATA_TYPE': 5,
        'INIT':      None,
        'INVERT':    False,
        'EXTRA':     '',
        'OUTPUT':    tmp
    })
    return tmp


# ── Merge into a single band ───────────────────────────────────────────────────
def merge_to_single_band(vec_path, raster_path, out_name):
    """
    Combine rasterised vector and original raster into one band.
    Priority: vector value where valid, raster value elsewhere.
    """
    print("Merging into single band...")
    ds1 = gdal.Open(vec_path)
    ds2 = gdal.Open(raster_path)

    arr_vec    = ds1.GetRasterBand(1).ReadAsArray().astype(np.float32)
    arr_raster = ds2.GetRasterBand(1).ReadAsArray().astype(np.float32)

    # Crop to common shape
    h = min(arr_vec.shape[0], arr_raster.shape[0])
    w = min(arr_vec.shape[1], arr_raster.shape[1])
    arr_vec    = arr_vec   [:h, :w]
    arr_raster = arr_raster[:h, :w]

    gt  = ds1.GetGeoTransform()
    ds1 = None
    ds2 = None

    # Build nodata masks
    vec_nodata    = (arr_vec    == NODATA) | np.isnan(arr_vec)
    raster_nodata = (arr_raster == NODATA) | np.isnan(arr_raster)

    # Mosaic: vector takes priority; fall back to raster where vector is nodata
    merged = np.where(~vec_nodata, arr_vec, arr_raster)
    # Mark pixels where both are nodata
    both_nodata = vec_nodata & raster_nodata
    merged[both_nodata] = NODATA

    # Write output
    out_path = tempfile.NamedTemporaryFile(suffix='_merged.tif', delete=False).name
    driver   = gdal.GetDriverByName('GTiff')
    ds_out   = driver.Create(out_path, w, h, 1, gdal.GDT_Float32,
                             ['COMPRESS=LZW', 'TILED=YES'])
    ds_out.SetGeoTransform(gt)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3035)
    ds_out.SetProjection(srs.ExportToWkt())
    band = ds_out.GetRasterBand(1)
    band.WriteArray(merged)
    band.SetNoDataValue(NODATA)
    band.FlushCache()
    ds_out = None

    return out_path


# ── Run ────────────────────────────────────────────────────────────────────────
dlg = MergeDialog()
if not dlg.exec_():
    raise SystemExit("Cancelled.")

p = dlg.get_params()

vec_reproj    = reproject_vector(p['vector'])
raster_reproj = reproject_raster(p['raster'], p['res'])
vec_raster    = rasterise_vector(vec_reproj, p['burn_field'], raster_reproj, p['res'])
merged_path   = merge_to_single_band(vec_raster, raster_reproj, p['out_name'])

print("Loading result into QGIS...")
merged_layer = QgsRasterLayer(merged_path, p['out_name'])
if not merged_layer.isValid():
    QMessageBox.critical(None, "Error", f"Failed to load output.\nPath: {merged_path}")
    raise SystemExit("Invalid output layer.")

QgsProject.instance().addMapLayer(merged_layer)

for f in [raster_reproj, vec_raster]:
    try: os.unlink(f)
    except: pass

print(f"\nDone. Layer '{p['out_name']}' loaded into QGIS.")
print(f"Output: {merged_path}")
print(f"Single band: vector values (field: {p['burn_field']}) where present, raster values elsewhere.")
