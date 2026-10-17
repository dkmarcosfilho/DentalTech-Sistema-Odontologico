(function() {
    "use strict";

    // Menu lateral (mobile)
    var toggle = document.querySelector("[data-nav-toggle]");
    var backdrop = document.querySelector(".sidebar-backdrop");

    function setNav(open) {
        document.body.classList.toggle("nav-open", open);
        if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }
    if (toggle) toggle.addEventListener("click", function() {
        setNav(!document.body.classList.contains("nav-open"));
    });
    if (backdrop) backdrop.addEventListener("click", function() { setNav(false); });
    document.addEventListener("keydown", function(e) { if (e.key === "Escape") setNav(false); });

    // Fechar alertas (e sumir sozinho os de sucesso)
    document.querySelectorAll(".alert").forEach(function(el) {
        var btn = el.querySelector(".alert-close");

        function close() {
            el.style.transition = "opacity .25s, transform .25s";
            el.style.opacity = "0";
            el.style.transform = "translateY(-6px)";
            setTimeout(function() { el.remove(); }, 260);
        }
        if (btn) btn.addEventListener("click", close);
        if (el.classList.contains("success")) setTimeout(close, 5000);
    });

    // Mostrar/ocultar senha
    document.querySelectorAll('.auth-card input[type="password"]').forEach(function(input) {
        var wrap = document.createElement("span");
        wrap.className = "pw-field";
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "pw-toggle";
        btn.textContent = "Mostrar";
        btn.setAttribute("aria-label", "Mostrar ou ocultar senha");
        btn.addEventListener("click", function() {
            var show = input.type === "password";
            input.type = show ? "text" : "password";
            btn.textContent = show ? "Ocultar" : "Mostrar";
        });
        wrap.appendChild(btn);
    });

    // Confirmação antes de ações destrutivas: <form data-confirm="Mensagem?">
    // (captura: roda antes do bloqueio de duplo envio abaixo)
    document.addEventListener("submit", function(e) {
        var msg = e.target.getAttribute && e.target.getAttribute("data-confirm");
        if (msg && !window.confirm(msg)) {
            e.preventDefault();
            e.stopImmediatePropagation();
        }
    }, true);

    // Imprimir relatório
    document.querySelectorAll("[data-print]").forEach(function(el) {
        el.addEventListener("click", function(e) {
            e.preventDefault();
            window.print();
        });
    });

    // Máscaras de CPF e telefone
    function digitos(v) { return (v || "").replace(/\D/g, ""); }
    var mascaras = {
        cpf: function(v) {
            v = digitos(v).slice(0, 11);
            return v.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2");
        },
        telefone: function(v) {
            v = digitos(v).slice(0, 11);
            if (v.length > 10) return v.replace(/(\d{2})(\d{5})(\d{0,4})/, "($1) $2-$3");
            if (v.length > 6) return v.replace(/(\d{2})(\d{4})(\d{0,4})/, "($1) $2-$3");
            if (v.length > 2) return v.replace(/(\d{2})(\d*)/, "($1) $2");
            return v;
        }
    };
    document.querySelectorAll("input[data-mask]").forEach(function(input) {
        var fn = mascaras[input.getAttribute("data-mask")];
        if (!fn) return;
        input.value = fn(input.value);
        input.addEventListener("input", function() { input.value = fn(input.value); });
    });

    // Anamnese: "limpar" desmarca as bolinhas de uma pergunta
    document.querySelectorAll("[data-limpar]").forEach(function(btn) {
        btn.addEventListener("click", function() {
            document.querySelectorAll("input[name='" + btn.dataset.limpar + "']").forEach(function(r) {
                r.checked = false;
            });
        });
    });


    // Evita duplo envio de formulários
    document.querySelectorAll("form[method='post']").forEach(function(form) {
        form.addEventListener("submit", function() {
            var b = form.querySelector("button[type='submit'], button:not([type])");
            if (b) setTimeout(function() {
                b.disabled = true;
                b.style.opacity = ".7";
            }, 0);
        });
    });
})();