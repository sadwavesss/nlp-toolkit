(function () {
    const input = document.getElementById("q");
    const list = document.getElementById("suggestions");
    if (!input || !list) return;

    let items = [];
    let active = -1;
    let timer = null;
    let requestId = 0;

    function lastWord(value) {
        const match = value.match(/[а-яёa-z]+$/i);
        return match ? match[0] : "";
    }

    function close() {
        list.hidden = true;
        list.replaceChildren();
        items = [];
        active = -1;
    }

    function apply(word) {
        const value = input.value;
        input.value = value.slice(0, value.length - lastWord(value).length) + word + " ";
        close();
        input.focus();
    }

    function render() {
        list.replaceChildren();
        items.forEach((item, index) => {
            const li = document.createElement("li");
            if (index === active) li.classList.add("active");

            const word = document.createElement("span");
            word.textContent = item.word;
            li.appendChild(word);

            if (item.fuzzy) {
                const tag = document.createElement("span");
                tag.className = "suggest-tag";
                tag.textContent = "исправление";
                li.appendChild(tag);
            }

            const count = document.createElement("span");
            count.className = "suggest-count";
            count.textContent = `${item.documents} док.`;
            li.appendChild(count);

            li.addEventListener("mousedown", (event) => {
                event.preventDefault();
                apply(item.word);
            });
            list.appendChild(li);
        });
        list.hidden = items.length === 0;
    }

    input.addEventListener("input", () => {
        clearTimeout(timer);
        const word = lastWord(input.value);
        if (word.length < 2) {
            close();
            return;
        }
        timer = setTimeout(async () => {
            const id = ++requestId;
            const response = await fetch(`${input.dataset.suggestUrl}?q=${encodeURIComponent(word)}`);
            const data = await response.json();
            if (id !== requestId) return;
            items = data;
            active = -1;
            render();
        }, 150);
    });

    input.addEventListener("keydown", (event) => {
        if (list.hidden) return;
        if (event.key === "ArrowDown") {
            active = (active + 1) % items.length;
            render();
            event.preventDefault();
        } else if (event.key === "ArrowUp") {
            active = (active - 1 + items.length) % items.length;
            render();
            event.preventDefault();
        } else if ((event.key === "Enter" || event.key === "Tab") && active >= 0) {
            event.preventDefault();
            apply(items[active].word);
        } else if (event.key === "Escape") {
            close();
        }
    });

    input.addEventListener("blur", () => setTimeout(close, 100));
})();
