#!/usr/bin/env python3
"""
Разова міграція: розбиває стару стрічку news.html (записи через <hr>) на окремі сторінки
htdocs/news/<дата>-<назва>.html з датою та нормальною розміткою. Після неї запустіть
tools/build_layout.py — він загорне сторінки в шаблон і збере список новин.

Дати й заголовки звірено вручну з текстом, заголовками та назвами файлів фото.
"""
import html
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "htdocs"))

# індекс запису в news.html → (дата, slug, заголовок). Дата: РРРР-ММ-ДД, РРРР-ММ, РРРР або "" (невідома).
ITEMS = {
	0: ("2026-09-18", "zdorove-kharchuvannia", "Здорове харчування — щоденна турбота про здоров’я, розвиток і добробут наших дітей"),
	1: ("2026-09", "osvitnii-protses-u-voiennyi-stan", "Організація освітнього процесу в умовах воєнного стану: безпека, гнучкість та безперервність навчання"),
	2: ("2026-09-01", "den-znan", "День знань 2026"),
	3: ("2026-08-30", "pidhotovka-do-navchalnoho-roku", "Трипільський НРЦ готується до нового навчального року"),
	4: ("2026-05-29", "vypusk-2026", "Випуск 2026"),
	5: ("2026-03-10", "shevchenkivske-sviato", "«Думи, мої думи…»: свято пам’яті Тараса Шевченка"),
	6: ("2025-12-12", "novorichne-sviato", "Новорічне свято «Вовк та семеро козенят на новий лад»"),
	7: ("2025-12-06", "den-sviatoho-mykolaia", "День святого Миколая 2025"),
	8: ("2025-12", "den-zbroinykh-syl", "Спортивне свято до Дня Збройних Сил України"),
	9: ("2025-11-07", "tyzhden-bezpeky-zhyttiediialnosti", "Тиждень знань безпеки життєдіяльності"),
	10: ("2025-10-30", "osinnii-bal", "Осінній бал"),
	11: ("2025-10-14", "zustrich-z-lytovskymy-druziamy", "Зустріч із литовськими друзями"),
	12: ("2025-10-06", "den-kulok", "День кульок: «Гра — королева дитинства»"),
	13: ("2025-10", "den-pratsivnykiv-osvity", "День працівників освіти"),
	14: ("2025-10-01", "kozachata-zaproshuiut-na-sviato", "Козачата запрошують на свято"),
	15: ("2025-09-01", "pershe-veresnia", "Перше вересня 2025"),
	17: ("2025-08-31", "litnie-ozdorovlennia", "Літнє оздоровлення дітей у Нідерландах"),
	18: ("2025-05", "ostannii-dzvonyk", "Останній дзвоник «Дитинства світ»"),
	19: ("2025-02", "nabir-do-1-klasu", "Набір учнів до 1 класу на 2025–2026 навчальний рік"),
	20: ("2024-12-06", "den-sviatoho-mykolaia", "День святого Миколая 2024"),
	21: ("2024-11-19", "1000-dniv-viiny", "1000 днів війни: вшанування пам’яті загиблих"),
	22: ("2024-11", "pamiataiemo-vypusknykiv", "Пам’ятаємо наших випускників-захисників"),
	23: ("2024-10-01", "tyzhden-kozatskoi-slavy", "Тиждень козацької слави"),
	24: ("2024-09-02", "pershyi-dzvonyk", "Перший дзвоник «З Україною в серці»"),
	25: ("2024-05", "ostannii-dzvonyk", "Останній дзвоник 2024"),
	26: ("2024-05-02", "velykden", "Великдень 2024"),
	27: ("2024", "nabir-do-1-klasu", "Набір учнів до 1 класу на 2024–2025 навчальний рік"),
	28: ("", "pryvitannia-imenynnykiv", "Привітання іменинників"),
	29: ("2023-09-29", "sviato-zolotoi-oseni", "Свято «Золотої осені»"),
	30: ("2023-09-01", "pershe-veresnia", "Перше вересня 2023"),
	31: ("2023-05-29", "ostannii-dzvonyk", "Останній дзвоник 2023"),
}
# 16 — обкладинка-розділювач «Шкільне життя 2025–2026 н.р.», 32–33 — посилання на архів

# Заголовки, що завершують підрозділ і повертаються на рівень h2
H2_FORCE = {"Безпека, комфорт і турбота — наші пріоритети"}

# Невідома дата: ключ сортування, щоб запис лишився на своєму місці в стрічці
SORT_FALLBACK = {28: "2023-12-31"}

# Текст оголошення, яке на сайті було лише картинкою (оголошення.jpg)
ANNOUNCEMENT_2024 = '''<p>Шановні батьки майбутніх першокласників! КЗ КОР «Трипільський навчально-реабілітаційний центр» проводить набір учнів до 1 класу на 2024–2025 навчальний рік. Запрошуємо ваших дітей у захопливу подорож до шкільного світу.</p>
<h2>Список необхідних документів</h2>
<ul>
<li>заява батьків про зарахування;</li>
<li>висновок інклюзивно-ресурсного центру про комплексну оцінку розвитку;</li>
<li>медичні документи (№ 086-1/о, № 063/о);</li>
<li>висновок психіатра;</li>
<li>копія свідоцтва про народження;</li>
<li>копія паспорта одного з батьків;</li>
<li>документ про місце проживання.</li>
</ul>
<h2>Контакти</h2>
<p>Корх Тамара Олександрівна, телефон <a href="tel:+380457233236">(04572) 33-2-36</a>, ел. пошта <a href="mailto:trypillia.internat@gmail.com">trypillia.internat@gmail.com</a>.</p>'''

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍⭐⬆↔-⇿]+")
INLINE_OK = re.compile(r"</?(?:a|strong|b|em|i)\b[^>]*>", re.I)


def text_only(s):
	return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def keep_inline(s):
	"""Прибирає всі теги, крім посилань і виділення."""
	keep = []
	def stash(m):
		keep.append(m.group(0))
		return "\x00%d\x00" % (len(keep) - 1)
	s = INLINE_OK.sub(stash, s)
	s = re.sub(r"<[^>]+>", " ", s)
	s = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)
	return re.sub(r"[ \t ]+", " ", s).strip()


def split_soft_lines(block):
	"""Рядки всередині блоку: новий абзац, якщо попередній закінчився реченням."""
	lines = [l.strip() for l in block.split("\n") if l.strip()]
	out = []
	for l in lines:
		prev = text_only(out[-1]) if out else ""
		starts_emoji = EMOJI.match(text_only(l))
		prev_is_heading = EMOJI.match(prev) and len(prev) <= 70 and not re.search(r"[.;,]$", prev)
		continues = re.match(r"[a-zа-яієїґ(«]", text_only(l))
		if out and continues and not prev_is_heading:
			out[-1] += " " + l
		elif out and not starts_emoji and not prev_is_heading and not re.search(r"[.!?…:;»\"”)]\s*(?:[💙💛✨]\s*)*$", prev):
			out[-1] += " " + l
		else:
			out.append(l)
	return out


def body_to_html(raw):
	raw = re.sub(r"<h[12]>.*?</h[12]>", "", raw, flags=re.S)
	raw = re.sub(r"<a\b[^>]*>\s*(<img[^>]*>)\s*</a>", r"\1", raw)
	lists = []
	def stash_ul(m):
		lists.append(m.group(0))
		return "\n\n\x01%d\x01\n\n" % (len(lists) - 1)
	raw = re.sub(r"<ul>.*?</ul>", stash_ul, raw, flags=re.S)
	raw = re.sub(r"<br\s*/?>|</?p\b[^>]*>|</?div\b[^>]*>", "\n\n", raw)
	raw = re.sub(r"<img[^>]*>", "", raw)

	lines = []
	for block in re.split(r"\n\s*\n", raw):
		lines += split_soft_lines(block)

	out, list_buf, in_section = [], [], False
	def flush():
		if list_buf:
			out.append("<ul>\n" + "\n".join("<li>%s</li>" % i for i in list_buf) + "\n</ul>")
			list_buf.clear()
	for l in lines:
		m = re.match(r"\x01(\d+)\x01$", l)
		if m:
			flush()
			ul = re.sub(r"\s*\n\s*", "\n", lists[int(m.group(1))])
			out.append(ul)
			continue
		l = keep_inline(l)
		t = text_only(l)
		if not t:
			continue
		bare = EMOJI.sub("", l).strip()
		if re.match(r"^\*\s+", l):
			list_buf.append(re.sub(r"^\*\s+", "", l))
			continue
		short = len(text_only(bare)) <= 70
		if EMOJI.match(t) and short and re.search(r"[;.]$", t) and not re.search(r"[.!?]\s", t):
			list_buf.append(bare)            # 🍽️ сніданок;  → пункт списку
			continue
		flush()
		heading = None
		if EMOJI.match(t) and short and not re.search(r"[.;,:]$", t):
			heading = bare                    # ✨ Косметичні ремонти → підзаголовок
		elif re.fullmatch(r"<(strong|b)>([^<]{3,120})</\1>", l):
			heading = re.fullmatch(r"<(strong|b)>([^<]{3,120})</\1>", l).group(2)
		if heading:
			# після «Що зроблено?» чи «Моделі…:» наступні заголовки — підрівень h3
			opens_section = heading.endswith((":", "?"))
			level = "h3" if in_section and not opens_section and heading not in H2_FORCE else "h2"
			if level == "h2":
				in_section = opens_section
			out.append("<%s>%s</%s>" % (level, heading.rstrip(":").strip(), level))
		else:
			out.append("<p>%s</p>" % l)
	flush()
	return join_stanzas(out)


def join_stanzas(blocks):
	"""Три й більше коротких рядки поспіль (вірші, контакти) — одна строфа з <br>."""
	res, run = [], []
	def flush():
		if len(run) >= 3:
			res.append("<p>" + "<br>\n".join(b[3:-4] for b in run) + "</p>")
		else:
			res.extend(run)
		run.clear()
	for b in blocks:
		if b.startswith("<p>") and len(text_only(b)) <= 60:
			run.append(b)
		else:
			flush()
			res.append(b)
	flush()
	return "\n".join(res)


def images(raw):
	return [m for m in re.findall(r'<img[^>]*src="([^"]+)"', raw)]


def main():
	src = open(os.path.join(ROOT, "news.html"), encoding="utf-8").read()
	m = re.search(r"<!-- content:start -->(.*?)<!-- content:end -->", src, re.S)
	if not m or os.path.isdir(os.path.join(ROOT, "news")):
		print("news/ вже існує або news.html не у форматі зі збірки — міграцію пропущено")
		return 1
	items = re.split(r"<hr>", m.group(1))
	os.makedirs(os.path.join(ROOT, "news"))
	used = set()
	for idx, (date, slug, title) in ITEMS.items():
		raw = items[idx]
		body = ANNOUNCEMENT_2024 if idx == 27 else body_to_html(raw)
		imgs = images(raw)
		alt = "Фото: " + title
		if idx == 27:
			alt = "Оголошення про набір до 1 класу на 2024–2025 навчальний рік (текст наведено вище)"
		gallery = ""
		if len(imgs) == 1:
			gallery = '\n<p><img src="%s" alt="%s"></p>' % (imgs[0], html.escape(alt))
		elif imgs:
			gallery = '\n<div class="gallery">\n' + "\n".join(
				'<a href="%s"><img src="%s" alt="%s"></a>' % (i, i, html.escape(alt)) for i in imgs) + "\n</div>"
		name = "%s-%s" % (date, slug) if date else slug
		while name in used:
			name += "-2"
		used.add(name)
		desc = text_only(body)
		desc = desc if len(desc) <= 160 else desc[:157].rsplit(" ", 1)[0] + "…"
		sort_key = date or SORT_FALLBACK[idx]
		page = f'''<!DOCTYPE html>
<html lang="uk">
<head>
	<meta charset="utf-8">
	<meta name="description" content="{html.escape(desc)}">
	<meta name="news-date" content="{date}">
	<meta name="news-sort" content="{sort_key}">
</head>
<body>
<!-- content:start -->
<h1>{html.escape(title)}</h1>
{body}{gallery}
<!-- content:end -->
</body>
</html>
'''
		with open(os.path.join(ROOT, "news", name + ".html"), "w", encoding="utf-8") as f:
			f.write(page)
		print("✓ news/%s.html" % name)
	return 0


if __name__ == "__main__":
	sys.exit(main())
