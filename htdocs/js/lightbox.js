// Перегляд фото галереї у вікні поверх сторінки (замість jQuery + fancybox).
// Без JavaScript посилання просто відкривають фото в браузері.
(function () {
	var links = Array.prototype.slice.call(document.querySelectorAll("a.fancybox"));
	if (!links.length || typeof HTMLDialogElement !== "function") return;

	var dialog = document.createElement("dialog");
	dialog.className = "lightbox";
	dialog.setAttribute("aria-label", "Перегляд фото");
	dialog.innerHTML =
		'<figure><img alt=""><figcaption></figcaption></figure>' +
		'<button type="button" class="lightbox-close" aria-label="Закрити">&times;</button>' +
		'<button type="button" class="lightbox-prev" aria-label="Попереднє фото">&#8249;</button>' +
		'<button type="button" class="lightbox-next" aria-label="Наступне фото">&#8250;</button>';
	document.body.appendChild(dialog);

	var img = dialog.querySelector("img");
	var caption = dialog.querySelector("figcaption");
	var current = 0;

	function show(index) {
		current = (index + links.length) % links.length;
		var thumb = links[current].querySelector("img");
		img.src = links[current].href;
		img.alt = thumb ? thumb.alt : "";
		caption.textContent = (current + 1) + " з " + links.length;
		new Image().src = links[(current + 1) % links.length].href;
	}

	links.forEach(function (link, index) {
		link.addEventListener("click", function (event) {
			event.preventDefault();
			show(index);
			dialog.showModal();
		});
	});

	dialog.querySelector(".lightbox-close").addEventListener("click", function () { dialog.close(); });
	dialog.querySelector(".lightbox-prev").addEventListener("click", function () { show(current - 1); });
	dialog.querySelector(".lightbox-next").addEventListener("click", function () { show(current + 1); });
	dialog.addEventListener("click", function (event) {
		if (event.target === dialog) dialog.close(); // клік по затемненню
	});
	dialog.addEventListener("keydown", function (event) {
		if (event.key === "ArrowLeft") show(current - 1);
		if (event.key === "ArrowRight") show(current + 1);
	});
	dialog.addEventListener("close", function () {
		links[current].focus();
		img.removeAttribute("src");
	});
})();
