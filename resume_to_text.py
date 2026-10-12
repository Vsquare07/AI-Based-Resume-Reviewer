import pymupdf

def find_gutter(words, page_width, min_gap=10):
    bins = [0] * (int(page_width) + 2)
    for w in words:
        for x in range(int(w[0]), min(int(w[2]) + 1, len(bins))):
            bins[x] += 1
    limit = max(2, len(words) * 0.01)  # tolerate a few stray header words
    lo, hi = int(page_width * 0.15), int(page_width * 0.85)
    best, start = None, None
    for x in range(lo, hi + 1):
        empty = x < hi and bins[x] <= limit
        if empty and start is None:
            start = x
        elif not empty and start is not None:
            if x - start >= min_gap and (best is None or x - start > best[1] - best[0]):
                best = (start, x)
            start = None
    return (best[0] + best[1]) / 2 if best else None

def build_lines(col, link_after):
    col = sorted(col, key=lambda w: (w[1] + w[3]) / 2)
    lines, cur, cy = [], [], None
    for w in col:
        y = (w[1] + w[3]) / 2
        if cy is None or abs(y - cy) <= 4:
            cur.append(w)
            cy = y if cy is None else cy
        else:
            lines.append(cur)
            cur, cy = [w], y
    if cur:
        lines.append(cur)
    return [
        " ".join(w[4] + link_after.get((w[5], w[6], w[7]), "")
                 for w in sorted(l, key=lambda w: w[0]))
        for l in lines
    ]

def extract_text(file_path):
    doc = pymupdf.open(file_path)
    pages = []
    for page in doc:
        words = page.get_text("words")
        if not words:
            continue

        # link_after: (block, line, word_no) of the last word in a link -> " (url)"
        link_after = {}
        for l in page.get_links():
            url = l.get("uri")
            if not url:
                continue
            rect = pymupdf.Rect(l["from"])
            hits = [w for w in words
                    if rect.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
            if not hits:
                continue
            anchor = " ".join(w[4] for w in hits)
            if anchor.lower().replace("https://", "").replace("http://", "").rstrip("/") in url.lower():
                continue
            last = hits[-1]
            link_after[(last[5], last[6], last[7])] = f" ({url})"

        split = find_gutter(words, page.rect.width)
        if split is None:
            cols = [words]
        else:
            cols = [
                [w for w in words if (w[0] + w[2]) / 2 < split],
                [w for w in words if (w[0] + w[2]) / 2 >= split],
            ]
        for col in cols:
            pages.append("\n".join(build_lines(col, link_after)))
    return "\n".join(pages)

if(__name__=="__main__"):
    print(extract_text("sample.pdf"))