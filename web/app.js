const languageInputs = document.querySelectorAll('input[name="language"]');
const languageSwitch = document.querySelector(".language-switch");
const switchThumb = document.querySelector(".switch-thumb");
const saverFolder = document.getElementById("saver-folder");
const saverFolderTrigger = document.getElementById("saver-folder-trigger");
const saverFolderLabel = document.getElementById("saver-folder-label");
const saverFolderMenu = document.getElementById("saver-folder-menu");
const cardInput = document.getElementById("card-input");
const prepareButton = document.getElementById("prepare-button");
const status = document.getElementById("status");

const EMPTY_INPUT_CARDS_MESSAGE =
  "input-cards.txt is empty. Add card rows to this file before preparing.";

function selectedLanguage() {
  return document.querySelector('input[name="language"]:checked').value;
}

function setStatus(message, type = "") {
  status.textContent = message;
  status.className = "status visible";
  if (type) {
    status.classList.add(type);
  }
}

function clearStatusSoon(delay = 8000) {
  window.setTimeout(() => {
    status.className = "status";
    status.textContent = "";
  }, delay);
}

function updateSwitchThumb() {
  if (!languageSwitch || !switchThumb) {
    return;
  }

  const checked = languageSwitch.querySelector('input[name="language"]:checked');
  if (!checked) {
    return;
  }

  const option = checked.closest(".switch-option");
  const switchRect = languageSwitch.getBoundingClientRect();
  const optionRect = option.getBoundingClientRect();

  switchThumb.style.width = `${optionRect.width}px`;
  switchThumb.style.transform = `translateX(${optionRect.left - switchRect.left}px)`;
  languageSwitch.classList.add("is-ready");
}

function updateFolderSelectionUi() {
  saverFolderLabel.textContent = saverFolder.value;

  for (const item of saverFolderMenu.querySelectorAll(".folder-dropdown-item")) {
    item.classList.toggle("is-selected", item.dataset.value === saverFolder.value);
    item.setAttribute("aria-selected", item.dataset.value === saverFolder.value);
  }
}

async function loadInputCards() {
  const folder = saverFolder.value;
  if (!folder) {
    cardInput.value = "";
    return;
  }

  try {
    const response = await fetch(
      `/api/input-cards?folder=${encodeURIComponent(folder)}`,
    );
    const data = await response.json();

    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Could not load input-cards.txt.");
    }

    cardInput.value = data.empty ? EMPTY_INPUT_CARDS_MESSAGE : data.content;
  } catch (error) {
    cardInput.value = error.message;
  }
}

function setSaverFolderValue(value) {
  saverFolder.value = value;
  updateFolderSelectionUi();

  if (selectedLanguage() === "korean") {
    loadInputCards();
  }
}

function closeSaverFolderMenu() {
  saverFolderMenu.hidden = true;
  saverFolderTrigger.setAttribute("aria-expanded", "false");
}

function openSaverFolderMenu() {
  if (saverFolderTrigger.disabled) {
    return;
  }
  saverFolderMenu.hidden = false;
  saverFolderTrigger.setAttribute("aria-expanded", "true");
}

function toggleSaverFolderMenu() {
  if (saverFolderMenu.hidden) {
    openSaverFolderMenu();
  } else {
    closeSaverFolderMenu();
  }
}

async function updateLanguageUi() {
  const isKorean = selectedLanguage() === "korean";
  saverFolderTrigger.disabled = !isKorean;

  if (!isKorean) {
    closeSaverFolderMenu();
    cardInput.value = "";
  } else if (saverFolder.value) {
    await loadInputCards();
  }

  updateSwitchThumb();
}

async function loadSaverFolders() {
  const response = await fetch("/api/saver-folders");
  const data = await response.json();

  saverFolderMenu.replaceChildren();
  for (const folder of data.folders) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "folder-dropdown-item";
    item.role = "option";
    item.dataset.value = folder;
    item.textContent = folder;
    item.addEventListener("click", () => {
      setSaverFolderValue(folder);
      closeSaverFolderMenu();
    });
    saverFolderMenu.appendChild(item);
  }

  if (data.default) {
    setSaverFolderValue(data.default);
  } else {
    updateFolderSelectionUi();
  }
}

saverFolderTrigger.addEventListener("click", (event) => {
  event.stopPropagation();
  toggleSaverFolderMenu();
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".folder-dropdown")) {
    closeSaverFolderMenu();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeSaverFolderMenu();
  }
});

languageInputs.forEach((input) => {
  input.addEventListener("change", updateLanguageUi);
});

prepareButton.addEventListener("click", async () => {
  const text = cardInput.value.trim();
  const language = selectedLanguage();

  if (!text || text === EMPTY_INPUT_CARDS_MESSAGE) {
    setStatus("Paste card data before preparing.", "error");
    clearStatusSoon(4200);
    return;
  }

  if (language === "korean" && !saverFolder.value) {
    setStatus("Choose a KoreanSaver folder.", "error");
    clearStatusSoon(4200);
    return;
  }

  prepareButton.disabled = true;
  setStatus("Preparing cards — generating audio and copying images…");

  try {
    const response = await fetch("/api/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        language,
        saver_folder: language === "korean" ? saverFolder.value : null,
      }),
    });
    const result = await response.json();

    if (!response.ok || !result.ok) {
      throw new Error(result.error || "Preparation failed.");
    }

    setStatus(
      [
        `Saved to ${result.output_file}`,
        `${result.card_count} cards.`,
        `Audio: ${result.audio_generated} new, ${result.audio_reused} reused.`,
        `Images: ${result.images_copied} copied, ${result.images_reused} reused, ${result.images_missing} missing.`,
      ].join(" "),
      "success",
    );
    clearStatusSoon();
  } catch (error) {
    setStatus(error.message, "error");
    clearStatusSoon(6000);
  } finally {
    prepareButton.disabled = false;
  }
});

loadSaverFolders().catch(() => {
  setStatus("Could not load KoreanSaver folders.", "error");
  clearStatusSoon(6000);
});

updateLanguageUi();

window.addEventListener("resize", updateSwitchThumb);