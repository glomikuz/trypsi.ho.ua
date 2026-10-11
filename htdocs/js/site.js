/* Трипільський НРЦ — меню, панель доступності, перегляд фото. Без залежностей. */
(function () {
	"use strict";

	var root = document.documentElement;
	var STORE = "trypsi-a11y";

	function loadPrefs() {
		try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch (e) { return {}; }
	}
	function savePrefs(p) {
		try { localStorage.setItem(STORE, JSON.stringify(p)); } catch (e) { /* приватний режим */ }
	}
	function applyPrefs(p) {
		root.dataset.font = p.font || "0";
		root.dataset.contrast = p.contrast ? "high" : "normal";
		root.dataset.underline = p.underline ? "on" : "off";
	}

	/* ---------- Мобільне меню ---------- */
	var nav = document.getElementById("main-nav");
	var menuBtn = document.querySelector(".menu-toggle");
	if (nav && menuBtn) {
		menuBtn.addEventListener("click", function () {
			var open = menuBtn.getAttribute("aria-expanded") !== "true";
			menuBtn.setAttribute("aria-expanded", String(open));
			menuBtn.querySelector(".btn-label").textContent = open ? "Закрити" : "Меню";
			nav.classList.toggle("is-open", open);
		});
	}

	/* ---------- Підменю ---------- */
	function closeAllSubmenus(except) {
		document.querySelectorAll(".sub-toggle[aria-expanded='true']").forEach(function (b) {
			if (b === except) return;
			b.setAttribute("aria-expanded", "false");
			b.closest("li").classList.remove("is-open");
		});
	}
	document.querySelectorAll(".sub-toggle").forEach(function (btn) {
		btn.addEventListener("click", function () {
			var open = btn.getAttribute("aria-expanded") !== "true";
			closeAllSubmenus(btn);
			btn.setAttribute("aria-expanded", String(open));
			btn.closest("li").classList.toggle("is-open", open);
		});
	});
	document.addEventListener("keydown", function (e) {
		if (e.key !== "Escape") return;
		var openBtn = document.querySelector(".sub-toggle[aria-expanded='true']");
		if (openBtn) { closeAllSubmenus(); openBtn.focus(); }
	});
	document.addEventListener("click", function (e) {
		if (!e.target.closest(".main-nav")) closeAllSubmenus();
	});
	// Підменю закривається, коли фокус клавіатури виходить за його межі
	document.querySelectorAll(".main-nav li").forEach(function (li) {
		li.addEventListener("focusout", function (e) {
			if (!li.classList.contains("is-open") || li.contains(e.relatedTarget)) return;
			var btn = li.querySelector(".sub-toggle");
			if (btn) btn.setAttribute("aria-expanded", "false");
			li.classList.remove("is-open");
		});
	});

	/* ---------- Панель доступності ---------- */
	var prefs = loadPrefs();
	applyPrefs(prefs);

	var a11yBtn = document.querySelector(".a11y-toggle");
	var panel = document.getElementById("a11y-panel");
	if (a11yBtn && panel) {
		a11yBtn.addEventListener("click", function () {
			var open = a11yBtn.getAttribute("aria-expanded") !== "true";
			a11yBtn.setAttribute("aria-expanded", String(open));
			panel.hidden = !open;
			if (open) panel.querySelector("h2").focus();
		});

		function syncButtons() {
			panel.querySelectorAll("[data-font-set]").forEach(function (b) {
				b.setAttribute("aria-pressed", String((prefs.font || "0") === b.dataset.fontSet));
			});
			panel.querySelectorAll("[data-pref]").forEach(function (b) {
				b.setAttribute("aria-pressed", String(!!prefs[b.dataset.pref]));
			});
		}
		syncButtons();

		panel.addEventListener("click", function (e) {
			var b = e.target.closest("button");
			if (!b) return;
			if (b.dataset.fontSet) prefs.font = b.dataset.fontSet;
			else if (b.dataset.pref) prefs[b.dataset.pref] = !prefs[b.dataset.pref];
			else if (b.hasAttribute("data-reset")) prefs = {};
			else return;
			applyPrefs(prefs);
			savePrefs(prefs);
			syncButtons();
		});
	}

	/* ---------- Слайдер на головній ---------- */
	var slider = document.querySelector(".slider");
	if (slider) {
		var slides = slider.querySelectorAll(".slide");
		var dots = slider.querySelectorAll(".slider-dot");
		var toggle = slider.querySelector(".slider-toggle");
		var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
		var idx = 0, timer = null, userPaused = reduce, hover = false;

		slider.querySelector(".slider-controls").hidden = false;
		function go(i) {
			slides[idx].classList.remove("is-active");
			dots[idx].removeAttribute("aria-current");
			idx = (i + slides.length) % slides.length;
			slides[idx].classList.add("is-active");
			dots[idx].setAttribute("aria-current", "true");
			var img = slides[idx].querySelector("img");
			if (img.loading === "lazy") img.loading = "eager";
		}
		function sync() {
			var run = !userPaused && !hover && !document.hidden;
			clearInterval(timer);
			timer = run ? setInterval(function () { go(idx + 1); }, 6000) : null;
			slider.classList.toggle("is-paused", userPaused);
			toggle.setAttribute("aria-label", userPaused ? "Відновити показ" : "Зупинити показ");
		}
		slider.addEventListener("click", function (e) {
			var b = e.target.closest("button");
			if (!b) return;
			if (b === toggle) userPaused = !userPaused;
			else if (b.dataset.step) { go(idx + Number(b.dataset.step)); userPaused = true; }
			else if (b.dataset.go) { go(Number(b.dataset.go)); userPaused = true; }
			sync();
		});
		/* пауза, поки користувач дивиться або працює з клавіатури */
		slider.addEventListener("mouseenter", function () { hover = true; sync(); });
		slider.addEventListener("mouseleave", function () { hover = false; sync(); });
		slider.addEventListener("focusin", function () { hover = true; sync(); });
		slider.addEventListener("focusout", function () { hover = false; sync(); });
		document.addEventListener("visibilitychange", sync);
		sync();
	}

	/* ---------- Перегляд фото в галереї ---------- */
	var links = Array.prototype.slice.call(document.querySelectorAll(".gallery a"));
	if (links.length && typeof HTMLDialogElement === "function") {
		var dlg = document.createElement("dialog");
		dlg.className = "lightbox";
		dlg.setAttribute("aria-label", "Перегляд фото");
		dlg.innerHTML =
			'<div class="lightbox-bar">' +
				'<span class="lightbox-count" aria-live="polite"></span>' +
				'<button type="button" class="btn" data-close>Закрити ✕</button>' +
			'</div>' +
			'<div class="lightbox-stage"><img alt=""></div>' +
			'<div class="lightbox-nav">' +
				'<button type="button" class="btn" data-step="-1">← Попереднє</button>' +
				'<button type="button" class="btn" data-step="1">Наступне →</button>' +
			'</div>';
		document.body.appendChild(dlg);
		var img = dlg.querySelector("img");
		var count = dlg.querySelector(".lightbox-count");
		var current = 0, opener = null;

		function show(i) {
			current = (i + links.length) % links.length;
			var thumb = links[current].querySelector("img");
			img.src = links[current].href;
			img.alt = thumb ? thumb.alt : "";
			count.textContent = "Фото " + (current + 1) + " з " + links.length;
		}
		links.forEach(function (a, i) {
			a.addEventListener("click", function (e) {
				e.preventDefault();
				opener = a;
				show(i);
				dlg.showModal();
			});
		});
		dlg.addEventListener("click", function (e) {
			var b = e.target.closest("button");
			if (b && b.dataset.step) show(current + Number(b.dataset.step));
			else if (b && b.hasAttribute("data-close")) dlg.close();
		});
		dlg.addEventListener("keydown", function (e) {
			if (e.key === "ArrowRight") show(current + 1);
			if (e.key === "ArrowLeft") show(current - 1);
		});
		dlg.addEventListener("close", function () { if (opener) opener.focus(); });
	}
})();
