"""決定論的な物理シミュレーション: 円の中のボールが跳ねるたびに大きくなる。"""
import math

FPS = 60
SUB = 8                 # 1フレームあたりのサブステップ
CX, CY, R = 540, 1000, 450
G = 1500.0              # 重力 px/s^2
R0 = 18.0               # 初期半径
GROW = 1.031            # 1バウンドごとの拡大率
FILL = R * 0.985        # この半径で「満杯」


def simulate(max_t=70.0):
    x, y = CX + 60.0, CY - 250.0
    vx, vy = 420.0, 0.0
    r = R0
    dt = 1.0 / (FPS * SUB)
    frames, bounces = [], []
    t, n, done_at = 0.0, 0, None
    while t < max_t:
        for _ in range(SUB):
            vy += G * dt
            x += vx * dt
            y += vy * dt
            dx, dy = x - CX, y - CY
            d = math.hypot(dx, dy)
            if r < FILL and d + r >= R:
                nx, ny = dx / d, dy / d
                vn = vx * nx + vy * ny
                if vn > 0:
                    vx -= 2 * vn * nx
                    vy -= 2 * vn * ny
                    # 速度を一定以上に保ち、少しだけ回転方向のゆらぎを加える
                    sp = math.hypot(vx, vy)
                    target = max(sp, 900.0)
                    vx, vy = vx / sp * target, vy / sp * target
                    n += 1
                    r = min(r * GROW + 1.2, FILL)
                    bounces.append((t, n, r, x + nx * r, y + ny * r))
                    if r >= FILL and done_at is None:
                        done_at = t
                x, y = CX + nx * (R - r), CY + ny * (R - r)
            t += dt
        if done_at is not None:
            x, y, vx, vy = CX, CY, 0.0, 0.0
        frames.append((x, y, r, n))
        if done_at is not None and t > done_at + 4.0:
            break
    return frames, bounces, done_at


if __name__ == "__main__":
    f, b, d = simulate()
    print("frames", len(f), "sec", len(f) / FPS, "bounces", len(b), "filled at", d)
