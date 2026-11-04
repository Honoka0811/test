"""資格のコスパランキングを作成する。

コスパ = 年収上乗せ額 ÷ 必要勉強時間
  年収上乗せ額 = 資格保有者の平均年収 − 日本の平均給与(460万円)
  → 「勉強1時間あたり、年収が何円上がるか(毎年)」を表す。
使い方: python3 rank.py   (ranking.csv と ranking.md を出力)
"""
import csv
from pathlib import Path

BASE_INCOME = 460  # 万円: 国税庁「民間給与実態統計調査」令和5年分の平均給与
HERE = Path(__file__).parent


def stars(hours):
    # 勉強時間から難易度を5段階で表示
    for limit, s in ((300, 1), (700, 2), (1500, 3), (3500, 4)):
        if hours <= limit:
            return "★" * s + "☆" * (5 - s)
    return "★★★★★"


def main():
    with open(HERE / "data.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        income = int(r["平均年収_万円"])
        hours = int(r["勉強時間_h"])
        premium = income - BASE_INCOME
        r["年収上乗せ_万円"] = premium
        r["コスパ_円per時間"] = round(premium * 10000 / hours)
        r["回収10年_円per時間"] = r["コスパ_円per時間"] * 10
        r["難易度"] = stars(hours)

    rows.sort(key=lambda r: r["コスパ_円per時間"], reverse=True)

    fields = ["順位", "資格", "分野", "平均年収_万円", "年収上乗せ_万円",
              "勉強時間_h", "難易度", "合格率", "コスパ_円per時間", "回収10年_円per時間"]
    with open(HERE / "ranking.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for i, r in enumerate(rows, 1):
            w.writerow({**r, "順位": i})

    lines = [
        "| 順位 | 資格 | 平均年収 | 年収上乗せ | 勉強時間 | 難易度 | 合格率 | **コスパ**<br>(円/勉強1h・年) | 10年累計<br>(円/勉強1h) |",
        "|---:|---|---:|---:|---:|---|---|---:|---:|",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | {r['資格']} | {int(r['平均年収_万円']):,}万円 | "
            f"{r['年収上乗せ_万円']:+,}万円 | {int(r['勉強時間_h']):,}h | {r['難易度']} | "
            f"{r['合格率']} | **{r['コスパ_円per時間']:,}** | {r['回収10年_円per時間']:,} |"
        )
    (HERE / "ranking.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
