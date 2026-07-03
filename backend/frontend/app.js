/* Búsqueda Terremoto Venezuela — chat frontend "Cielo de Venezuela".
   Sin framework. Vanilla JS. Habla con /api/search.
   Incluye: cielo estrellado (canvas), sonidos (Web Audio),
   partículas tricolor, radar de búsqueda, i18n ES/EN. */

(() => {
    "use strict";

    const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // ---------- I18N ----------
    const I18N = {
        es: {
            title: "Búsqueda Terremoto Venezuela",
            subtitle: "Busca personas desaparecidas en múltiples plataformas oficiales y comunitarias.",
            disclaimer_title: "Importante:",
            disclaimer_body: "Esta es una búsqueda agregada sobre plataformas de terceros, sin base de datos propia. Verifica siempre el estado en la fuente original.",
            welcome: "Hola. Escribe el nombre (o parte del nombre) de la persona que buscas — consulto 12 plataformas a la vez. Abajo tienes el directorio de emergencia con teléfonos y portales.",
            search_label: "Buscar persona",
            search_placeholder: "Ej: María González, vista en Catia La Mar",
            send: "Buscar",
            examples_label: "Ejemplos:",
            footer: "Búsqueda federada sobre plataformas oficiales y comunitarias. Cada resultado enlaza a su fuente original.",
            powered_by: "Funciona con",
            no_match: "Sin coincidencias.",
            error_generic: "Hubo un problema. Intenta de nuevo.",
            copy: "Copiar",
            copied: "✓ Copiado",
            matches: "coincidencias",
            platforms: "plataformas",
            elapsed: "s buscando…",
            sound_on: "Sonido activado",
            sound_off: "Sonido silenciado",
            directory_title: "Directorio de emergencia — teléfonos y portales",
            dir_phones: "Teléfonos de emergencia",
            dir_persons: "Personas desaparecidas / encontradas",
            dir_hospital: "Hospitalizados / pacientes",
            dir_aid: "Acopio / ayuda / refugios",
            dir_pets: "Mascotas",
            dir_official: "Fuentes oficiales",
            share_title: "Comparte si conoces a alguien buscando",
            share_sub: "Un clic puede ayudar a una familia a encontrar a su ser querido.",
            share_native: "Compartir",
            share_copy: "Copiar enlace",
            share_email: "Email",
            share_copied: "✓ Copiado",
            consent_title: "Antes de usar la búsqueda",
            consent_p1: "Esta página es un buscador auspiciado que consulta plataformas ya creadas por la comunidad y organizaciones. No tenemos base de datos propia ni almacenamos información personal.",
            consent_p2: "No nos hacemos responsables por los detalles publicados en las fuentes. Verifica siempre cada dato en el sitio original antes de tomar decisiones.",
            consent_limit: "Para proteger las plataformas, el límite es de 5 búsquedas por hora por persona.",
            consent_accept: "Acepto y entiendo",
            quota_left: "búsquedas disponibles esta hora",
            quota_none: "Límite alcanzado. Podrás buscar de nuevo en",
            quota_min: "min",
            rate_limited: "Alcanzaste el límite de 5 búsquedas por hora. Es para proteger las plataformas — podrás buscar de nuevo en unos minutos. Mientras tanto, revisa el directorio de emergencia de abajo.",
            searching_steps: [
                "Conectando con las 12 plataformas…",
                "Buscando en Desaparecidos Terremoto Venezuela…",
                "Buscando en Venezuela Te Busca…",
                "Buscando en StatusVzla…",
                "Buscando en Terremoto en Venezuela…",
                "Buscando en Búsqueda Vzla y Rescate VE…",
                "Buscando en VenApp y Reporte Venezuela…",
                "Revisando pacientes hospitalizados…",
                "Consultando Venezuela Ayuda…",
                "Consultando Cruz Roja Internacional…",
                "Cruzando resultados…",
                "Casi listo…",
            ],
        },
        en: {
            title: "Venezuela Earthquake Search",
            subtitle: "Search missing persons across multiple official and community platforms.",
            disclaimer_title: "Important:",
            disclaimer_body: "This is an aggregated search over third-party platforms, with no database of our own. Always verify the status on the original source.",
            welcome: "Hi. Type the name (or part of the name) of the person you're looking for — I check 12 platforms at once. The emergency directory with phone lines and portals is below.",
            search_label: "Search person",
            search_placeholder: "E.g.: María González, last seen in Catia La Mar",
            send: "Search",
            examples_label: "Examples:",
            footer: "Federated search across official and community platforms. Every result links back to its original source.",
            powered_by: "Powered by",
            no_match: "No matches.",
            error_generic: "Something went wrong. Please try again.",
            copy: "Copy",
            copied: "✓ Copied",
            matches: "matches",
            platforms: "platforms",
            elapsed: "s searching…",
            sound_on: "Sound on",
            sound_off: "Sound muted",
            directory_title: "Emergency directory — phone lines and portals",
            dir_phones: "Emergency phone lines",
            dir_persons: "Missing / found persons",
            dir_hospital: "Hospitalized / patients",
            dir_aid: "Supplies / aid / shelters",
            dir_pets: "Pets",
            dir_official: "Official sources",
            share_title: "Share if you know someone searching",
            share_sub: "One click can help a family find their loved one.",
            share_native: "Share",
            share_copy: "Copy link",
            share_email: "Email",
            share_copied: "✓ Copied",
            consent_title: "Before you use the search",
            consent_p1: "This page is a sponsored search tool that queries platforms already built by the community and organizations. We have no database of our own and we store no personal information.",
            consent_p2: "We are not responsible for the details published on the sources. Always verify every piece of information on the original site before making decisions.",
            consent_limit: "To protect the platforms, the limit is 5 searches per hour per person.",
            consent_accept: "I accept and understand",
            quota_left: "searches left this hour",
            quota_none: "Limit reached. You can search again in",
            quota_min: "min",
            rate_limited: "You reached the limit of 5 searches per hour. This protects the platforms — you can search again in a few minutes. Meanwhile, check the emergency directory below.",
            searching_steps: [
                "Connecting to all 12 platforms…",
                "Searching Desaparecidos Terremoto Venezuela…",
                "Searching Venezuela Te Busca…",
                "Searching StatusVzla…",
                "Searching Terremoto en Venezuela…",
                "Searching Búsqueda Vzla and Rescate VE…",
                "Searching VenApp and Reporte Venezuela…",
                "Checking hospitalized patients…",
                "Checking Venezuela Ayuda…",
                "Checking International Red Cross…",
                "Merging results…",
                "Almost there…",
            ],
        },
    };

    let currentLang = (navigator.language || "es").toLowerCase().startsWith("es") ? "es" : "en";

    function t(key) { return (I18N[currentLang] && I18N[currentLang][key]) || I18N.es[key] || key; }

    function applyI18n() {
        document.documentElement.lang = currentLang;
        document.querySelectorAll("[data-i18n]").forEach((el) => {
            el.textContent = t(el.getAttribute("data-i18n"));
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
            el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
        });
        document.querySelectorAll(".lang-btn").forEach((b) => {
            b.classList.toggle("is-active", b.dataset.lang === currentLang);
        });
        document.title = currentLang === "es"
            ? "Búsqueda Terremoto Venezuela 🇻🇪"
            : "Venezuela Earthquake Search 🇻🇪";
    }

    // ---------- SONIDO (Web Audio, sin archivos) ----------
    const Sound = (() => {
        let ctx = null;
        let master = null;
        let enabled = localStorage.getItem("vz-sound") !== "off";

        function ensureCtx() {
            if (ctx) return;
            try {
                ctx = new (window.AudioContext || window.webkitAudioContext)();
                master = ctx.createGain();
                master.gain.value = 0.5;
                master.connect(ctx.destination);
            } catch (_) { /* sin audio */ }
        }

        function note(freq, when, dur, type, peak) {
            if (!ctx) return;
            const osc = ctx.createOscillator();
            const g = ctx.createGain();
            osc.type = type || "sine";
            osc.frequency.value = freq;
            g.gain.setValueAtTime(0.0001, when);
            g.gain.exponentialRampToValueAtTime(peak || 0.07, when + 0.015);
            g.gain.exponentialRampToValueAtTime(0.0001, when + dur);
            osc.connect(g).connect(master);
            osc.start(when);
            osc.stop(when + dur + 0.05);
        }

        function play(name) {
            if (!enabled) return;
            ensureCtx();
            if (!ctx) return;
            if (ctx.state === "suspended") ctx.resume();
            const now = ctx.currentTime;
            switch (name) {
                case "send": // pluck ascendente, como cuerda de cuatro
                    note(392, now, 0.12, "triangle", 0.08);
                    note(587, now + 0.06, 0.16, "triangle", 0.07);
                    break;
                case "receive": // campanita suave de dos notas
                    note(659, now, 0.25, "sine", 0.06);
                    note(880, now + 0.12, 0.4, "sine", 0.05);
                    break;
                case "found": // arpegio dorado: hay coincidencias
                    note(523, now, 0.18, "triangle", 0.06);
                    note(659, now + 0.1, 0.18, "triangle", 0.06);
                    note(784, now + 0.2, 0.3, "triangle", 0.06);
                    note(1047, now + 0.32, 0.5, "sine", 0.05);
                    break;
                case "error": // tono bajo, sobrio
                    note(196, now, 0.25, "sawtooth", 0.04);
                    note(147, now + 0.12, 0.3, "sawtooth", 0.035);
                    break;
                case "tick": // click de interfaz
                    note(1568, now, 0.04, "sine", 0.04);
                    break;
                case "toggle":
                    note(784, now, 0.08, "sine", 0.05);
                    break;
            }
        }

        function toggle() {
            enabled = !enabled;
            localStorage.setItem("vz-sound", enabled ? "on" : "off");
            if (enabled) play("toggle");
            return enabled;
        }

        return { play, toggle, get enabled() { return enabled; } };
    })();

    const soundBtn = document.getElementById("sound-toggle");
    soundBtn.setAttribute("aria-pressed", String(Sound.enabled));
    soundBtn.title = Sound.enabled ? t("sound_on") : t("sound_off");
    soundBtn.addEventListener("click", () => {
        const on = Sound.toggle();
        soundBtn.setAttribute("aria-pressed", String(on));
        soundBtn.title = on ? t("sound_on") : t("sound_off");
    });

    // ---------- CIELO ESTRELLADO (canvas) ----------
    (() => {
        const canvas = document.getElementById("sky");
        if (!canvas) return;
        const cx = canvas.getContext("2d");
        let W, H, stars = [], meteors = [];
        let mouseX = 0.5, mouseY = 0.5;

        function resize() {
            W = canvas.width = window.innerWidth * devicePixelRatio;
            H = canvas.height = window.innerHeight * devicePixelRatio;
            const count = Math.min(260, Math.floor((window.innerWidth * window.innerHeight) / 4200));
            stars = Array.from({ length: count }, () => ({
                x: Math.random(),
                y: Math.random(),
                r: (Math.random() * 1.3 + 0.3) * devicePixelRatio,
                depth: Math.random() * 0.6 + 0.4,          // parallax
                tw: Math.random() * Math.PI * 2,           // fase de titileo
                sp: Math.random() * 1.4 + 0.4,             // velocidad de titileo
                gold: Math.random() < 0.14,                // algunas doradas
            }));
        }

        function spawnMeteor() {
            meteors.push({
                x: Math.random() * 0.8 + 0.1,
                y: Math.random() * 0.25,
                vx: -(Math.random() * 5 + 4) * devicePixelRatio,
                vy: (Math.random() * 2.5 + 2) * devicePixelRatio,
                life: 1,
            });
        }

        let last = 0;
        function frame(ts) {
            const dt = Math.min((ts - last) / 1000, 0.05);
            last = ts;
            cx.clearRect(0, 0, W, H);

            for (const s of stars) {
                s.tw += dt * s.sp;
                const alpha = 0.35 + 0.65 * (0.5 + Math.sin(s.tw) / 2);
                const px = s.x * W + (mouseX - 0.5) * 30 * s.depth * devicePixelRatio;
                const py = s.y * H + (mouseY - 0.5) * 18 * s.depth * devicePixelRatio;
                cx.beginPath();
                cx.arc(px, py, s.r, 0, Math.PI * 2);
                cx.fillStyle = s.gold
                    ? `rgba(255, 214, 60, ${alpha})`
                    : `rgba(214, 228, 255, ${alpha * 0.9})`;
                cx.fill();
            }

            for (let i = meteors.length - 1; i >= 0; i--) {
                const m = meteors[i];
                m.x += (m.vx * dt) / window.innerWidth;
                m.y += (m.vy * dt) / window.innerHeight;
                m.life -= dt * 0.9;
                if (m.life <= 0) { meteors.splice(i, 1); continue; }
                const px = m.x * W, py = m.y * H;
                const grad = cx.createLinearGradient(px, py, px - m.vx * 16, py - m.vy * 16);
                grad.addColorStop(0, `rgba(255, 236, 160, ${m.life * 0.9})`);
                grad.addColorStop(1, "rgba(255, 236, 160, 0)");
                cx.strokeStyle = grad;
                cx.lineWidth = 1.6 * devicePixelRatio;
                cx.beginPath();
                cx.moveTo(px, py);
                cx.lineTo(px - m.vx * 16, py - m.vy * 16);
                cx.stroke();
            }

            if (!REDUCED_MOTION && Math.random() < dt / 7) spawnMeteor();
            if (!REDUCED_MOTION) requestAnimationFrame(frame);
        }

        window.addEventListener("resize", resize, { passive: true });
        window.addEventListener("pointermove", (e) => {
            mouseX = e.clientX / window.innerWidth;
            mouseY = e.clientY / window.innerHeight;
        }, { passive: true });

        resize();
        if (REDUCED_MOTION) {
            // Un solo cuadro estático
            requestAnimationFrame((ts) => { last = ts; frame(ts); });
        } else {
            requestAnimationFrame((ts) => { last = ts; requestAnimationFrame(frame); });
        }
    })();

    // ---------- EFECTOS: partículas, ripple, destellos ----------
    const TRICOLOR = ["#FFCE00", "#FFDE59", "#2E63D9", "#5B8DEF", "#EF3340", "#FFFFFF"];

    function burstParticles(x, y, count) {
        if (REDUCED_MOTION) return;
        for (let i = 0; i < (count || 16); i++) {
            const p = document.createElement("span");
            p.className = "particle";
            const angle = Math.random() * Math.PI * 2;
            const dist = Math.random() * 90 + 40;
            p.style.left = `${x}px`;
            p.style.top = `${y}px`;
            p.style.background = TRICOLOR[Math.floor(Math.random() * TRICOLOR.length)];
            p.style.setProperty("--px", `${Math.cos(angle) * dist}px`);
            p.style.setProperty("--py", `${Math.sin(angle) * dist - 30}px`);
            p.style.setProperty("--pr", `${Math.random() * 540 - 270}deg`);
            document.body.appendChild(p);
            setTimeout(() => p.remove(), 950);
        }
    }

    function sparkleAt(el) {
        if (REDUCED_MOTION || !el) return;
        const rect = el.getBoundingClientRect();
        for (let i = 0; i < 7; i++) {
            const s = document.createElement("span");
            s.className = "sparkle";
            s.textContent = "★";
            s.style.left = `${rect.left + Math.random() * rect.width}px`;
            s.style.top = `${rect.top + Math.random() * rect.height * 0.6 + rect.height * 0.2}px`;
            s.style.animationDelay = `${i * 90}ms`;
            document.body.appendChild(s);
            setTimeout(() => s.remove(), 1300 + i * 90);
        }
    }

    function rippleOn(btn, e) {
        if (REDUCED_MOTION) return;
        const rect = btn.getBoundingClientRect();
        const r = document.createElement("span");
        r.className = "ripple";
        const size = Math.max(rect.width, rect.height);
        r.style.width = r.style.height = `${size}px`;
        const px = (e && e.clientX ? e.clientX - rect.left : rect.width / 2) - size / 2;
        const py = (e && e.clientY ? e.clientY - rect.top : rect.height / 2) - size / 2;
        r.style.left = `${px}px`;
        r.style.top = `${py}px`;
        btn.appendChild(r);
        setTimeout(() => r.remove(), 600);
    }

    // ---------- CONSENTIMIENTO + CUOTA (5 búsquedas/hora) ----------
    const QUOTA_MAX = 5;
    const QUOTA_WINDOW_MS = 60 * 60 * 1000;
    const consentEl = document.getElementById("consent");
    const consentBtn = document.getElementById("consent-accept");
    const quotaEl = document.getElementById("quota");

    const Consent = {
        get accepted() { return localStorage.getItem("vz-consent") === "accepted"; },
        show() {
            consentEl.hidden = false;
            requestAnimationFrame(() => consentEl.classList.add("is-open"));
            consentBtn.focus();
        },
        accept() {
            localStorage.setItem("vz-consent", "accepted");
            Sound.play("found");
            consentEl.classList.remove("is-open");
            setTimeout(() => { consentEl.hidden = true; }, 450);
            document.getElementById("q").focus();
        },
    };

    consentBtn.addEventListener("click", () => Consent.accept());

    const Quota = {
        _stamps() {
            let arr;
            try { arr = JSON.parse(localStorage.getItem("vz-quota") || "[]"); } catch (_) { arr = []; }
            const now = Date.now();
            return arr.filter((ts) => now - ts < QUOTA_WINDOW_MS);
        },
        remaining() { return Math.max(0, QUOTA_MAX - this._stamps().length); },
        minutesToFree() {
            const s = this._stamps();
            if (s.length < QUOTA_MAX) return 0;
            return Math.max(1, Math.ceil((QUOTA_WINDOW_MS - (Date.now() - s[0])) / 60000));
        },
        consume() {
            const s = this._stamps();
            s.push(Date.now());
            localStorage.setItem("vz-quota", JSON.stringify(s));
        },
        render(serverRemaining) {
            const left = typeof serverRemaining === "number"
                ? Math.min(serverRemaining, this.remaining())
                : this.remaining();
            if (left > 0) {
                quotaEl.textContent = `${"★".repeat(left)}${"☆".repeat(QUOTA_MAX - left)} ${left} ${t("quota_left")}`;
                quotaEl.classList.remove("quota-empty");
            } else {
                quotaEl.textContent = `${t("quota_none")} ~${this.minutesToFree()} ${t("quota_min")}`;
                quotaEl.classList.add("quota-empty");
            }
        },
    };

    // ---------- CHAT ----------
    const log = document.getElementById("chat-log");
    const composer = document.getElementById("composer");
    const input = document.getElementById("q");
    const sendBtn = document.getElementById("send");

    function escapeHtml(s) {
        return String(s || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function linkify(s) {
        const escaped = escapeHtml(s);
        return escaped.replace(
            /(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
        ).replace(/\n/g, "<br>");
    }

    /* Igual que linkify, pero cada línea entra animada en cascada. */
    function linkifyRevealed(s) {
        const lines = String(s || "").split("\n");
        return lines.map((line, i) => {
            const html = escapeHtml(line).replace(
                /(https?:\/\/[^\s<]+)/g,
                '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
            );
            return `<span class="reveal-line" style="--l:${Math.min(i, 40)}">${html || "&nbsp;"}</span>`;
        }).join("");
    }

    function appendBubble(role, htmlContent) {
        const wrap = document.createElement("div");
        wrap.className = `msg msg-${role} ${role === "user" ? "msg-in-right" : "msg-in-left"}`;
        if (role === "bot") {
            const av = document.createElement("div");
            av.className = "msg-avatar";
            av.setAttribute("aria-hidden", "true");
            av.innerHTML = '<svg class="avatar-flag"><use href="#vz-flag"/></svg>';
            wrap.appendChild(av);
        }
        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        bubble.innerHTML = htmlContent;
        wrap.appendChild(bubble);
        log.appendChild(wrap);
        log.scrollTo({ top: log.scrollHeight, behavior: REDUCED_MOTION ? "auto" : "smooth" });
        return bubble;
    }

    function appendUser(text) {
        appendBubble("user", linkify(text));
    }

    /* Estado de espera: radar + plataforma rotando + cronómetro. */
    function appendThinking() {
        const bubble = appendBubble("bot", "");
        bubble.innerHTML = `
            <span class="searching">
                <span class="radar" aria-hidden="true"></span>
                <span class="searching-text">
                    <span class="searching-platform"></span>
                    <span class="searching-elapsed"></span>
                </span>
                <span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
            </span>`;

        const platformEl = bubble.querySelector(".searching-platform");
        const elapsedEl = bubble.querySelector(".searching-elapsed");
        const steps = t("searching_steps");
        let step = 0;
        const started = Date.now();

        platformEl.textContent = steps[0];

        const stepTimer = setInterval(() => {
            step = Math.min(step + 1, steps.length - 1);
            platformEl.textContent = steps[step];
            platformEl.style.animation = "none";
            void platformEl.offsetWidth; // reinicia la animación
            platformEl.style.animation = "";
            Sound.play("tick");
        }, 2600);

        const clockTimer = setInterval(() => {
            elapsedEl.textContent = `${Math.floor((Date.now() - started) / 1000)}${t("elapsed")}`;
        }, 1000);

        bubble.dataset.cleanup = "pending";
        bubble._stopTimers = () => {
            clearInterval(stepTimer);
            clearInterval(clockTimer);
        };
        return bubble;
    }

    async function ask(query) {
        appendUser(query);
        Sound.play("send");
        const thinking = appendThinking();
        sendBtn.disabled = true;
        Quota.consume();
        Quota.render();

        try {
            const res = await fetch("/api/search", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "vzla-search",
                },
                body: JSON.stringify({ query, language: currentLang }),
            });
            if (res.status === 429) {
                let detail = null;
                try { detail = (await res.json()).detail; } catch (_) { /* texto plano */ }
                const msg = detail && detail[`message_${currentLang}`]
                    ? detail[`message_${currentLang}`]
                    : t("rate_limited");
                thinking._stopTimers();
                thinking.classList.add("is-error");
                thinking.textContent = msg;
                Sound.play("error");
                return;
            }
            if (!res.ok) {
                const errText = await res.text().catch(() => "");
                throw new Error(`HTTP ${res.status}: ${errText || res.statusText}`);
            }
            const data = await res.json();
            Quota.render(data.searches_remaining);

            thinking._stopTimers();
            const text = currentLang === "es" ? data.formatted_es : data.formatted_en;
            thinking.innerHTML = linkifyRevealed(text);

            const hasMatches = (data.total_matches || 0) > 0;
            if (hasMatches) {
                thinking.classList.add("has-matches");
                Sound.play("found");
                sparkleAt(thinking);
            } else {
                Sound.play("receive");
            }

            // Chips de metadatos
            const metaEl = document.createElement("div");
            metaEl.className = "msg-meta";
            metaEl.innerHTML = [
                `<span class="${hasMatches ? "meta-hit" : ""}">${data.total_matches} ${t("matches")}</span>`,
                `<span>${data.platforms_queried} ${t("platforms")}</span>`,
                `<span>${escapeHtml(String(data.language || "").toUpperCase())}</span>`,
            ].join("");
            thinking.parentElement.appendChild(metaEl);

            // Botón copiar
            const copyBtn = document.createElement("button");
            copyBtn.type = "button";
            copyBtn.className = "copy-btn";
            copyBtn.textContent = t("copy");
            copyBtn.addEventListener("click", async (e) => {
                rippleOn(copyBtn, e);
                try {
                    await navigator.clipboard.writeText(text);
                    Sound.play("tick");
                    copyBtn.textContent = t("copied");
                    copyBtn.classList.add("copied");
                    setTimeout(() => {
                        copyBtn.textContent = t("copy");
                        copyBtn.classList.remove("copied");
                    }, 1800);
                } catch (_) { /* ignore */ }
            });
            thinking.parentElement.appendChild(copyBtn);
            log.scrollTo({ top: log.scrollHeight, behavior: REDUCED_MOTION ? "auto" : "smooth" });
        } catch (err) {
            thinking._stopTimers();
            thinking.classList.add("is-error");
            thinking.innerHTML = `${escapeHtml(t("error_generic"))}<br><small>${escapeHtml(String(err.message || err))}</small>`;
            Sound.play("error");
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    }

    // ---------- EVENTOS ----------
    composer.addEventListener("submit", (e) => {
        e.preventDefault();
        if (!Consent.accepted) { Consent.show(); return; }
        if (Quota.remaining() <= 0) {
            Quota.render();
            appendBubble("bot", escapeHtml(t("rate_limited"))).classList.add("is-error");
            Sound.play("error");
            return;
        }
        const q = input.value.trim();
        if (q.length < 2) return;
        input.value = "";

        const rect = sendBtn.getBoundingClientRect();
        burstParticles(rect.left + rect.width / 2, rect.top + rect.height / 2, 18);
        rippleOn(sendBtn, null);

        ask(q);
    });

    document.querySelectorAll(".lang-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            currentLang = btn.dataset.lang;
            Sound.play("tick");
            rippleOn(btn, e);
            applyI18n();
            Quota.render();
        });
    });

    document.querySelectorAll(".example").forEach((b) => {
        b.addEventListener("click", (e) => {
            Sound.play("tick");
            rippleOn(b, e);
            input.value = b.dataset.q;
            input.focus();
        });
    });

    // ---------- COMPARTIR ----------
    const SHARE_TEXT = {
        es: "🇻🇪 Busca personas desaparecidas del terremoto de Venezuela en 13 plataformas a la vez — sin instalación:",
        en: "🇻🇪 Search for missing persons from the Venezuela earthquake across 13 platforms at once — no install:",
    };

    function shareUrl() {
        return window.location.href;
    }

    function shareText() {
        return SHARE_TEXT[currentLang] || SHARE_TEXT.es;
    }

    const SHARE_HANDLERS = {
        native: async () => {
            if (!navigator.share) return;
            try {
                await navigator.share({
                    title: t("title"),
                    text: shareText(),
                    url: shareUrl(),
                });
                Sound.play("tick");
            } catch (_) { /* user cancelled */ }
        },
        whatsapp: () => openWindow(`https://wa.me/?text=${encodeURIComponent(shareText() + " " + shareUrl())}`),
        telegram: () => openWindow(`https://t.me/share/url?url=${encodeURIComponent(shareUrl())}&text=${encodeURIComponent(shareText())}`),
        twitter: () => openWindow(`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText())}&url=${encodeURIComponent(shareUrl())}`),
        facebook: () => openWindow(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl())}`),
        linkedin: () => openWindow(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl())}`),
        email: () => {
            const subject = encodeURIComponent(currentLang === "en" ? "Venezuela Earthquake Search" : "Búsqueda Terremoto Venezuela");
            const body = encodeURIComponent(shareText() + "\n\n" + shareUrl());
            openWindow(`mailto:?subject=${subject}&body=${body}`);
        },
        copy: async (btn) => {
            try {
                await navigator.clipboard.writeText(shareUrl());
                const labelEl = btn.querySelector("[data-i18n]") || btn;
                const orig = labelEl.textContent;
                btn.classList.add("copied");
                labelEl.textContent = t("share_copied");
                Sound.play("tick");
                setTimeout(() => {
                    btn.classList.remove("copied");
                    labelEl.textContent = t("share_copy");
                }, 1800);
            } catch (_) { /* clipboard blocked */ }
        },
    };

    function openWindow(url) {
        try {
            window.open(url, "_blank", "noopener,noreferrer");
            Sound.play("tick");
        } catch (_) { /* popup blocked */ }
    }

    // Show native share button only where supported (mobile).
    if (navigator.share) {
        const nativeBtn = document.querySelector('[data-share="native"]');
        if (nativeBtn) nativeBtn.hidden = false;
    }

    document.querySelectorAll("[data-share]").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            rippleOn(btn, e);
            const kind = btn.dataset.share;
            const handler = SHARE_HANDLERS[kind];
            if (!handler) return;
            if (kind === "copy") return handler(btn);
            handler();
        });
    });

    applyI18n();
    Quota.render();
    if (!Consent.accepted) {
        Consent.show();
    } else {
        input.focus();
    }
})();
