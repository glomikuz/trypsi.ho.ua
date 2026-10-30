#!/usr/bin/env python3
"""Перетворює документ Word (.docx або .doc) на HTML-фрагмент для сторінки сайту.

Тільки стандартна бібліотека. Файли .doc спершу конвертуються в .docx через
macOS `textutil`. Результат — «сира» розмітка в стилі сайту (p, ul/ol, таблиці
.doc-table з colspan/rowspan, .doc-subtitle для тексту по центру, .doc-approve
для тексту праворуч), яку потім треба переглянути й доредагувати вручну:
розставити <h2>, прибрати підписи/порожні рядки тощо.

Використання:
	python3 tools/docx2html.py htdocs/file.docx > /tmp/out.html
	python3 tools/docx2html.py htdocs/file.doc --text     # лише текст, для огляду
"""
import html
import os
import re
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def load(path):
	if path.lower().endswith(".doc"):
		out = os.path.join(tempfile.mkdtemp(), "doc.docx")
		subprocess.run(["textutil", "-convert", "docx", path, "-output", out], check=True)
		path = out
	with zipfile.ZipFile(path) as z:
		return ET.fromstring(z.read("word/document.xml")).find(W + "body")


def on(el, tag):
	x = el.find(tag) if el is not None else None
	return x is not None and x.get(W + "val") not in ("0", "false", "none")


def runs(p):
	"""Список (текст, жирний) для абзацу."""
	out = []
	for r in p.iter(W + "r"):
		rp = r.find(W + "rPr")
		t = ""
		for x in r:
			if x.tag == W + "t":
				t += x.text or ""
			elif x.tag == W + "tab":
				t += " "
			elif x.tag in (W + "br", W + "cr"):
				t += "\n"
		if t:
			out.append((t, on(rp, W + "b")))
	return out


def clean(s):
	s = s.replace(" ", " ")
	s = re.sub(r"[ \t]+", " ", s)
	s = re.sub(r" *\n *", "\n", s)
	return s.strip()


def inline(p, all_bold_doc):
	rs = runs(p)
	text = clean("".join(t for t, _ in rs))
	if not text:
		return "", False
	bold_all = all(b for t, b in rs if t.strip())
	if bold_all or all_bold_doc:
		body = html.escape(text)
	else:
		parts, cur, buf = [], None, ""
		for t, b in rs:
			if b != cur and buf:
				parts.append((buf, cur))
				buf = ""
			cur = b
			buf += t
		parts.append((buf, cur))
		body = "".join(("<b>%s</b>" % html.escape(t) if b and t.strip() else html.escape(t)) for t, b in parts)
		body = clean(body)
	return body.replace("\n", "<br>"), bold_all


def ppr(p):
	pp = p.find(W + "pPr")
	jc = pp.find(W + "jc").get(W + "val") if pp is not None and pp.find(W + "jc") is not None else ""
	num = pp is not None and pp.find(W + "numPr") is not None
	return jc, num


def cell_text(tc, all_bold_doc):
	ps = [x for x in (inline(p, True)[0] for p in tc.findall(W + "p")) if x]
	out = ""
	for x in ps:
		# рядок, перенесений у Word вручну (продовження з малої літери), — через пробіл
		out += (" " if out and re.match(r"^[a-zа-яіїєґ(«]", x) and not re.search(r"[.:;!?]$", out) else "<br>" if out else "") + x
	return out


def table(tbl, all_bold_doc):
	rows = []
	for tr in tbl.findall(W + "tr"):
		row = []
		for tc in tr.findall(W + "tc"):
			pr = tc.find(W + "tcPr")
			span = 1
			vm = None
			if pr is not None:
				g = pr.find(W + "gridSpan")
				if g is not None:
					span = int(g.get(W + "val"))
				v = pr.find(W + "vMerge")
				if v is not None:
					vm = v.get(W + "val") or "continue"
			row.append({"text": cell_text(tc, all_bold_doc), "span": span, "vm": vm, "rows": 1})
		rows.append(row)
	# rowspan: «continue»-клітинки додаються до клітинки з тим самим стовпцем вище
	def col_of(row, i):
		return sum(c["span"] for c in row[:i])
	for ri, row in enumerate(rows):
		for ci, c in enumerate(row):
			if c["vm"] == "continue":
				col = col_of(row, ci)
				for up in range(ri - 1, -1, -1):
					hit = [x for k, x in enumerate(rows[up]) if col_of(rows[up], k) == col and x["vm"] != "continue"]
					if hit:
						hit[0]["rows"] += 1
						break
	# порожні колонки-розділювачі (жодного тексту в жодному рядку) — прибираємо
	width = max(sum(c["span"] for c in r) for r in rows)
	used = [False] * width
	for r in rows[1:] if len(rows) > 2 else rows:   # колонка лише з назвою в шапці теж порожня
		col = 0
		for c in r:
			if c["text"] and c["span"] < width:
				for k in range(col, col + c["span"]):
					used[k] = True
			col += c["span"]
	if not all(used) and any(used):
		for r in rows:
			col, keep = 0, []
			for c in r:
				dead = [k for k in range(col, col + c["span"]) if not used[k]]
				col += c["span"]
				if len(dead) == c["span"]:
					continue
				c["span"] -= len(dead)
				keep.append(c)
			r[:] = keep
	if len(rows) == 1 and len(rows[0]) <= 2:
		# таблиця-«шапка» (ЗАТВЕРДЖУЮ тощо) — віддаємо як абзаци
		return "\n".join('<p class="doc-approve">%s</p>' % c["text"] for c in rows[0] if c["text"])
	head = max(c["rows"] for c in rows[0]) if len(rows) > 1 else 0   # шапка: перший рядок + рядки під його rowspan
	out = ['<div class="table-wrap"><table class="doc-table">']
	if head:
		out.append("<thead>")
	for ri, row in enumerate(rows):
		if ri < head and not any(c["text"] for c in row):
			continue   # порожній рядок шапки
		if head and ri == head:
			out.append("</thead>\n<tbody>")
		cells = []
		for c in row:
			if c["vm"] == "continue":
				continue
			attrs = ""
			if c["span"] > 1:
				attrs += ' colspan="%d"' % c["span"]
			if c["rows"] > 1:
				attrs += ' rowspan="%d"' % c["rows"]
			tag = "th" if ri < head else "td"
			if tag == "th":
				attrs += ' scope="colgroup"' if c["span"] > 1 else ' scope="col"'
			cells.append("<%s%s>%s</%s>" % (tag, attrs, c["text"], tag))
		live = [c for c in row if c["vm"] != "continue"]
		if ri >= head and len(live) == 1 and len(cells) == 1 and live[0]["span"] > 1:
			# рядок-розділ на всю ширину («1 тиждень», «Понеділок»)
			out.append('<tr class="group"><th colspan="%d" scope="colgroup">%s</th></tr>' % (live[0]["span"], live[0]["text"]))
			continue
		total = ri >= head and row and any(re.match(r"(Разом|Всього|Усього|Сумарна|Гранично)", re.sub("<[^>]+>", "", c["text"])) for c in row[:2])
		out.append(("<tr class=\"total\">%s</tr>" if total else "<tr>%s</tr>") % "".join(cells))
	out.append("</tbody>" if head else "")
	out.append("</table></div>")
	return "\n".join(out).replace("<thead>\n</thead>\n", "")


def convert(path, text_only=False):
	body = load(path)
	ps = [p for p in body.iter(W + "p")]
	all_bold_doc = sum(1 for p in ps if inline(p, False)[1]) > 0.8 * max(1, sum(1 for p in ps if inline(p, False)[0]))
	out, lst = [], None
	for el in body:
		if el.tag == W + "tbl":
			if lst:
				out.append("</%s>" % lst)
				lst = None
			out.append(table(el, all_bold_doc))
			continue
		if el.tag != W + "p":
			continue
		text, bold = inline(el, all_bold_doc)
		if not text:
			continue
		jc, num = ppr(el)
		if text_only:
			out.append(("[%s%s] " % (jc[:1] or "-", "N" if num else "")) + re.sub("<[^>]+>", "", text))
			continue
		plain = re.sub("<[^>]+>", "", text)
		dash = re.match(r"^[-–—•·▪]\s*", plain)
		if num or dash:
			if not lst:
				lst = "ul"
				out.append("<ul>")
			out.append("<li>%s</li>" % (re.sub(r"^[-–—•·▪]\s*", "", text) if dash else text))
			continue
		if lst:
			out.append("</%s>" % lst)
			lst = None
		letters = re.sub(r"[^A-Za-zА-Яа-яІіЇїЄєҐґ’']", "", plain)
		if re.match(r"^(Додаток|ДОДАТОК)\s*№?\s*\d+$", plain) or (len(plain) < 150 and len(letters) > 3 and letters == letters.upper() and not re.match(r"^(ЗАТВЕРДЖ|ПОГОДЖ|СХВАЛ)", plain, re.I)):
			out.append("<h2>%s</h2>" % text)
		elif out and out[-1].startswith('<p class="doc-sign">') and len(plain) < 120 and not plain.endswith("."):
			out[-1] = out[-1][:-4] + "<br>" + text + "</p>"   # продовження підпису
		elif re.match(r"^(Директор|Уповноважена особа)", plain) and len(plain) < 200:
			out.append('<p class="doc-sign">%s</p>' % text)
		elif jc == "center" or re.match(r"^Розділ [0-9IVXІ]+\.\s", plain) and len(plain) < 250:
			out.append('<p class="doc-subtitle">%s</p>' % text)
		elif jc in ("right", "end") or re.match(r"^(ЗАТВЕРДЖ|ПОГОДЖ|СХВАЛ)", plain, re.I):
			out.append('<p class="doc-approve">%s</p>' % text)
		else:
			out.append("<p>%s</p>" % text)
	if lst:
		out.append("</%s>" % lst)
	out = [l for l in out if not re.search(r"MERGEFORMAT|^<p>\s*</p>$", l)]
	# «Розділ I» + заголовок КАПСОМ у кілька рядків -> один <h2>
	joined = []
	for line in out:
		h = re.match(r"<h2>(.*)</h2>$", line)
		if h and joined:
			ph = re.match(r"<h2>(.*)</h2>$", joined[-1])
			pr = re.match(r'<p class="doc-subtitle">(Розділ [^<]{1,8})</p>$', joined[-1])
			if ph and not re.match(r"^\s*(Додаток|ДОДАТОК)", ph.group(1)):
				joined[-1] = "<h2>%s %s</h2>" % (ph.group(1), h.group(1))
				continue
			if pr:
				joined[-1] = "<h2>%s. %s</h2>" % (pr.group(1).strip(), h.group(1))
				continue
		joined.append(line)
	out = joined
	# короткі рядки по центру всередині тексту — підзаголовки (h3, якщо вже є h2 КАПСОМ, інакше h2)
	has_h2 = sum(1 for l in out if l.startswith("<h2>")) > 2
	first_text = next((i for i, l in enumerate(out) if l.startswith("<p>") and len(l) > 150), 0)
	for i, l in enumerate(out):
		m = re.match(r'<p class="doc-subtitle">([^<]{3,200})</p>$', l)
		if m and i > first_text:
			out[i] = ("<h3>%s</h3>" if has_h2 else "<h2>%s</h2>") % m.group(1)
	# заголовок, перенесений на наступний рядок (продовження з малої літери або «КЗ КОР…»)
	tail = []
	for line in out:
		m = re.match(r"<(h[23])>(.*)</h[23]>$", line)
		pm = tail and re.match(r"<(h[23])>(.*)</h[23]>$", tail[-1])
		if m and pm and m.group(1) == pm.group(1) and (re.match(r"^(КЗ КОР|[a-zа-яіїєґ«])", m.group(2)) or m.group(2).endswith(".") and not re.search(r"[.:]$", pm.group(2))):
			tail[-1] = "<%s>%s %s</%s>" % (m.group(1), pm.group(2), m.group(2), m.group(1))
		else:
			tail.append(line)
	out = tail
	# абзаци-перелік, що закінчуються «;», — у список
	res, i = [], 0
	while i < len(out):
		j = i
		while j < len(out) and re.match(r"^<p>[^<]{0,300};</p>$", out[j]):
			j += 1
		if j - i >= 2:
			if j < len(out) and re.match(r"^<p>[^<]{0,300}\.</p>$", out[j]):
				j += 1
			res.append("<ul>")
			res += ["<li>%s</li>" % re.sub(r"^<p>(.*)</p>$", r"\1", l) for l in out[i:j]]
			res.append("</ul>")
			i = j
		else:
			res.append(out[i])
			i += 1
	out = res
	# пункти переліку, що йдуть одразу після списку (у Word без маркера), — у той самий список
	res = []
	for l in out:
		if res and res[-1] == "</ul>" and len(res) > 1 and re.search(r";</li>$", res[-2]) and re.match(r"^<p>[^<]{0,300}[;.]</p>$", l):
			res.insert(len(res) - 1, "<li>%s</li>" % l[3:-4])
			continue
		res.append(l)
	out = res
	# заголовок, що закінчується двокрапкою, — це вступ до переліку, а не розділ
	out = [re.sub(r"^<h2>(.*:)</h2>$", r"<h3>\1</h3>", l) for l in out]
	# сусідні рядки шапки/підпису/підзаголовка зливаємо в один абзац
	merged = []
	for line in out:
		m = re.match(r'<p class="(doc-subtitle|doc-approve|doc-sign)">(.*)</p>$', line, re.S)
		prev = merged and re.match(r'<p class="(doc-subtitle|doc-approve|doc-sign)">(.*)</p>$', merged[-1], re.S)
		if m and prev and prev.group(1) == m.group(1):
			merged[-1] = '<p class="%s">%s<br>%s</p>' % (m.group(1), prev.group(2), m.group(2))
		else:
			merged.append(line)
	return "\n".join(merged)
	return "\n".join(out)


if __name__ == "__main__":
	args = [a for a in sys.argv[1:] if not a.startswith("--")]
	if not args:
		sys.exit(__doc__)
	print(convert(args[0], "--text" in sys.argv))
