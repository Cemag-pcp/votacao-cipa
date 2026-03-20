(function () {
  const form = document.getElementById("contactCreateForm");
  if (!form) return;

  const modalEl = document.getElementById("contactCreateModal");
  const alertBox = document.getElementById("contactCreateAlert");
  const submitBtn = document.getElementById("contactCreateSubmit");
  const spinner = document.getElementById("contactCreateSpinner");

  const companyInput = document.getElementById("contactCompanyName");
  const companyIdInput = document.getElementById("contactCompanyId");
  const companySuggestions = document.getElementById("contactCompanySuggestions");
  const companyFeedback = document.getElementById("contactCompanyFeedback");

  const cityInput = document.getElementById("contactCityName");
  const cityIdInput = document.getElementById("contactCityId");
  const citySuggestions = document.getElementById("contactCitySuggestions");
  const cityFeedback = document.getElementById("contactCityFeedback");

  const nameInput = document.getElementById("contactName");
  const phoneInput = document.getElementById("contactPhone");
  const phoneTypeSelect = document.getElementById("contactPhoneType");
  const ownerIdInput = document.getElementById("contactOwnerId");

  let companyTimeout = null;
  let cityTimeout = null;

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

  function hasRequiredFields() {
    return Boolean(
      (companyIdInput?.value || "").trim() &&
      (nameInput?.value || "").trim() &&
      (phoneInput?.value || "").trim() &&
      (cityIdInput?.value || "").trim()
    );
  }

  function setLoading(isLoading) {
    if (submitBtn) submitBtn.disabled = isLoading || !hasRequiredFields();
    if (spinner) spinner.classList.toggle("d-none", !isLoading);
  }

  function updateSubmitState() {
    if (submitBtn && (!spinner || spinner.classList.contains("d-none"))) {
      submitBtn.disabled = !hasRequiredFields();
    }
  }

  function showLoading(dropdownEl, label) {
    if (!dropdownEl) return;
    dropdownEl.innerHTML = `
      <div class="list-group-item d-flex align-items-center gap-2 text-secondary">
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        <span>${label}</span>
      </div>
    `;
    dropdownEl.classList.remove("d-none");
  }

  function hideDropdown(dropdownEl) {
    if (!dropdownEl) return;
    dropdownEl.classList.add("d-none");
    dropdownEl.innerHTML = "";
  }

  function renderCompanySuggestions(items) {
    if (!companySuggestions) return;
    companySuggestions.innerHTML = "";
    if (!items.length) {
      companySuggestions.innerHTML = `<div class="list-group-item text-secondary">Nenhuma empresa encontrada</div>`;
      companySuggestions.classList.remove("d-none");
      return;
    }

    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "list-group-item list-group-item-action";
      btn.textContent = item.nome || "";
      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        companyInput.value = item.nome || "";
        companyIdInput.value = item.id || "";
        companyFeedback.textContent = "Empresa selecionada.";
        companyFeedback.classList.remove("text-warning");
        companyFeedback.classList.add("text-success");
        hideDropdown(companySuggestions);
        updateSubmitState();
      });
      companySuggestions.appendChild(btn);
    });
    companySuggestions.classList.remove("d-none");
  }

  function renderCitySuggestions(items) {
    if (!citySuggestions) return;
    citySuggestions.innerHTML = "";
    if (!items.length) {
      citySuggestions.innerHTML = `<div class="list-group-item text-secondary">Nenhuma cidade encontrada</div>`;
      citySuggestions.classList.remove("d-none");
      return;
    }

    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "list-group-item list-group-item-action";
      btn.textContent = item.estado ? `${item.cidade} - ${item.estado}` : (item.cidade || "");
      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        cityInput.value = item.cidade || "";
        cityIdInput.value = item.id || "";
        cityFeedback.textContent = item.estado ? `Cidade selecionada: ${item.cidade} - ${item.estado}` : "Cidade selecionada.";
        cityFeedback.classList.remove("text-warning");
        cityFeedback.classList.add("text-success");
        hideDropdown(citySuggestions);
        updateSubmitState();
      });
      citySuggestions.appendChild(btn);
    });
    citySuggestions.classList.remove("d-none");
  }

  async function searchCompanies(term) {
    showLoading(companySuggestions, "Carregando empresas...");
    try {
      const ownerId = Number(ownerIdInput?.value || 0) || "";
      const url = `/api/ploomes/companies/search/?term=${encodeURIComponent(term || "")}&owner_id=${ownerId}&top=100`;
      const response = await fetch(url);
      const data = await response.json();
      if (!response.ok) {
        hideDropdown(companySuggestions);
        return;
      }
      renderCompanySuggestions(data.results || []);
    } catch (_) {
      hideDropdown(companySuggestions);
    }
  }

  async function searchCities(term) {
    showLoading(citySuggestions, "Carregando cidades...");
    try {
      const url = `/api/ploomes/cities/search/?term=${encodeURIComponent(term || "")}&top=30`;
      const response = await fetch(url);
      const data = await response.json();
      if (!response.ok) {
        hideDropdown(citySuggestions);
        return;
      }
      renderCitySuggestions(data.results || []);
    } catch (_) {
      hideDropdown(citySuggestions);
    }
  }

  companyInput?.addEventListener("focus", () => searchCompanies(companyInput.value || ""));
  companyInput?.addEventListener("input", () => {
    companyIdInput.value = "";
    companyFeedback.textContent = "Selecione uma empresa da lista.";
    companyFeedback.classList.remove("text-success");
    companyFeedback.classList.add("text-warning");
    updateSubmitState();
    if (companyTimeout) clearTimeout(companyTimeout);
    companyTimeout = setTimeout(() => searchCompanies(companyInput.value || ""), 250);
  });

  cityInput?.addEventListener("focus", () => searchCities(cityInput.value || ""));
  cityInput?.addEventListener("input", () => {
    cityIdInput.value = "";
    cityFeedback.textContent = "Selecione uma cidade da lista.";
    cityFeedback.classList.remove("text-success");
    cityFeedback.classList.add("text-warning");
    updateSubmitState();
    if (cityTimeout) clearTimeout(cityTimeout);
    cityTimeout = setTimeout(() => searchCities(cityInput.value || ""), 250);
  });

  [nameInput, phoneInput, phoneTypeSelect].forEach((el) => {
    el?.addEventListener("input", updateSubmitState);
    el?.addEventListener("change", updateSubmitState);
  });

  companyInput?.addEventListener("blur", () => setTimeout(() => hideDropdown(companySuggestions), 150));
  cityInput?.addEventListener("blur", () => setTimeout(() => hideDropdown(citySuggestions), 150));

  document.addEventListener("click", (event) => {
    if (companySuggestions && !companySuggestions.contains(event.target) && !companyInput?.contains(event.target)) {
      hideDropdown(companySuggestions);
    }
    if (citySuggestions && !citySuggestions.contains(event.target) && !cityInput?.contains(event.target)) {
      hideDropdown(citySuggestions);
    }
  });

  modalEl?.addEventListener("hidden.bs.modal", () => {
    clearAlert();
    form.reset();
    companyIdInput.value = "";
    cityIdInput.value = "";
    companyFeedback.textContent = "";
    cityFeedback.textContent = "";
    companyFeedback.classList.remove("text-success", "text-warning");
    cityFeedback.classList.remove("text-success", "text-warning");
    hideDropdown(companySuggestions);
    hideDropdown(citySuggestions);
    updateSubmitState();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAlert();
    setLoading(true);
    try {
      const phoneTypeId = Number(phoneTypeSelect?.value || 1);
      const phoneTypeName = (phoneTypeSelect?.selectedOptions?.[0]?.textContent || "Comercial").trim();

      const payload = {
        company_id: Number(companyIdInput?.value || 0) || null,
        nome: (nameInput?.value || "").trim(),
        telefone: (phoneInput?.value || "").trim(),
        tipoTelefone: phoneTypeName,
        codigoTipoTelefone: phoneTypeId,
        cidade_id: Number(cityIdInput?.value || 0) || null,
        cidade: (cityInput?.value || "").trim(),
        owner_id: Number(ownerIdInput?.value || 0) || null,
      };

      if (!payload.company_id || !payload.nome || !payload.telefone || !payload.cidade_id) {
        setAlert("Preencha os campos obrigatórios e selecione empresa/cidade da lista.", "warning");
        return;
      }

      const response = await fetch("/api/ploomes/contacts/create/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        setAlert(data.detail || "Falha ao criar contato.", "danger");
        return;
      }

      setAlert(data.detail || "Contato criado com sucesso.", "success");
      setTimeout(() => {
        try {
          const instance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
          instance.hide();
        } catch (_) {
          // noop
        }
      }, 900);
    } catch (err) {
      setAlert(`Erro ao salvar: ${err.message}`, "danger");
    } finally {
      setLoading(false);
    }
  });

  updateSubmitState();
})();
