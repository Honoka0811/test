import math
LON0, LAT1 = 138.2, 47.6
COSL = math.cos(math.radians(43.3))
K = 650.0                      # base px per world unit
BASE_W = int((146.8 - LON0) * COSL * K)
BASE_H = int((LAT1 - 37.6) * K)
def world(lon, lat): return ((lon - LON0) * COSL, (LAT1 - lat))
W, H, FPS = 1080, 1920, 30
# full view camera: Hokkaido bbox lon 139.33-145.82, lat 41.35-45.56
_hx0, _hy0 = world(139.33, 45.56); _hx1, _hy1 = world(145.82, 41.35)
Z0 = 1010 / (_hx1 - _hx0)
FULL = ((_hx0 + _hx1) / 2, (_hy0 + _hy1) / 2, Z0)
FULL_SY = 800      # screen y of camera center in full view
FOCUS_SY = 640     # screen y of focused city
ZF = Z0 * 1.75
FONT_DIR = '/tmp/claude-0/-home-user-test/6d1dd308-8d3d-5d9e-bb71-763cdc5e0fc0/scratchpad/fonts/'
DELA = FONT_DIR + 'DelaGothicOne.ttf'
MPB = FONT_DIR + 'MPLUSRounded1c-800.ttf'
MPM = FONT_DIR + 'MPLUSRounded1c-500.ttf'
