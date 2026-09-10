# -*- coding: utf-8 -*-
"""重新抓取 examples/ 用到的公开数据，写进 examples/data/*.csv。

**出图时不跑这个脚本。** 三个例子只读 data/ 下的 CSV——渲染必须离线、
确定性，跑两次字节一致；联网取数会让产物随数据源的更新而漂。
把数据落成 CSV 还有一层意思：每个数字都可核对，读者不必相信代码。

数据源：世界银行 World Development Indicators（CC BY-4.0）
    https://api.worldbank.org/v2/
重新取数：python3 examples/fetch.py
"""
import csv, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
API = "https://api.worldbank.org/v2"


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def countries():
    """真实国家/地区 → (英文名, 区域)。剔除「世界」「欧元区」「中等收入」
    这些聚合口径：把它们和国家混在一张图里，等于同一个标度上放了两级行政层级。"""
    out = {}
    for c in get(f"{API}/country?format=json&per_page=400")[1]:
        if c["region"]["id"] != "NA":
            out[c["id"]] = (c["name"], c["region"]["value"])
    return out


def indicator(code, date, geo="all"):
    d = get(f"{API}/country/{geo}/indicator/{code}?date={date}&format=json&per_page=500")
    if len(d) < 2 or d[1] is None:
        raise SystemExit(f"{code} 在 {date} 没有数据")
    return d[1]


def write(name, header, rows, source):
    """走 csv 模块，不手拼字符串：国名里本来就有逗号（Korea, Rep.），
    手拼出来的文件读回去会当场错位。"""
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(f"# {source}\n")
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name}  {len(rows)} 行")


def main():
    os.makedirs(DATA, exist_ok=True)
    stamp = sys.argv[1] if len(sys.argv) > 1 else "取数日期见 git 提交时间"
    real = countries()

    pop = [(r["countryiso3code"], real[r["countryiso3code"]][0], int(r["value"]))
           for r in indicator("SP.POP.TOTL", 2024)
           if r["value"] is not None and r["countryiso3code"] in real]
    pop.sort(key=lambda t: -t[2])
    write("population-2024.csv", ["iso3", "name_en", "population"], pop[:12],
          f"世界银行 WDI · SP.POP.TOTL · 2024 年 · 取数 {stamp} · 仅保留人口前 12")

    life = [(r["countryiso3code"], real[r["countryiso3code"]][0],
             real[r["countryiso3code"]][1], round(r["value"], 2))
            for r in indicator("SP.DYN.LE00.IN", 2023)
            if r["value"] is not None and r["countryiso3code"] in real]
    life.sort()
    write("life-expectancy-2023.csv", ["iso3", "name_en", "region_en", "years"], life,
          f"世界银行 WDI · SP.DYN.LE00.IN · 2023 年 · 取数 {stamp}")

    urb = [(r["countryiso3code"], int(r["date"]), round(r["value"], 2))
           for r in indicator("SP.URB.TOTL.IN.ZS", "1990:2023", "CHN;KOR;BRA;IND;NGA")
           if r["value"] is not None]
    urb.sort(key=lambda t: (t[0], t[1]))
    write("urbanization-1990-2023.csv", ["iso3", "year", "urban_pct"], urb,
          f"世界银行 WDI · SP.URB.TOTL.IN.ZS · 1990–2023 · 取数 {stamp}")


if __name__ == "__main__":
    main()
