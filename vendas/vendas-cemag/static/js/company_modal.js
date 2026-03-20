(function () {
  const form = document.getElementById("companyCreateForm");
  if (!form) return;

  const modalEl = document.getElementById("companyCreateModal");
  const cidadeInput = document.getElementById("companyCidade");
  const cidadeSuggestions = document.getElementById("companyCidadeSuggestions");
  const cidadeFeedback = document.getElementById("companyCidadeFeedback");
  const cnpjInput = document.getElementById("companyCnpj");
  const cnpjFeedback = document.getElementById("companyCnpjFeedback");
  const ownerIdInput = document.getElementById("companyOwnerId");
  const submitBtn = document.getElementById("companyCreateSubmit");
  const spinner = document.getElementById("companyCreateSpinner");
  const alertBox = document.getElementById("companyCreateAlert");

  let lastCityValidation = null;
  let citySearchTimeout = null;

  function setAlert(message, type) {
    if (!alertBox) return;
    alertBox.className = `alert alert-${type}`;
    alertBox.textContent = message;
    alertBox.classList.remove("d-none");
  }

  function clearAlert() {
    if (!alertBox) return;
    alertBox.classList.add("d-none");
    alertBox.textContent = "";
  }

  function hasRequiredFieldsFilled() {
    const nome = document.getElementById("companyNome")?.value?.trim() || "";
    const telefone = document.getElementById("companyTelefone")?.value?.trim() || "";
    const cidade = cidadeInput?.value?.trim() || "";
    const cnpj = cnpjInput?.value || "";
    return Boolean(nome && telefone && cidade && isCnpjValid(cnpj));
  }

  function updateSubmitState(isLoading = false) {
    if (submitBtn) submitBtn.disabled = isLoading || !hasRequiredFieldsFilled();
  }

  function setLoading(loading) {
    updateSubmitState(loading);
    if (spinner) spinner.classList.toggle("d-none", !loading);
  }

  function formatCnpj(value) {
    const digits = (value || "").replace(/\D/g, "").slice(0, 14);
    return digits
      .replace(/^(\d{2})(\d)/, "$1.$2")
      .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/\.(\d{3})(\d)/, ".$1/$2")
      .replace(/(\d{4})(\d)/, "$1-$2");
  }

  function isCnpjValid(value) {
    const cnpj = (value || "").replace(/\D/g, "");
    if (cnpj.length !== 14) return false;
    if (/^(\d)\1{13}$/.test(cnpj)) return false;

    const calcDigit = (base, factors) => {
      const total = base
        .split("")
        .reduce((acc, n, i) => acc + Number(n) * factors[i], 0);
      const mod = total % 11;
      return mod < 2 ? 0 : 11 - mod;
    };

    const d1 = calcDigit(cnpj.slice(0, 12), [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
    const d2 = calcDigit(cnpj.slice(0, 12) + d1, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
    return cnpj.endsWith(`${d1}${d2}`);
  }

  function validateCnpjField() {
    if (!cnpjInput) return true;
    const raw = cnpjInput.value || "";
    const hasAnyValue = (raw || "").replace(/\D/g, "").length > 0;
    const valid = isCnpjValid(raw);

    if (!hasAnyValue) {
      if (cnpjFeedback) {
        cnpjFeedback.textContent = "";
        cnpjFeedback.classList.remove("text-warning", "text-success");
        cnpjFeedback.classList.add("text-secondary");
      }
      updateSubmitState(false);
      return false;
    }

    if (!valid) {
      if (cnpjFeedback) {
        cnpjFeedback.textContent = "Digite um cnpj válido.";
        cnpjFeedback.classList.remove("text-secondary", "text-success");
        cnpjFeedback.classList.add("text-warning");
      }
      updateSubmitState(false);
      return false;
    }

    if (cnpjFeedback) {
      cnpjFeedback.textContent = "CNPJ válido.";
      cnpjFeedback.classList.remove("text-secondary", "text-warning");
      cnpjFeedback.classList.add("text-success");
    }
    updateSubmitState(false);
    return true;
  }

  function hideCitySuggestions() {
    if (!cidadeSuggestions) return;
    cidadeSuggestions.classList.add("d-none");
    cidadeSuggestions.innerHTML = "";
  }

  function showCitySuggestionsLoading() {
    if (!cidadeSuggestions) return;
    cidadeSuggestions.innerHTML = `
      <div class="list-group-item d-flex align-items-center gap-2 text-secondary">
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        <span>Carregando cidades...</span>
      </div>
    `;
    cidadeSuggestions.classList.remove("d-none");
  }

  function renderCitySuggestions(items) {
    if (!cidadeSuggestions) return;
    cidadeSuggestions.innerHTML = "";
    if (!items || !items.length) {
      hideCitySuggestions();
      return;
    }

    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "list-group-item list-group-item-action";
      btn.textContent = item.estado ? `${item.cidade} - ${item.estado}` : item.cidade;
      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        cidadeInput.value = item.cidade || "";
        lastCityValidation = {
          cidade: item.cidade || "",
          estado: item.estado || "",
          cidade_id: item.id || null,
          valid: Boolean(item.id),
        };
        cidadeFeedback.textContent = item.estado ? `Cidade selecionada: ${item.cidade} - ${item.estado}` : `Cidade selecionada: ${item.cidade}`;
        cidadeFeedback.classList.remove("text-warning");
        cidadeFeedback.classList.add("text-success");
        hideCitySuggestions();
        updateSubmitState(false);
      });
      cidadeSuggestions.appendChild(btn);
    });
    cidadeSuggestions.classList.remove("d-none");
  }

  async function searchCities(term = "") {
    try {
      showCitySuggestionsLoading();
      const url = `/api/ploomes/cities/search/?term=${encodeURIComponent(term)}&top=20`;
      const response = await fetch(url);
      const data = await response.json();
      if (!response.ok) {
        hideCitySuggestions();
        return;
      }
      renderCitySuggestions(data.results || []);
    } catch (err) {
      hideCitySuggestions();
    }
  }

  async function validateCity(cidade) {
    const city = (cidade || "").trim();
    if (!city) {
      cidadeFeedback.textContent = "";
      lastCityValidation = null;
      return null;
    }

    try {
      const url = `/api/ploomes/cities/validate/?cidade=${encodeURIComponent(city)}`;
      const response = await fetch(url);
      const data = await response.json();

      if (!response.ok) {
        cidadeFeedback.textContent = "Cidade não encontrada.";
        cidadeFeedback.classList.remove("text-success");
        cidadeFeedback.classList.add("text-warning");
        lastCityValidation = null;
        return null;
      }

      cidadeFeedback.textContent = `Cidade válida: ${data.cidade} - ${data.estado}`;
      cidadeFeedback.classList.remove("text-warning");
      cidadeFeedback.classList.add("text-success");
      lastCityValidation = data;
      return data;
    } catch (err) {
      cidadeFeedback.textContent = "Falha ao validar cidade.";
      cidadeFeedback.classList.remove("text-success");
      cidadeFeedback.classList.add("text-warning");
      lastCityValidation = null;
      return null;
    }
  }

  cidadeInput?.addEventListener("focus", () => {
    searchCities(cidadeInput.value || "");
  });

  cnpjInput?.addEventListener("input", () => {
    cnpjInput.value = formatCnpj(cnpjInput.value);
    validateCnpjField();
    updateSubmitState(false);
  });

  cnpjInput?.addEventListener("blur", () => {
    validateCnpjField();
  });

  cidadeInput?.addEventListener("input", () => {
    lastCityValidation = null;
    updateSubmitState(false);
    if (citySearchTimeout) clearTimeout(citySearchTimeout);
    citySearchTimeout = setTimeout(() => {
      searchCities(cidadeInput.value || "");
    }, 200);
  });

  cidadeInput?.addEventListener("blur", () => {
    window.setTimeout(() => {
      hideCitySuggestions();
      validateCity(cidadeInput.value).finally(() => updateSubmitState(false));
    }, 120);
  });

  ["companyNome", "companyTelefone", "companyCidade"].forEach((id) => {
    const el = document.getElementById(id);
    el?.addEventListener("input", () => updateSubmitState(false));
  });

  modalEl?.addEventListener("hidden.bs.modal", () => {
    hideCitySuggestions();
    lastCityValidation = null;
    cidadeFeedback.textContent = "";
    if (cnpjFeedback) {
      cnpjFeedback.textContent = "";
      cnpjFeedback.classList.remove("text-warning", "text-success");
      cnpjFeedback.classList.add("text-secondary");
    }
    clearAlert();
    form.reset();
    updateSubmitState(false);
  });

  document.addEventListener("click", (event) => {
    if (!cidadeSuggestions || !cidadeInput) return;
    if (cidadeSuggestions.contains(event.target) || cidadeInput.contains(event.target)) return;
    hideCitySuggestions();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAlert();
    setLoading(true);

    try {
      const payload = {
        nome: document.getElementById("companyNome")?.value?.trim(),
        cnpj: document.getElementById("companyCnpj")?.value?.trim(),
        telefone: document.getElementById("companyTelefone")?.value?.trim(),
        tipoTelefone: document.getElementById("companyTipoTelefone")?.value,
        cidade: cidadeInput?.value?.trim(),
        responsavel: document.getElementById("companyResponsavel")?.value?.trim(),
        condicao: document.getElementById("companyCondicao")?.value,
        tipo_id: Number(document.getElementById("companyTipoId")?.value || 1),
        owner_id: Number(ownerIdInput?.value || 0) || null,
      };

      if (!payload.nome || !payload.cnpj || !payload.telefone || !payload.cidade) {
        setAlert("Preencha os campos obrigatórios.", "warning");
        return;
      }

      if (!validateCnpjField()) {
        return;
      }

      if (!lastCityValidation || (lastCityValidation.cidade || "").toLowerCase() !== payload.cidade.toLowerCase()) {
        const validated = await validateCity(payload.cidade);
        if (!validated) {
          setAlert("Cidade inválida. Ajuste o nome antes de salvar.", "warning");
          return;
        }
      }

      const response = await fetch("/api/ploomes/companies/create/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (!response.ok) {
        setAlert(data.detail || "Falha ao criar empresa.", "danger");
        return;
      }

      setAlert(data.detail || "Empresa criada com sucesso.", "success");
      form.reset();
      cidadeFeedback.textContent = "";
      lastCityValidation = null;

      window.setTimeout(() => {
        try {
          const instance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
          instance.hide();
        } catch (e) {
          // noop
        }
      }, 1000);
    } catch (err) {
      setAlert(`Erro ao salvar: ${err.message}`, "danger");
    } finally {
      setLoading(false);
    }
  });

  validateCnpjField();
  updateSubmitState(false);
})();
