"""tickers.txt 의 종목들 일봉(시/고/저/종/거래량)과 종목명을 받아 data/prices.json 으로 저장.
표준 라이브러리만 사용. 네이버 금융의 비공식 주소를 쓰므로 바뀌면 동작이 멈출 수 있음."""
import json, re, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "prices.json"
COUNT = 400  # 종목당 받아올 일봉 개수
UA = {"User-Agent": "Mozilla/5.0 (compatible; stock-lab/1.0)"}


def get(url, enc="utf-8"):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode(enc, errors="replace")


def read_tickers():
    codes = []
    for line in (ROOT / "tickers.txt").read_text(encoding="utf-8").splitlines():
        code = line.split("#")[0].strip()
        if re.fullmatch(r"[0-9A-Z]{6}", code):
            codes.append(code)
    return codes


def fetch_candles(code):
    url = (f"https://fchart.stock.naver.com/sise.nhn?symbol={code}"
           f"&timeframe=day&count={COUNT}&requestType=0")
    xml = get(url, "euc-kr")
    out = []
    for m in re.finditer(r'data="([^"]+)"', xml):
        p = m.group(1).split("|")
        if len(p) < 6:
            continue
        d = p[0]
        try:
            o, h, l, c, v = (int(float(x)) for x in p[1:6])
        except ValueError:
            continue
        if c <= 0:
            continue
        out.append([f"{d[:4]}-{d[4:6]}-{d[6:8]}", o, h, l, c, v])
    out.sort(key=lambda x: x[0])
    return out


def fetch_name(code):
    try:
        j = json.loads(get(f"https://m.stock.naver.com/api/stock/{code}/basic"))
        if j.get("stockName"):
            return j["stockName"]
    except Exception:
        pass
    try:
        j = json.loads(get(f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{code}"))
        return j["result"]["areas"][0]["datas"][0]["nm"]
    except Exception:
        return None


def main():
    old = {}
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            old = {}
    result, ok = {}, 0
    for code in read_tickers():
        try:
            candles = fetch_candles(code)
            if not candles:
                raise ValueError("받아온 일봉이 없음")
            name = fetch_name(code) or old.get(code, {}).get("name") or code
            result[code] = {"name": name, "candles": candles}
            ok += 1
            print(f"OK   {code} {name} {len(candles)}개 (마지막 {candles[-1][0]})")
        except Exception as e:
            print(f"FAIL {code}: {e}", file=sys.stderr)
            if code in old:
                result[code] = old[code]  # 실패하면 어제 데이터 유지
        time.sleep(0.5)
    if ok == 0:
        print("받아온 종목이 하나도 없어서 저장하지 않습니다.", file=sys.stderr)
        sys.exit(1)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
