
# ══════════════════════════════════════════════════════════════════════════════
# URBANISATION SCORE MAP – QGIS Plugin
# Paste all 5 parts into a single .py file, in order.
# ══════════════════════════════════════════════════════════════════════════════

# ── PART 1: Imports & Constants ───────────────────────────────────────────────

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QMessageBox, QSlider, QSpinBox, QGroupBox,
    QFormLayout, QDialogButtonBox
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsProject, QgsMapLayer, QgsRasterLayer,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsColorRampShader, QgsRasterShader,
    QgsSingleBandPseudoColorRenderer
)
from qgis.gui import QgsMapTool
from qgis.utils import iface
from osgeo import gdal, osr
from scipy.ndimage import convolve
import numpy as np
import processing
import tempfile, os, math

# ── Target CRS ─────────────────────────────────────────────────────────────────
EPSG3035 = QgsCoordinateReferenceSystem('EPSG:3035')

# ── Warn user if output raster exceeds this pixel count ───────────────────────
WARN_PIXEL_COUNT = 5_000_000

# ── Sampling radius in metres (used in Part 4 kernel and Part 5 hover tool) ───
SAMPLE_RADIUS_M = 30

# ── Nodata value used throughout ──────────────────────────────────────────────
NODATA_VAL = -9999.0

# ── GHS-BUILT-C height-band weights (based on your legend) ────────────────────
# Open / non-built classes → 0
# Built classes → weight by height band
BUILT_WEIGHTS = {
    1: 0, 2: 0, 3: 0, 4: 0, 5: 0,      # open spaces (veg, water, road)
    11: 1, 12: 2, 13: 3, 14: 4, 15: 5,  # residential  (<=3m … >30m)
    21: 1, 22: 2, 23: 3, 24: 4, 25: 5,  # non-residential
}

# ── PART 2: WeightSlider widget & main dialog ─────────────────────────────────

class WeightSlider(QHBoxLayout):
    """A labelled horizontal slider that returns a 0.00–1.00 float weight."""
    def __init__(self, label, default_pct):
        super().__init__()
        lbl = QLabel(label)
        lbl.setMinimumWidth(230)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(default_pct)
        self.slider.setTickInterval(5)
        self.val_label = QLabel(f"{default_pct/100:.2f}")
        self.val_label.setMinimumWidth(35)
        self.slider.valueChanged.connect(
            lambda v: self.val_label.setText(f"{v/100:.2f}")
        )
        self.addWidget(lbl)
        self.addWidget(self.slider)
        self.addWidget(self.val_label)

    @property
    def value(self):
        return self.slider.value() / 100.0


class UrbanScoreDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Urbanisation Score Map")
        self.setMinimumWidth(520)
        layout = QVBoxLayout()

        # Collect raster layers from project
        self.rasters = [
            l for l in QgsProject.instance().mapLayers().values()
            if l.type() == QgsMapLayer.RasterLayer
        ]
        names = [l.name() for l in self.rasters]

        if len(self.rasters) < 4:
            QMessageBox.critical(None, "Error",
                "At least 4 raster layers must be loaded:\n"
                "IMD, Green area, Population density, GHS-BUILT-C.")
            self.reject()
            return

        # ── Raster assignment ──────────────────────────────────────────────
        rbox  = QGroupBox("Assign raster layers")
        rform = QFormLayout()
        self.combo_imd   = QComboBox(); self.combo_imd.addItems(names)
        self.combo_green = QComboBox(); self.combo_green.addItems(names)
        self.combo_pop   = QComboBox(); self.combo_pop.addItems(names)
        self.combo_built = QComboBox(); self.combo_built.addItems(names)
        # Default: assign first 4 rasters in order
        for i, c in enumerate([self.combo_imd, self.combo_green,
                                self.combo_pop, self.combo_built]):
            if i < len(names):
                c.setCurrentIndex(i)
        rform.addRow("IMD raster (impervious surface %):", self.combo_imd)
        rform.addRow("Green area raster (fraction 0–1):", self.combo_green)
        rform.addRow("Population density raster:", self.combo_pop)
        rform.addRow("GHS-BUILT-C raster (integer classes):", self.combo_built)
        rbox.setLayout(rform)
        layout.addWidget(rbox)

        # ── Output resolution ──────────────────────────────────────────────
        resbox    = QGroupBox("Output resolution")
        reslayout = QHBoxLayout()
        reslayout.addWidget(QLabel("Pixel size (metres):"))
        self.spin_res = QSpinBox()
        self.spin_res.setRange(1, 500)
        self.spin_res.setValue(10)
        self.spin_res.setSuffix(" m")
        reslayout.addWidget(self.spin_res)
        reslayout.addStretch()
        resbox.setLayout(reslayout)
        layout.addWidget(resbox)

        # ── Indicator weights ──────────────────────────────────────────────
        wbox    = QGroupBox("Indicator weights  (auto-normalised so they sum to 1)")
        wlayout = QVBoxLayout()
        self.w_imd   = WeightSlider("IMD weight (default 0.35):",               35)
        self.w_pop   = WeightSlider("Population density weight (default 0.25):", 25)
        self.w_built = WeightSlider("Built index weight (default 0.20):",        20)
        self.w_green = WeightSlider("Green area weight (default 0.20):",         20)
        for w in [self.w_imd, self.w_pop, self.w_built, self.w_green]:
            wlayout.addLayout(w)
        wbox.setLayout(wlayout)
        layout.addWidget(wbox)

        # ── OK / Cancel ────────────────────────────────────────────────────
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.setLayout(layout)

    def get_params(self):
        return {
            'imd':     self.rasters[self.combo_imd.currentIndex()],
            'green':   self.rasters[self.combo_green.currentIndex()],
            'pop':     self.rasters[self.combo_pop.currentIndex()],
            'built':   self.rasters[self.combo_built.currentIndex()],
            'res':     self.spin_res.value(),
            'w_imd':   self.w_imd.value,
            'w_pop':   self.w_pop.value,
            'w_built': self.w_built.value,
            'w_green': self.w_green.value,
        }

# ── PART 3: Helper functions & canvas extent setup ────────────────────────────

def warp_to_array(layer, extent, res, method=1):
    """
    Reproject, clip and resample a raster layer to the target extent/resolution.
    method: 0 = nearest neighbour (use for categorical, e.g. GHS-BUILT-C)
            1 = bilinear  (use for continuous, e.g. IMD, pop, green)
    Returns a float32 numpy array; nodata pixels become nan.
    """
    tmp = tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name
    processing.run("gdal:warpreproject", {
        'INPUT':         layer,
        'SOURCE_CRS':    layer.crs(),
        'TARGET_CRS':    EPSG3035,
        'RESAMPLING':    method,
        'TARGET_EXTENT': (f"{extent.xMinimum()},{extent.xMaximum()},"
                          f"{extent.yMinimum()},{extent.yMaximum()} [EPSG:3035]"),
        'TARGET_RESOLUTION': res,
        'NODATA':        -9999,
        'OUTPUT':        tmp
    })
    ds  = gdal.Open(tmp)
    arr = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
    nd  = ds.GetRasterBand(1).GetNoDataValue()
    ds  = None
    os.unlink(tmp)
    if nd is not None:
        arr[arr == nd] = np.nan
    return arr


def norm(arr):
    """Min-max normalise a numpy array, ignoring nan values."""
    mn, mx = np.nanmin(arr), np.nanmax(arr)
    if mx == mn:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


# ── Show dialog ────────────────────────────────────────────────────────────────
dlg = UrbanScoreDialog()
if not dlg.exec_():
    raise SystemExit("Cancelled.")

p = dlg.get_params()

# ── Get canvas extent and transform to EPSG:3035 ──────────────────────────────
canvas     = iface.mapCanvas()
canvas_crs = canvas.mapSettings().destinationCrs()
transform  = QgsCoordinateTransform(canvas_crs, EPSG3035, QgsProject.instance())
extent     = transform.transformBoundingBox(canvas.extent())

res    = p['res']
width  = int((extent.xMaximum() - extent.xMinimum()) / res)
height = int((extent.yMaximum() - extent.yMinimum()) / res)
n_pix  = width * height

print(f"Output grid: {width} x {height} = {n_pix:,} pixels at {res} m.")

# ── Warn if area is large ──────────────────────────────────────────────────────
if n_pix > WARN_PIXEL_COUNT:
    reply = QMessageBox.question(
        None, "Large area warning",
        f"The current canvas extent will produce a raster of\n"
        f"{n_pix:,} pixels ({width} x {height} at {res} m).\n\n"
        f"This may take several minutes.\n\n"
        f"Tip: zoom in or increase the pixel size to reduce computation time.\n\n"
        f"Continue anyway?",
        QMessageBox.Yes | QMessageBox.No
    )
    if reply == QMessageBox.No:
        raise SystemExit("Cancelled — extent too large.")


# ── PART 4: True 30 m window score map ───────────────────────────────────────
# For each pixel, the score is computed by:
#   1. Taking the mean of raw indicator values in a 30 m radius window
#   2. Normalising across all pixels in the canvas extent
#   3. Applying the weighted composite formula
# This matches the original point-based method exactly.
# ─────────────────────────────────────────────────────────────────────────────

from scipy.ndimage import uniform_filter, generic_filter
import math

# ── Load rasters ───────────────────────────────────────────────────────────────
print("Warping IMD raster (bilinear)...")
imd_arr   = warp_to_array(p['imd'],   extent, res, method=1)

print("Warping green area raster (bilinear)...")
green_arr = warp_to_array(p['green'], extent, res, method=1)

print("Warping population density raster (bilinear)...")
pop_arr   = warp_to_array(p['pop'],   extent, res, method=1)

print("Warping GHS-BUILT-C raster (nearest neighbour)...")
built_raw = warp_to_array(p['built'], extent, res, method=0)

# ── Crop to common shape ───────────────────────────────────────────────────────
actual_height = min(imd_arr.shape[0], green_arr.shape[0],
                    pop_arr.shape[0],  built_raw.shape[0])
actual_width  = min(imd_arr.shape[1], green_arr.shape[1],
                    pop_arr.shape[1],  built_raw.shape[1])
print(f"Actual array shape: {actual_height} x {actual_width}")

imd_arr   = imd_arr  [:actual_height, :actual_width]
green_arr = green_arr[:actual_height, :actual_width]
pop_arr   = pop_arr  [:actual_height, :actual_width]
built_raw = built_raw[:actual_height, :actual_width]

# ── Build circular kernel for 30 m window ─────────────────────────────────────
# Kernel radius in pixels; res is the pixel size in metres
r_px = int(math.ceil(SAMPLE_RADIUS_M / res))
k_size = 2 * r_px + 1
ky, kx = np.ogrid[-r_px:r_px+1, -r_px:r_px+1]
circle_kernel = (kx**2 + ky**2 <= r_px**2).astype(np.float32)
kernel_sum = circle_kernel.sum()
print(f"Circular kernel: {k_size}x{k_size} px, {int(kernel_sum)} pixels in circle.")

# ── Circular moving-window mean (fast convolution) ────────────────────────────
# For nodata-safe convolution: compute sum of values and sum of valid counts
# separately, then divide.
from scipy.ndimage import convolve

def circular_mean(arr, kernel):
    """
    Compute circular moving-window mean, ignoring nodata (nan) pixels.
    Returns nan where no valid pixels exist in the window.
    """
    valid = (~np.isnan(arr)).astype(np.float32)
    arr_filled = np.where(np.isnan(arr), 0.0, arr).astype(np.float32)
    val_sum   = convolve(arr_filled, kernel, mode='reflect')
    count_sum = convolve(valid,      kernel, mode='reflect')
    with np.errstate(invalid='ignore', divide='ignore'):
        result = np.where(count_sum > 0, val_sum / count_sum, np.nan)
    return result.astype(np.float32)

# ── Height-weighted built index (per pixel, before windowing) ─────────────────
print("Computing height-weighted built index...")
built_weighted = np.full_like(built_raw, np.nan)
for cls, w in BUILT_WEIGHTS.items():
    built_weighted[built_raw == cls] = float(w)

# ── Apply 30 m circular window to all layers ──────────────────────────────────
print("Applying 30 m circular window to IMD...")
imd_w   = circular_mean(imd_arr,       circle_kernel)

print("Applying 30 m circular window to green area...")
green_w = circular_mean(green_arr,     circle_kernel)

print("Applying 30 m circular window to population density...")
pop_w   = circular_mean(pop_arr,       circle_kernel)

print("Applying 30 m circular window to built index...")
built_w = circular_mean(built_weighted, circle_kernel)

# ── Normalise across canvas extent (min-max, ignoring nan) ────────────────────
print("Normalising across canvas extent...")
imd_n   = norm(imd_w)
pop_n   = norm(pop_w)
built_n = norm(built_w)
green_n = 1.0 - norm(green_w)   # invert: less green = more urban

# ── Composite score ────────────────────────────────────────────────────────────
w_total = p['w_imd'] + p['w_pop'] + p['w_built'] + p['w_green']
if w_total == 0:
    QMessageBox.critical(None, "Error", "All weights are 0.")
    raise SystemExit("All weights zero.")

print("Computing composite urbanisation score...")
score = (
    p['w_imd']   * imd_n   +
    p['w_pop']   * pop_n   +
    p['w_built'] * built_n +
    p['w_green'] * green_n
) / w_total

# Mask pixels where any windowed layer is fully nodata
nodata_mask = (np.isnan(imd_w) | np.isnan(green_w) |
               np.isnan(pop_w) | np.isnan(built_w))
score[nodata_mask] = -9999.0

# ── Write GeoTIFF ──────────────────────────────────────────────────────────────
print("Writing output GeoTIFF...")
out_path = tempfile.NamedTemporaryFile(suffix='_urban_score.tif', delete=False).name
driver   = gdal.GetDriverByName('GTiff')
ds_out   = driver.Create(out_path, actual_width, actual_height, 1,
                         gdal.GDT_Float32, ['COMPRESS=LZW', 'TILED=YES'])
ds_out.SetGeoTransform([extent.xMinimum(), res, 0,
                        extent.yMaximum(), 0, -res])
srs = osr.SpatialReference()
srs.ImportFromEPSG(3035)
ds_out.SetProjection(srs.ExportToWkt())
band = ds_out.GetRasterBand(1)
band.WriteArray(score.astype(np.float32))
band.SetNoDataValue(-9999.0)
band.FlushCache()
ds_out = None

# ── Load into QGIS with green → yellow → red colour ramp ─────────────────────
print("Loading result into QGIS...")
result_layer = QgsRasterLayer(out_path, "Urbanisation Score (30 m window)")
QgsProject.instance().addMapLayer(result_layer)

ramp_items = [
    QgsColorRampShader.ColorRampItem(0.00, QColor('#1a9641'), '0.00 - least urban'),
    QgsColorRampShader.ColorRampItem(0.25, QColor('#a6d96a')),
    QgsColorRampShader.ColorRampItem(0.50, QColor('#ffffbf')),
    QgsColorRampShader.ColorRampItem(0.75, QColor('#fdae61')),
    QgsColorRampShader.ColorRampItem(1.00, QColor('#d7191c'), '1.00 - most urban'),
]
color_ramp = QgsColorRampShader()
color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
color_ramp.setColorRampItemList(ramp_items)

raster_shader = QgsRasterShader()
raster_shader.setRasterShaderFunction(color_ramp)

renderer = QgsSingleBandPseudoColorRenderer(
    result_layer.dataProvider(), 1, raster_shader
)
renderer.setClassificationMin(0.0)
renderer.setClassificationMax(1.0)
result_layer.setRenderer(renderer)
result_layer.triggerRepaint()

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\nDone. Output saved to:\n{out_path}")
print(f"Effective weights (normalised): "
      f"IMD={p['w_imd']/w_total:.2f}, "
      f"Pop={p['w_pop']/w_total:.2f}, "
      f"Built={p['w_built']/w_total:.2f}, "
      f"Green={p['w_green']/w_total:.2f}")

# ── PART 5: Hover tool ────────────────────────────────────────────────────────
# Reads the score directly from the raster computed in Part 4.
# The value shown is the exact pixel value under the cursor —
# which already represents the 30 m window mean score.
# ─────────────────────────────────────────────────────────────────────────────

from qgis.PyQt.QtWidgets import QLabel
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont
from qgis.gui import QgsMapTool
from qgis.core import QgsCoordinateTransform, QgsProject, QgsCoordinateReferenceSystem

NODATA_VAL = -9999.0


class HoverScoreTool(QgsMapTool):
    """
    Reads the urbanisation score pixel value directly under the cursor
    and displays it as a colour-coded overlay label.
    No resampling needed — the raster already encodes the 30 m window score.
    """

    def __init__(self, canvas, score_layer):
        super().__init__(canvas)
        self.canvas      = canvas
        self.score_layer = score_layer
        self.epsg3035    = QgsCoordinateReferenceSystem('EPSG:3035')

        # ── Overlay label ──────────────────────────────────────────────────
        self.label = QLabel(canvas)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Monospace", 10, QFont.Bold))
        self.label.setFixedHeight(28)
        self.label.hide()

        self._open_raster()

    def _open_raster(self):
        """Open score GeoTIFF with GDAL and cache geotransform."""
        self.ds = gdal.Open(self.score_layer.source())
        if self.ds is None:
            return
        gt = self.ds.GetGeoTransform()
        self.px_w     = gt[1]
        self.px_h     = abs(gt[5])
        self.x_origin = gt[0]
        self.y_origin = gt[3]
        self.raster_w = self.ds.RasterXSize
        self.raster_h = self.ds.RasterYSize
        self.band     = self.ds.GetRasterBand(1)

    def _canvas_to_3035(self, point):
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        transform  = QgsCoordinateTransform(
            canvas_crs, self.epsg3035, QgsProject.instance()
        )
        return transform.transform(point)

    def _read_pixel(self, pt_3035):
        """Read the single pixel value at pt_3035. Returns None if out of bounds or nodata."""
        if self.ds is None:
            return None
        col = int((pt_3035.x() - self.x_origin) / self.px_w)
        row = int((self.y_origin - pt_3035.y()) / self.px_h)
        if not (0 <= col < self.raster_w and 0 <= row < self.raster_h):
            return None
        val = self.band.ReadAsArray(col, row, 1, 1)[0][0]
        if val == NODATA_VAL or np.isnan(val):
            return None
        return float(val)

    def _score_to_colour(self, score):
        """Interpolate hex colour on green→yellow→red ramp."""
        breakpoints = [
            (0.00, (26,  150, 65)),
            (0.25, (166, 217, 106)),
            (0.50, (255, 255, 191)),
            (0.75, (253, 174, 97)),
            (1.00, (215, 25,  28)),
        ]
        score = max(0.0, min(1.0, score))
        for i in range(len(breakpoints) - 1):
            v0, c0 = breakpoints[i]
            v1, c1 = breakpoints[i + 1]
            if score <= v1:
                t = (score - v0) / (v1 - v0)
                r = int(c0[0] + t * (c1[0] - c0[0]))
                g = int(c0[1] + t * (c1[1] - c0[1]))
                b = int(c0[2] + t * (c1[2] - c0[2]))
                return f"#{r:02x}{g:02x}{b:02x}"
        return "#d7191c"

    def canvasMoveEvent(self, event):
        pos     = event.pos()
        map_pt  = self.toMapCoordinates(pos)
        pt_3035 = self._canvas_to_3035(map_pt)
        val     = self._read_pixel(pt_3035)

        if val is None:
            self.label.hide()
            return

        colour = self._score_to_colour(val)
        self.label.setText(f"  Urban score (30 m): {val:.3f}  ")
        self.label.setStyleSheet(
            f"background-color: rgba(30,30,30,210);"
            f"color: {colour};"
            f"border: 1.5px solid {colour};"
            f"border-radius: 6px;"
            f"padding: 4px 10px;"
            f"font-weight: bold;"
        )
        self.label.adjustSize()

        offset_x = 15
        offset_y = -self.label.height() - 8
        new_x = min(pos.x() + offset_x,
                    self.canvas.width() - self.label.width() - 4)
        new_y = max(pos.y() + offset_y, 4)
        self.label.move(new_x, new_y)
        self.label.show()

    def canvasLeaveEvent(self, event):
        self.label.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.deactivate()

    def deactivate(self):
        self.label.hide()
        self.ds = None
        super().deactivate()
        print("Hover score tool deactivated.")


# ── Activate ──────────────────────────────────────────────────────────────────
hover_tool = HoverScoreTool(iface.mapCanvas(), result_layer)
iface.mapCanvas().setMapTool(hover_tool)
print("Hover tool active — move cursor over the map. Press Escape to stop.")
