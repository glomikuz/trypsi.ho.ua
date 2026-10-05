#!/usr/bin/env python3
"""
Збирає сторінки сайту в єдиний шаблон за дизайн-кодом державних сайтів.

Контент кожної сторінки лежить між маркерами <!-- content:start --> і <!-- content:end -->.
Усе інше (шапка, меню, хлібні крихти, бічна навігація, підвал) генерується тут,
тож щоб змінити меню чи підвал на всіх сторінках, правте цей файл і запустіть:

    python3 tools/build_layout.py

Перший запуск також переводить старі сторінки (#mainholder) у новий формат і чистить
контент: прибирає інлайн-стилі, додає alt до зображень, тип і розмір файлів до посилань тощо.
Повторні запуски безпечні.
"""
import html
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "htdocs")
ROOT = os.path.normpath(ROOT)


def asset_version():
	"""Версія для ?v= — змінюється разом із CSS/JS, щоб браузер не брав старі файли з кешу."""
	return str(int(max(os.path.getmtime(os.path.join(ROOT, f)) for f in ("css/style.css", "js/site.js"))))

ORG_NAME = "Трипільський навчально-реабілітаційний центр"
ORG_FULL = "КЗ КОР «Трипільський навчально-реабілітаційний центр»"
ORG_OWNER = "Комунальний заклад Київської обласної ради"
ORG_SHORT = "Трипільський НРЦ"
ADDRESS = "08722, Київська обл., Обухівський р-н, с. Трипілля, вул. Замкова, 1-Б"
PHONE_TEXT = "(04572) 33-2-36"
PHONE_TEL = "+380457233236"
EMAIL = "trypillia.internat@gmail.com"

# (назва, файл, [(назва, файл), ...])
MENU = [
	("Головна", "index.html", []),
	("Про нас", "about.html", [
		("Історія", "history.html"),
		("Адміністрація", "staff.html"),
		("Педагогічний колектив", "staff2.html"),
		("Документи для зарахування", "docs.html"),
		("Матеріальна база", "mat_baza.html"),
		("Партнерство та співпраця", "partnership.html"),
		("Безпечне освітнє середовище", "bezpeka.html"),
		("Організація освітнього процесу в умовах воєнного стану", "voienny_stan.html"),
	]),
	("Освітній процес", "edu.html", [
		("Організація освітнього процесу", "org_osvit.html"),
		("Корекційно-розвиткова робота", "correct.html"),
		("Індивідуальна програма розвитку", "ipr.html"),
		("Учнівське самоврядування", "child_organization.html"),
		("Національно-патріотичне виховання", "nacional_patriot.html"),
		("Бібліотека", "library.html"),
		("Мережа класів", "mereg_class.html"),
		("Режим роботи", "reg_rob.html"),
		("Розклад уроків", "rozklad.html"),
		("Гуртки", "child_club.html"),
		("Розклад гуртків", "rozklad_club.html"),
	]),
	("Здоров’я", "health.html", []),
	("Традиції", "tradition.html", []),
	("Прозорість", "prozorist.html", [
		("Статут", "statut.html"),
		("Освітні програми", "odvit_prog.html"),
		("Ліцензований обсяг", "ptog_pot.html"),
		("Вакансії", "vacation.html"),
		("Матеріально-технічне забезпечення", "mat_baza.html"),
		("Річний звіт", "report.html"),
		("Кошторис і фінансовий звіт", "koshtoris.html"),
		("Благодійна допомога", "blago.html"),
		("Організація харчування", "dining.html"),
		("Положення про запобігання та протидію насильству та жорстокому поводженню з дітьми", "nasylstvo.html"),
		("Моніторинг якості освіти", "monitoring.html"),
		("Умови доступності", "dostupnist.html"),
		("Правила поведінки здобувачів освіти", "rules.html"),
		("Положення про дистанційне навчання", "dystant.html"),
		("Плата за навчання та додаткові освітні послуги", "plata.html"),
		("Порядок зарахування, відрахування та переведення учнів", "zarahuvannia.html"),
	]),
	("Антикорупція", "anti_corr_program.html", [
		("Антикорупційна програма", "anti_corr_program.html"),
		("Контактні дані", "anti_corr_contact.html"),
		("План діяльності", "anti_corr_plan.html"),
		("Звітність", "anti_corr_zvit.html"),
	]),
	("Новини", "news.html", []),
	("Галерея", "gallery.html", []),
	("Контакти", "address.html", []),
]

# Сторінки поза меню: до якого розділу їх віднести у хлібних крихтах
EXTRA_PARENT = {
	"metod_work.html": "edu.html",
	"bulling.html": "prozorist.html",
	"osvit.html": "prozorist.html",
	"status.html": "about.html",
	"anti_corr.html": "anti_corr_program.html",
	"dblago.html": "prozorist.html",
	"news_old.html": "news.html",
	"codex.html": "prozorist.html",
}

EXTERNAL_LINKS = [
	("Кабінет Міністрів України", "https://www.kmu.gov.ua/"),
	("Міністерство освіти і науки України", "https://mon.gov.ua/"),
	("Київська обласна військова адміністрація", "https://koda.gov.ua/"),
	("Департамент освіти і науки Київської ОВА", "https://www.kyiv-oblosvita.gov.ua/"),
	("Національне агентство з питань запобігання корупції", "https://nazk.gov.ua/uk/"),
	("Педагогічна преса", "https://pedpresa.com/"),
	("Державна служба якості освіти України", "https://sqe.gov.ua/"),
	("Інститут спеціальної педагогіки і психології імені Миколи Ярмаченка НАПН України", "https://ispukr.org.ua/"),
	("Законодавство України — Верховна Рада України", "https://zakon.rada.gov.ua/laws/main"),
]

ICON_A11Y = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="2"/>'
	'<circle cx="12" cy="6.5" r="1.75" fill="currentColor"/><path d="M6.5 9.25 12 10.5l5.5-1.25M12 10.5v3.5m0 0-2.5 5m2.5-5 2.5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')
ICON_MENU = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
ICON_CHEVRON = '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="m3 6 5 5 5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ICON_EXT = '<svg class="ext-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="M9 2h5v5M14 2 7 9M12 10v4H2V4h4" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/></svg>'
EXT_SUFFIX = ICON_EXT + '<span class="visually-hidden"> (відкриється в новій вкладці)</span>'

PARENT = {}
SIBLINGS = {}
TITLES = {}
for _name, _href, _subs in MENU:
	TITLES.setdefault(_href, _name)
	for _sname, _shref in _subs:
		PARENT.setdefault(_shref, _href)
		SIBLINGS.setdefault(_shref, _href)
		TITLES.setdefault(_shref, _sname)
	if _subs:
		SIBLINGS[_href] = _href
PARENT.update({k: v for k, v in EXTRA_PARENT.items() if k not in PARENT})


def esc(s):
	return html.escape(s, quote=True)


def strip_tags(s):
	return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


# ---------------------------------------------------------------- витяг зі старих сторінок

def balanced_div(src, start):
	"""Повертає (inner, end) для <div ...> що починається на позиції start."""
	open_end = src.index(">", start) + 1
	depth, i = 1, open_end
	tag = re.compile(r"<(/?)div\b[^>]*>", re.I)
	while depth:
		m = tag.search(src, i)
		if not m:
			return src[open_end:], len(src)
		depth += -1 if m.group(1) else 1
		i = m.end()
	return src[open_end:m.start()], i


def find_div(src, cls):
	m = re.search(r'<div[^>]*class="%s"[^>]*>' % re.escape(cls), src)
	if not m:
		return None
	return balanced_div(src, m.start())[0]


def extract_old(src):
	m = re.search(r'<div id="mainholder">', src)
	region = src[m.end():]
	for cls in ("Content3Column", "Content2Column", "Content1Column"):
		inner = find_div(region, cls)
		if inner is not None:
			return inner
	raise ValueError("контент не знайдено")


def extract_new(src):
	m = re.search(r"<!-- content:start -->\n?(.*?)\n?<!-- content:end -->", src, re.S)
	return m.group(1) if m else None


def meta_description(src):
	m = re.search(r'<meta name="description" content="([^"]*)"', src)
	return html.unescape(m.group(1)) if m else ""


# ---------------------------------------------------------------- чистка контенту

def file_size_label(href):
	path = os.path.join(ROOT, html.unescape(href).split("?")[0].lstrip("./"))
	if not os.path.isfile(path):
		return None
	size = os.path.getsize(path)
	if size >= 1024 * 1024:
		return ("%.1f МБ" % (size / 1024 / 1024)).replace(".", ",")
	return "%d КБ" % max(1, round(size / 1024))


ABBR = {"НРЦ", "ІПР", "КЗ", "КОР", "КЗКОР", "ІРЦ", "НУШ", "ЗСУ", "МОН", "НАПН", "ОВА", "ПМПК", "ЗСО", "ЗНО", "НМТ", "РАС", "ЗВО"}


def sentence_case(text):
	"""«ІНДИВІДУАЛЬНИЙ ПІДХІД — ОСНОВА» → «Індивідуальний підхід — основа»; абревіатури лишаються."""
	words = re.split(r"(\W+)", text.lower())
	out, first = [], True
	for w in words:
		if w.upper() in ABBR:
			out.append(w.upper())
		elif first and any(c.isalpha() for c in w):
			out.append(w[0].upper() + w[1:])
		else:
			out.append(w)
		if any(c.isalpha() for c in w):
			first = False
	return "".join(out)


def fix_headings(c):
	c = re.sub(r"<(h[1-6])>\s*<(?:strong|b)>(.*?)</(?:strong|b)>\s*</\1>", r"<\1>\2</\1>", c, flags=re.S)
	c = re.sub(r"<(h[1-6])>\s*(.*?)\s*</\1>", r"<\1>\2</\1>", c, flags=re.S)
	def caps(m):
		t = m.group(2)
		letters = [ch for ch in t if ch.isalpha()]
		if len(letters) > 6 and sum(ch.isupper() for ch in letters) / len(letters) > 0.8:
			t = sentence_case(t)
		return "<%s>%s</%s>" % (m.group(1), t, m.group(1))
	c = re.sub(r"<(h[1-6])>([^<]+)</\1>", caps, c)
	# підзаголовок одразу після h1 — це вступний абзац, а не заголовок
	# «Організація освітнього процесу» + «у КЗКОР …» з малої літери — одне речення
	c = re.sub(r"(<h1>[^<]*?)\s*</h1>\s*<h3>\s*([a-zа-яієїґ][^<]*)</h3>", r"\1 \2</h1>", c, count=1)
	if re.search(r"<h2\b", c):
		c = re.sub(r"(</h1>\s*)<h3>(.*?)</h3>", r'\1<p class="lead">\2</p>', c, count=1, flags=re.S)
	else:
		c = re.sub(r"<(/?)h3>", r"<\1h2>", c)
	return c


def clean_content(c, page_title):
	# центровані абзаци з одним <strong> — фактично заголовки новин
	c = re.sub(r'<p[^>]*text-align:\s*center[^>]*>\s*<strong>([^<]{3,200})</strong>\s*</p>',
		lambda m: "<h2>%s</h2>" % m.group(1).strip(), c)
	# <h2><p>Ім'я</p></h2> → <h2>Ім'я</h2>
	c = re.sub(r"<(h[1-6])>\s*<p[^>]*>(.*?)</p>\s*</\1>", r"<\1>\2</\1>", c, flags=re.S)
	c = re.sub(r"</?center>", "", c)
	# інлайн-стилі та застарілі атрибути
	c = re.sub(r'<iframe\b([^>]*?)"(?=width)', r'<iframe\1" ', c)
	c = re.sub(r'\s+style\s*=\s*"[^"]*"', "", c)
	c = re.sub(r"\s+style\s*=\s*'[^']*'", "", c)
	c = re.sub(r'\s+(?:border|align|frameborder|valign|bgcolor)\s*=\s*"?[^"\s>]*"?', "", c)
	c = re.sub(r'\s+(?:width|height)\s*=\s*"?[\d.]+(?:%|px)"?', "", c)
	c = re.sub(r'\s+class="(?:HTXT|Mso[^"]*|img-welcome)"', "", c)
	c = re.sub(r"<span>\s*(?:&nbsp;)?\s*</span>", "", c)
	prev = None
	while prev != c:
		prev = c
		c = re.sub(r"<span>((?:(?!</?span)[\s\S])*)</span>", r"\1", c)
	c = re.sub(r'(<iframe\b)(?![^>]*\btitle=)', r'\1 title="Вбудований документ"', c)
	c = re.sub(r'(<iframe\b[^>]*src="[^"]*maps[^"]*")', lambda m: m.group(1).replace('title="Вбудований документ"', 'title="Карта: як нас знайти"'), c)
	c = re.sub(r"\s+allowfullscreen(?=[\s>])", "", c)
	c = c.replace('href="http://trypsi.ho.ua"', 'href="./index.html"')
	c = re.sub(r"<p>\s*</p>\s*", "", c)
	c = re.sub(r"(<img\b[^>]*?)\s*/>", r"\1>", c)

	# alt для зображень: найближчий попередній заголовок
	out, last_heading, pos = [], page_title, 0
	for m in re.finditer(r"<h[1-3][^>]*>(.*?)</h[1-3]>|<img\b[^>]*>", c, re.S):
		out.append(c[pos:m.start()])
		tok = m.group(0)
		if tok.startswith("<h"):
			last_heading = strip_tags(m.group(1)) or last_heading
		elif not re.search(r'\salt="[^"]+"', tok):
			alt = "Фото: " + last_heading
			if len(alt) > 120:
				alt = alt[:117].rsplit(" ", 1)[0] + "…"
			tok = re.sub(r'\salt="[^"]*"', "", tok)
			tok = tok.replace("<img", '<img alt="%s"' % esc(alt), 1)
		if tok.startswith("<img") and "loading=" not in tok:
			tok = tok.replace("<img", '<img loading="lazy"', 1)
		out.append(tok)
		pos = m.end()
	out.append(c[pos:])
	c = "".join(out)

	# галерея (колишній fancybox)
	def gallery(m):
		links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*(<img[^>]*>)\s*</a>', m.group(0))
		return '<div class="gallery">\n' + "\n".join(
			'<a href="%s">%s</a>' % (h, i) for h, i in links) + "\n</div>"
	c = re.sub(r"<p\s*>\s*(?:<a class=\"fancybox\"[^>]*>\s*<img[^>]*>\s*</a>\s*)+(?:</p>)?", gallery, c)
	c = re.sub(r'\s+class="fancybox"|\s+rel="gallery1"', "", c)

	# кілька фото поспіль → сітка з переглядом
	img_p = r'<p\s*>\s*(?:<a href="[^"]+">\s*)?<img[^>]*>\s*(?:</a>\s*)?</p>\s*(?:</p>\s*)*'
	def photo_row(m):
		items = []
		for im in re.finditer(r'(?:<a href="([^"]+)">\s*)?(<img[^>]*>)', m.group(0)):
			src = re.search(r'src="([^"]+)"', im.group(2)).group(1)
			items.append('<a href="%s">%s</a>' % (im.group(1) or src, im.group(2)))
		return '<div class="gallery">\n' + "\n".join(items) + "\n</div>\n"
	c = re.sub(r"(?:%s){2,}" % img_p, photo_row, c)

	# зовнішні посилання: нова вкладка + позначка
	def ext(m):
		a, body = m.group(1), m.group(2)
		if "ext-icon" in body or "<img" in body:
			return m.group(0)
		if "target=" not in a:
			a = a[:-1] + ' target="_blank">'
		if "rel=" not in a:
			a = a[:-1] + ' rel="noopener">'
		return a + body + EXT_SUFFIX + "</a>"
	c = re.sub(r'(<a\b[^>]*href="https?://[^"]+"[^>]*>)(.*?)</a>', ext, c, flags=re.S)

	# документи: тип і розмір
	def doc(m):
		href, body, tail = m.group(2), m.group(3), m.group(4)
		if "<img" in body or "file-meta" in tail:
			return m.group(0)
		ext_ = href.rsplit(".", 1)[-1].upper().replace("DOCX", "DOC")
		size = file_size_label(href)
		label = "%s, %s" % (ext_, size) if size else ext_
		return '%s%s</a> <span class="file-meta">(%s)</span>%s' % (m.group(1), body, label, tail)
	c = re.sub(r'(<a\b[^>]*href="([^"]+\.(?:pdf|docx?|xlsx?))"[^>]*>)(.*?)</a>( ?<span class="file-meta"|)', doc, c, flags=re.S | re.I)

	# абзац, у якому лише посилання на документ, — картка документа
	c = re.sub(r'<p>\s*(<a\b[^>]*href="[^"]+\.(?:pdf|docx?|xlsx?)"[^>]*>[^<]*</a>)\s*(<span class="file-meta">[^<]*</span>)\s*</p>',
		r'<p class="doc">\1 \2</p>', c, flags=re.I)
	# таблиці — у контейнер із горизонтальною прокруткою на вузьких екранах
	c = re.sub(r"(?<!<div class=\"table-wrap\">)(<table\b.*?</table>)", r'<div class="table-wrap">\1</div>', c, flags=re.S)
	c = fix_headings(c)
	c = re.sub(r"\n{3,}", "\n\n", c)
	return c.strip()


def page_h1(c, fallback):
	m = re.search(r"<h1[^>]*>(.*?)</h1>", c, re.S)
	return strip_tags(m.group(1)) if m else fallback


# ---------------------------------------------------------------- шаблон

def nav_html(current):
	section = PARENT.get(current, current)
	items = []
	for i, (name, href, subs) in enumerate(MENU):
		active = href == current or href == section
		cur = ' aria-current="page"' if href == current else ""
		cls = ' class="nav-item is-active"' if active else ' class="nav-item"'
		if subs:
			sub_items = "\n".join(
				'\t\t\t\t\t<li><a href="./%s"%s>%s</a></li>' % (h, ' aria-current="page"' if h == current else "", esc(n))
				for n, h in subs)
			items.append(
				'\t\t\t<li>\n\t\t\t\t<div%s><a class="nav-link" href="./%s"%s>%s</a>'
				'<button type="button" class="sub-toggle" aria-expanded="false" aria-controls="sub-%d">'
				'<span class="visually-hidden">Підрозділи: %s</span>%s</button></div>\n'
				'\t\t\t\t<ul class="submenu" id="sub-%d">\n%s\n\t\t\t\t</ul>\n\t\t\t</li>'
				% (cls, href, cur, esc(name), i, esc(name), ICON_CHEVRON, i, sub_items))
		else:
			items.append('\t\t\t<li><div%s><a class="nav-link" href="./%s"%s>%s</a></div></li>' % (cls, href, cur, esc(name)))
	return "\n".join(items)


def header_html(current):
	return f'''<a class="skip-link" href="#content">Перейти до основного вмісту</a>
<header class="site-header">
	<div class="container header-top">
		<a class="brand" href="./index.html"{' aria-current="page"' if current == "index.html" else ""}>
			<img class="brand-gerb" src="./assets/gerb.svg" alt="Малий Державний Герб України" width="40" height="56">
			<span class="brand-divider" aria-hidden="true"></span>
			<img class="brand-logo" src="./image/logo2.png" alt="" width="58" height="50">
			<span class="brand-text">
				<span class="brand-owner">{esc(ORG_OWNER)}</span>
				<span class="brand-name">{esc(ORG_NAME)}</span>
			</span>
		</a>
		<div class="header-actions">
			<button type="button" class="btn a11y-toggle" aria-expanded="false" aria-controls="a11y-panel">{ICON_A11Y}<span class="btn-label">Доступність</span><span class="visually-hidden"> — налаштування для людей з порушенням зору</span></button>
			<button type="button" class="btn menu-toggle" aria-expanded="false" aria-controls="main-nav">{ICON_MENU}<span class="btn-label">Меню</span></button>
		</div>
	</div>
	<section class="a11y-panel" id="a11y-panel" aria-labelledby="a11y-title" hidden>
		<div class="container">
			<h2 id="a11y-title" tabindex="-1">Налаштування доступності</h2>
			<div class="a11y-groups">
				<fieldset class="a11y-group">
					<legend>Розмір тексту</legend>
					<button type="button" class="btn" data-font-set="0" aria-pressed="true">A<span class="visually-hidden"> — звичайний</span></button><button type="button" class="btn" data-font-set="1" aria-pressed="false">A+<span class="visually-hidden"> — більший</span></button><button type="button" class="btn" data-font-set="2" aria-pressed="false">A++<span class="visually-hidden"> — найбільший</span></button>
				</fieldset>
				<fieldset class="a11y-group">
					<legend>Відображення</legend>
					<button type="button" class="btn" data-pref="contrast" aria-pressed="false">Висока контрастність</button><button type="button" class="btn" data-pref="underline" aria-pressed="false">Підкреслити посилання</button>
				</fieldset>
				<fieldset class="a11y-group">
					<legend>Інше</legend>
					<button type="button" class="btn" data-reset>Скинути</button>
					<a class="btn" href="./dostupnist.html">Умови доступності закладу</a>
				</fieldset>
			</div>
		</div>
	</section>
	<nav class="main-nav" id="main-nav" aria-label="Головне меню">
		<div class="container">
		<ul>
{nav_html(current)}
		</ul>
		</div>
	</nav>
</header>'''


def footer_html():
	links = [("Про нас", "about.html"), ("Освітній процес", "edu.html"), ("Новини", "news.html"),
		("Прозорість", "prozorist.html"), ("Антикорупція", "anti_corr_program.html"),
		("Умови доступності", "dostupnist.html"), ("Вакансії", "vacation.html"), ("Контакти", "address.html")]
	li = "\n".join('\t\t\t\t\t<li><a href="./%s">%s</a></li>' % (h, esc(n)) for n, h in links)
	return f'''<footer class="site-footer">
	<div class="container">
		<div class="footer-grid">
			<section class="footer-contacts" aria-labelledby="footer-contacts-title">
				<div class="footer-brand">
					<img src="./image/logo2.png" alt="" width="72" height="62">
					<h2 id="footer-contacts-title">{esc(ORG_FULL)}</h2>
				</div>
				<p>{esc(ADDRESS)}</p>
				<p>Телефон/факс: <a href="tel:{PHONE_TEL}">{PHONE_TEXT}</a></p>
				<p>Ел. пошта: <a href="mailto:{EMAIL}">{EMAIL}</a></p>
			</section>
			<nav class="footer-links" aria-labelledby="footer-links-title">
				<h2 id="footer-links-title">Розділи сайту</h2>
				<ul>
{li}
				</ul>
			</nav>
		</div>
	</div>
</footer>'''


def breadcrumbs_html(current, h1):
	crumbs = [("Головна", "index.html")]
	parent = PARENT.get(current)
	if parent and parent != current:
		crumbs.append((TITLES.get(parent, parent), parent))
	items = "".join('<li><a href="./%s">%s</a></li>' % (h, esc(n)) for n, h in crumbs)
	items += '<li><span aria-current="page">%s</span></li>' % esc(h1)
	return '<nav class="breadcrumbs" aria-label="Ви тут"><ol>%s</ol></nav>' % items


def section_nav_html(current):
	section = SIBLINGS.get(current)
	if not section:
		return ""
	name, href, subs = next(m for m in MENU if m[1] == section)
	lis = "\n".join('\t\t\t\t<li><a href="./%s"%s>%s</a></li>' % (h, ' aria-current="page"' if h == current else "", esc(n)) for n, h in subs)
	return f'''
			<nav class="section-nav" aria-labelledby="section-nav-title">
				<h2 id="section-nav-title">{esc(name)}</h2>
				<ul>
{lis}
				</ul>
			</nav>'''


def page_html(current, title, description, content, top="", bottom="", aside=None, doc_title=None):
	is_home = current == "index.html"
	h1 = page_h1(content, title)
	if doc_title is None:
		doc_title = "%s — %s" % (ORG_FULL, "Головна") if is_home else "%s — %s" % (h1, ORG_SHORT)
	if is_home:
		main = f'''<main id="content" tabindex="-1">
<!-- content:start -->
{content}
<!-- content:end -->
</main>'''
	else:
		if aside is None:
			aside = section_nav_html(current)
		main = f'''<main id="content" tabindex="-1">
	<div class="container">
		{breadcrumbs_html(current, h1)}
		<div class="page{' has-aside' if aside else ''}">
			<article class="content prose">{top}
<!-- content:start -->
{content}
<!-- content:end -->{bottom}
			</article>{aside}
		</div>
	</div>
</main>'''
	return f'''<!DOCTYPE html>
<html lang="uk">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{esc(doc_title)}</title>
	<meta name="description" content="{esc(description)}">
	<link rel="icon" href="./assets/gerb.svg" type="image/svg+xml">
	<link rel="preload" href="./assets/fonts/e-Ukraine-Regular.woff2" as="font" type="font/woff2" crossorigin>
	<link rel="stylesheet" href="./css/style.css?v={asset_version()}">
	<script>try{{var p=JSON.parse(localStorage.getItem("trypsi-a11y"))||{{}};var r=document.documentElement;r.dataset.font=p.font||"0";if(p.contrast)r.dataset.contrast="high";if(p.underline)r.dataset.underline="on"}}catch(e){{}}</script>
	<script src="./js/site.js?v={asset_version()}" defer></script>
</head>
<body>
{header_html(current)}
{main}
{footer_html()}
</body>
</html>
'''


# ---------------------------------------------------------------- головна та «Прозорість»

def build_home_content(src):
	welcome = find_div(src, "Content3Column")
	welcome = re.sub(r"<h1>.*?</h1>", "", welcome, flags=re.S)
	welcome = re.sub(r"<p>\s*<img[^>]*>\s*</p>", "", welcome)
	welcome = clean_content(welcome, ORG_NAME)
	welcome = re.sub(r"<(/?)h2>", r"<\1h3>", welcome)   # підрозділи всередині «Про Центр»
	welcome = re.sub(r"^\s*<p>(.*?)</p>", "", welcome, count=1, flags=re.S)   # перший абзац іде в лід

	cards = [
		("Освітня програма", "Чого і як навчаються діти в Центрі", "./odvit_prog.html"),
		("Документи для зарахування", "Що потрібно, щоб дитина почала навчання", "./docs.html"),
		("Розклад уроків", "Розклад на поточний навчальний рік", "./rozklad.html"),
		("Новини", "Події та життя Центру", "./news.html"),
		("Звіт директора", "Річний звіт про діяльність закладу", "./report.html"),
		("Стоп булінг", "Як ми запобігаємо цькуванню і куди звернутися", "./bulling.html"),
		("Методична робота", "Педагогічна тема та професійний розвиток", "./metod_work.html"),
		("Прозорість", "Статут, кошторис, звіти та інші документи", "./prozorist.html"),
	]
	cards_html = "\n".join(
		f'\t\t\t<li class="card"><h3><a href="{h}">{esc(t)}</a></h3><p>{esc(d)}</p></li>' for t, d, h in cards)
	links_html = "\n".join(
		f'\t\t\t\t\t<li><a href="{h}" target="_blank" rel="noopener">{esc(n)}{EXT_SUFFIX}</a></li>' for n, h in EXTERNAL_LINKS)

	return f'''<section class="hero">
	<div class="container hero-grid">
		<div class="hero-text">
			<h1>{esc(ORG_NAME)}</h1>
			<p class="hero-lead">Наш Центр — це простір, у якому навчання поєднується з корекційно-розвитковою та реабілітаційною роботою, турботою про здоров’я, безпеку, емоційний добробут і формування життєвої самостійності дитини.</p>
			<div class="hero-actions">
				<a class="btn btn-primary" href="./docs.html">Як вступити до Центру</a>
				<a class="btn" href="./address.html">Контакти</a>
			</div>
		</div>
		<div class="hero-media">
			<img src="./image/image001.jpg" alt="Головний корпус Центру та шкільне подвір’я з алеєю берез" width="1280" height="410">
		</div>
	</div>
</section>

<div class="container">
	<section class="home-section" aria-labelledby="quick-title">
		<h2 id="quick-title">Швидкий доступ</h2>
		<ul class="cards">
{cards_html}
		</ul>
	</section>

	<div class="home-section home-layout">
		<section class="content prose" aria-labelledby="about-title">
			<h2 id="about-title">Про Центр</h2>
{welcome}
		</section>
		<nav class="links" aria-labelledby="links-title">
			<h2 id="links-title">Корисні посилання</h2>
			<ul>
{links_html}
			</ul>
		</nav>
	</div>
</div>'''


def build_section_index(section_href):
	name, href, subs = next(m for m in MENU if m[1] == section_href)
	lis = "\n".join('<li class="card"><h2><a href="./%s">%s</a></h2></li>' % (h, esc(n)) for n, h in subs)
	return f'''<h1>{esc(name)}</h1>
<p class="lead">Інформація про діяльність закладу та документи, які заклад освіти оприлюднює відповідно до статті 30 Закону України «Про освіту».</p>
<ul class="cards">
{lis}
</ul>'''


# ---------------------------------------------------------------- запуск

# ---------------------------------------------------------------- слайдер на головній

SLIDES = [
	("image/image001.jpg", "Головний корпус Центру та шкільне подвір’я з алеєю берез"),
	("image/slider/image_01.jpg", "Педагогиня грається з учнями м’якими іграшками в ігровій кімнаті"),
	("image/slider/image_02.jpg", "Учні виконують гімнастичні вправи у спортивній залі"),
	("image/slider/image_03.jpg", "Дівчинки грають на сопілці на уроці музики"),
	("image/slider/image_04.jpg", "Хлопчик грається з розвивальним лабіринтом із намистинами"),
	("image/slider/image_05.jpg", "Діти відпочивають серед м’яких модулів у сенсорній кімнаті"),
	("image/slider/image_06.jpg", "Хлопчик обідає в їдальні Центру"),
	("image/slider/image_07.jpg", "Стіна ігрової кімнати з усміхненим сонечком"),
	("image/slider/image_08.jpg", "Педагогиня займається з групою хлопчиків за столом"),
	("image/slider/image_09.jpg", "Учні з м’ячами та обручами на занятті з фізкультури"),
	("image/slider/image_10.jpg", "Хлопчик грає в лікаря зі стетоскопом і лялькою"),
	("image/slider/image_11.jpg", "Учні на занятті в класі"),
	("image/slider/image_12.jpg", "Хлопчики працюють за комп’ютером у класі"),
]


def slider_html():
	n = len(SLIDES)
	slides = "\n".join(
		'\t\t\t\t<li class="slide%s" aria-roledescription="слайд" aria-label="%d з %d"><img src="./%s" alt="%s" width="990" height="330"%s></li>'
		% (" is-active" if i == 0 else "", i + 1, n, src, esc(alt), "" if i == 0 else ' loading="lazy"')
		for i, (src, alt) in enumerate(SLIDES))
	dots = "".join(
		'<button type="button" class="slider-dot" data-go="%d" aria-label="Фото %d"%s></button>' % (i, i + 1, ' aria-current="true"' if i == 0 else "")
		for i in range(n))
	return f'''<!-- slider:start -->
		<section class="slider" aria-roledescription="карусель" aria-label="Фото з життя Центру">
			<ul class="slider-track" aria-live="off">
{slides}
			</ul>
			<div class="slider-controls" hidden>
				<button type="button" class="slider-btn slider-toggle" aria-label="Зупинити показ"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path class="i-pause" d="M8 5v14M16 5v14" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><path class="i-play" d="M8 5l11 7-11 7z" fill="currentColor"/></svg></button>
				<div class="slider-dots">{dots}</div>
				<button type="button" class="slider-btn" data-step="-1" aria-label="Попереднє фото"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m15 5-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
				<button type="button" class="slider-btn" data-step="1" aria-label="Наступне фото"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
			</div>
		</section>
		<!-- slider:end -->'''


# ---------------------------------------------------------------- новини

NEWS_DIR = "news"
NEWS_PER_PAGE = 10
DEFAULT_NEWS_IMAGE = "./assets/news-default.svg"   # обкладинка для новин без фото
MONTHS_GEN = ["січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]
MONTHS_NOM = ["Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень", "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"]


def format_date(d):
	"""2026-09-18 → «18 вересня 2026», 2026-09 → «Вересень 2026», 2024 → «2024»."""
	parts = d.split("-") if d else []
	if len(parts) == 3:
		return "%d %s %s" % (int(parts[2]), MONTHS_GEN[int(parts[1]) - 1], parts[0])
	if len(parts) == 2:
		return "%s %s" % (MONTHS_NOM[int(parts[1]) - 1], parts[0])
	return d


def meta(src, name):
	m = re.search(r'<meta name="%s" content="([^"]*)"' % name, src)
	return html.unescape(m.group(1)) if m else ""


def thumbnail(src):
	"""Зменшена копія фото для списку новин (macOS sips). Без sips — оригінал."""
	if not src:
		return ""
	rel = src[2:] if src.startswith("./") else src
	orig = os.path.join(ROOT, rel)
	name = re.sub(r"[^A-Za-z0-9._-]+", "-", rel.rsplit(".", 1)[0]).strip("-") + ".jpg"
	out = os.path.join(ROOT, "image", "thumbs", name)
	if not os.path.exists(out) and os.path.exists(orig):
		os.makedirs(os.path.dirname(out), exist_ok=True)
		os.system('sips -Z 640 -s format jpeg -s formatOptions 75 "%s" --out "%s" >/dev/null 2>&1' % (orig, out))
	return "./image/thumbs/" + name if os.path.exists(out) else src


def load_news():
	folder = os.path.join(ROOT, NEWS_DIR)
	items = []
	for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
		if not f.endswith(".html"):
			continue
		src = open(os.path.join(folder, f), encoding="utf-8").read()
		content = re.sub(r'(href|src)="\.\./', r'\1="./', extract_new(src))   # шляхи від кореня сайту
		date = meta(src, "news-date")
		img = re.search(r'<img[^>]*src="([^"]+)"', content)
		items.append({
			"file": "%s/%s" % (NEWS_DIR, f),
			"content": content,
			"date": date,
			"sort": meta(src, "news-sort") or date,
			"title": page_h1(content, f),
			"description": meta(src, "description"),
			"image": img.group(1) if img else "",
		})
	items.sort(key=lambda n: (n["sort"], n["file"]), reverse=True)
	for n in items:
		PARENT[n["file"]] = "news.html"
	return items


def time_html(n, cls="news-date"):
	if not n["date"]:
		return ""
	return '<time class="%s" datetime="%s">%s</time>' % (cls, n["date"], format_date(n["date"]))


def news_card(n, heading="h2"):
	img = thumbnail(n["image"])
	pic = '<img src="%s" alt="" loading="lazy">' % (img or DEFAULT_NEWS_IMAGE)
	return f'''<li class="news-item">
	<div class="news-thumb">{pic}</div>
	<div class="news-body">
		{time_html(n)}
		<{heading} class="news-title"><a href="./{n["file"]}">{esc(n["title"])}</a></{heading}>
		<p class="news-excerpt">{esc(n["description"])}</p>
	</div>
</li>'''


def news_list_page_name(page):
	return "news.html" if page == 1 else "news-%d.html" % page


def pagination_html(page, pages):
	if pages < 2:
		return ""
	items = []
	if page > 1:
		items.append('<li><a href="./%s" rel="prev">← Новіші</a></li>' % news_list_page_name(page - 1))
	for p in range(1, pages + 1):
		if p == page:
			items.append('<li><span aria-current="page">%d</span></li>' % p)
		else:
			items.append('<li><a href="./%s" aria-label="Сторінка %d">%d</a></li>' % (news_list_page_name(p), p, p))
	if page < pages:
		items.append('<li><a href="./%s" rel="next">Старіші →</a></li>' % news_list_page_name(page + 1))
	return '<nav class="pagination" aria-label="Сторінки новин"><ul>%s</ul></nav>' % "".join(items)


def build_news(items):
	pages = max(1, -(-len(items) // NEWS_PER_PAGE))
	for page in range(1, pages + 1):
		chunk = items[(page - 1) * NEWS_PER_PAGE: page * NEWS_PER_PAGE]
		name = news_list_page_name(page)
		if page > 1:
			PARENT[name] = "news.html"
		cards = "\n".join(news_card(n) for n in chunk)
		archive = '\n<p class="news-archive"><a href="./news_old.html">Архів новин до 2023 року</a></p>' if page == pages else ""
		content = '<h1>Новини</h1>\n<ul class="news-list">\n%s\n</ul>\n%s%s' % (cards, pagination_html(page, pages), archive)
		title = "Новини" if page == 1 else "Новини, сторінка %d" % page
		out = page_html(name, "Новини", "Новини та події Трипільського навчально-реабілітаційного центру", content,
			aside="", doc_title="%s — %s" % (title, ORG_SHORT))
		write(name, out)
	for f in os.listdir(ROOT):   # зайві сторінки списку після видалення новин
		m = re.fullmatch(r"news-(\d+)\.html", f)
		if m and int(m.group(1)) > pages:
			os.remove(os.path.join(ROOT, f))

	for i, n in enumerate(items):
		others = [o for o in items if o is not n][:3]
		aside = '''
			<aside class="section-nav news-aside" aria-labelledby="more-news-title">
				<h2 id="more-news-title">Інші новини</h2>
				<ul>
%s
				</ul>
			</aside>''' % "\n".join(
			'\t\t\t\t<li><a href="./%s"><span class="news-aside-title">%s</span>%s</a></li>' % (o["file"], esc(o["title"]), ("<span class=\"news-aside-date\">%s</span>" % format_date(o["date"])) if o["date"] else "")
			for o in others)
		top = "\n" + time_html(n) if n["date"] else ""
		if not n["image"]:
			top += '\n<img class="news-cover" src="%s" alt="" width="1200" height="800">' % DEFAULT_NEWS_IMAGE
		bottom = '\n<p class="news-back"><a href="./news.html">← Усі новини</a></p>'
		content = clean_content(n["content"], n["title"])
		out = page_html(n["file"], n["title"], n["description"], content, top=top, bottom=bottom, aside=aside)
		out = re.sub(r'(href|src)="\./', r'\1="../', out)   # сторінка лежить у news/
		write(n["file"], out, wrap_paths=True)


def latest_news_html(items):
	cards = "\n".join(news_card(n, heading="h3") for n in items[:3])
	return f'''<!-- latest-news:start -->
	<section class="home-section" aria-labelledby="latest-news-title">
		<div class="section-head">
			<h2 id="latest-news-title">Останні новини</h2>
			<a href="./news.html">Усі новини →</a>
		</div>
		<ul class="news-list news-list--grid">
{cards}
		</ul>
	</section>
	<!-- latest-news:end -->'''


def write(name, out, wrap_paths=False):
	path = os.path.join(ROOT, name)
	if wrap_paths:
		# зберігаємо службові метадані новини, щоб наступна збірка їх прочитала
		src = open(path, encoding="utf-8").read()
		keep = "".join('\t<meta name="%s" content="%s">\n' % (k, esc(meta(src, k))) for k in ("news-date", "news-sort") if meta(src, k) or k == "news-date")
		out = out.replace("</head>", keep + "</head>", 1)
	with open(path, "w", encoding="utf-8") as f:
		f.write(out)
	print("✓", name)


def main():
	news = load_news()
	files = sorted(f for f in os.listdir(ROOT) if f.endswith(".html") and not (news and re.fullmatch(r"news(-\d+)?\.html", f)))
	if "prozorist.html" not in files:
		files.append("prozorist.html")
	for name in files:
		path = os.path.join(ROOT, name)
		src = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
		description = meta_description(src) or "Офіційний сайт: %s" % ORG_FULL
		content = extract_new(src)
		if content is None:
			if name == "index.html":
				content = build_home_content(src)
			elif name == "prozorist.html":
				content = build_section_index("prozorist.html")
				description = "Прозорість та інформаційна відкритість закладу"
			else:
				content = clean_content(extract_old(src), TITLES.get(name, ORG_NAME))
		elif name != "index.html":
			content = clean_content(content, TITLES.get(name, ORG_NAME))
		if name == "index.html":
			if "<!-- slider:start -->" in content:
				content = re.sub(r"<!-- slider:start -->.*?<!-- slider:end -->", lambda m: slider_html(), content, flags=re.S)
			else:
				content = re.sub(r'<div class="hero-media">.*?</div>', lambda m: '<div class="hero-media">\n\t\t' + slider_html() + '\n\t\t</div>', content, count=1, flags=re.S)
		if name == "index.html" and news:
			block = latest_news_html(news)
			if "<!-- latest-news:start -->" in content:
				content = re.sub(r"<!-- latest-news:start -->.*?<!-- latest-news:end -->", lambda m: block, content, flags=re.S)
			else:
				content = content.replace('\n\n\t<div class="home-section home-layout">', "\n\n\t" + block + '\n\n\t<div class="home-section home-layout">', 1)
		title = page_h1(content, TITLES.get(name, ORG_NAME))
		if "Ласкаво просимо" in description or not description:
			description = "Офіційний сайт: %s" % ORG_FULL
		# на сторінці-покажчику розділу плитки вже дублюють бічне меню
		aside = "" if name == "prozorist.html" else None
		write(name, page_html(name, title, description, content, aside=aside))
	if news:
		build_news(news)


if __name__ == "__main__":
	sys.exit(main())
