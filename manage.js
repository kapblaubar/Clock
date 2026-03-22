const gallery = document.getElementById("gallery");
const photoInput = document.getElementById("photoInput");
const uploadButton = document.getElementById("uploadButton");
const showAnalog = document.getElementById("showAnalog");
const mode24 = document.getElementById("mode24");
const saveSettings = document.getElementById("saveSettings");
const statusText = document.getElementById("statusText");
const displayMode = document.getElementById("displayMode");
const rotationMode = document.getElementById("rotationMode");
const graphicPanel = document.getElementById("graphicPanel");
const worldPanel = document.getElementById("worldPanel");
const airportPanel = document.getElementById("airportPanel");
const lichtzeitpegelPanel = document.getElementById("lichtzeitpegelPanel");
const homeLocationSelect = document.getElementById("homeLocationSelect");
const applyHomeLocation = document.getElementById("applyHomeLocation");
const clearHomeLocation = document.getElementById("clearHomeLocation");
const homeLocationStatus = document.getElementById("homeLocationStatus");
const customLabel = document.getElementById("customLabel");
const customCity = document.getElementById("customCity");
const customCountry = document.getElementById("customCountry");
const customTimezone = document.getElementById("customTimezone");
const customLat = document.getElementById("customLat");
const customLon = document.getElementById("customLon");
const saveCustomPlace = document.getElementById("saveCustomPlace");
const customPlacesList = document.getElementById("customPlacesList");
const countryFilter = document.getElementById("countryFilter");
const citySelect = document.getElementById("citySelect");
const addDestination = document.getElementById("addDestination");
const destinationList = document.getElementById("destinationList");
const airportUnits = document.getElementById("airportUnits");
const airportRotateSeconds = document.getElementById("airportRotateSeconds");
const lichtColorH = document.getElementById("lichtColorH");
const lichtColorh = document.getElementById("lichtColorh");
const lichtColorM = document.getElementById("lichtColorM");
const lichtColorm = document.getElementById("lichtColorm");
const lichtColorS = document.getElementById("lichtColorS");
const lichtColors = document.getElementById("lichtColors");
const wordClockPanel = document.getElementById("wordClockPanel");
const wordClockLanguage = document.getElementById("wordClockLanguage");
const wordClockStyle = document.getElementById("wordClockStyle");
const wordClockFont = document.getElementById("wordClockFont");

let currentState = null;
let currentPhotos = [];
let currentCities = [];
let maxAirportDestinations = 6;
let currentRotationModes = [];
let currentAirportUnitModes = [];
let airportRotateSecondsRange = { min: 15, max: 3600 };
let lichtzeitpegelColorModes = [];
let wordClockLanguages = [];
let wordClockStyles = [];
let wordClockFonts = [];

function setStatus(message) {
  statusText.textContent = message;
}

function createOption(value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

function countriesFromCities() {
  return Array.from(new Set(currentCities.map((city) => city.country))).sort((a, b) => a.localeCompare(b));
}

function filteredCities() {
  const country = countryFilter.value;
  return currentCities.filter((city) => !country || city.country === country);
}

function customPlaceOptions() {
  return (currentState?.customPlaces || []).map((place) => ({
    value: `custom:${place.id}`,
    label: `${place.country || "Custom"} · ${place.city || place.label}`,
    payload: place,
  }));
}

function cityOptionById(cityId) {
  return currentCities.find((city) => city.id === cityId);
}

function populateDisplayMode() {
  const modes = ["graphic", "world-daylight", "airport-board", "lichtzeitpegel", "word-clock"];
  displayMode.innerHTML = "";
  modes.forEach((mode) => displayMode.appendChild(createOption(mode, mode)));
  displayMode.value = currentState.displayMode;
}

function rotationLabel(mode) {
  const labels = {
    landscape: "Landscape",
    portrait: "Portrait",
    "landscape-flipped": "Landscape Flipped",
    "portrait-flipped": "Portrait Flipped",
  };
  return labels[mode] || mode;
}

function populateRotationMode() {
  const modes = currentRotationModes.length ? currentRotationModes : ["portrait"];
  rotationMode.innerHTML = "";
  modes.forEach((mode) => rotationMode.appendChild(createOption(mode, rotationLabel(mode))));
  rotationMode.value = currentState.rotation || "portrait";
}

function airportUnitLabel(mode) {
  const labels = {
    imperial: "Miles + Fahrenheit",
    metric: "Kilometers + Celsius",
  };
  return labels[mode] || mode;
}

function populateAirportUnits() {
  const modes = currentAirportUnitModes.length ? currentAirportUnitModes : ["imperial", "metric"];
  airportUnits.innerHTML = "";
  modes.forEach((mode) => airportUnits.appendChild(createOption(mode, airportUnitLabel(mode))));
  airportUnits.value = currentState.airportUnits || "imperial";
}

function lichtColorLabel(mode) {
  const labels = {
    amber: "Amber",
    red: "Red",
    green: "Green",
    blue: "Blue",
    purple: "Purple",
    white: "White",
  };
  return labels[mode] || mode;
}

function populateLichtzeitpegelColors() {
  const modes = lichtzeitpegelColorModes.length ? lichtzeitpegelColorModes : ["amber"];
  const controls = {
    H: lichtColorH,
    h: lichtColorh,
    M: lichtColorM,
    m: lichtColorm,
    S: lichtColorS,
    s: lichtColors,
  };
  Object.entries(controls).forEach(([key, control]) => {
    control.innerHTML = "";
    modes.forEach((mode) => control.appendChild(createOption(mode, lichtColorLabel(mode))));
    control.value = currentState.lichtzeitpegelColors?.[key] || "amber";
  });
}

function populateWordClockSettings() {
  wordClockLanguage.innerHTML = "";
  (wordClockLanguages.length ? wordClockLanguages : ["english"]).forEach((mode) => {
    wordClockLanguage.appendChild(createOption(mode, mode));
  });
  wordClockLanguage.value = currentState.wordClockLanguage || "english";

  wordClockStyle.innerHTML = "";
  (wordClockStyles.length ? wordClockStyles : ["direct", "relative"]).forEach((mode) => {
    wordClockStyle.appendChild(createOption(mode, mode));
  });
  wordClockStyle.value = currentState.wordClockStyle || "direct";

  const fontLabels = {
    "classic-sans": "Classic Sans",
    "serif-display": "Serif Display",
    "cursive-italic": "Cursive / Italic",
    "urw-gothic-demi": "URW Gothic Demi",
    "artsy-script": "Artsy Script",
  };
  wordClockFont.innerHTML = "";
  (wordClockFonts.length ? wordClockFonts : ["classic-sans"]).forEach((mode) => {
    wordClockFont.appendChild(createOption(mode, fontLabels[mode] || mode));
  });
  wordClockFont.value = currentState.wordClockFont || "classic-sans";
}

function populateCountryFilter() {
  const countries = countriesFromCities();
  countryFilter.innerHTML = "";
  countryFilter.appendChild(createOption("", "All Countries"));
  countries.forEach((country) => countryFilter.appendChild(createOption(country, country)));
}

function populateCitySelect() {
  const cities = filteredCities();
  citySelect.innerHTML = "";
  cities.forEach((city) => citySelect.appendChild(createOption(city.id, `${city.country} · ${city.city}`)));
}

function populateHomeLocationSelect() {
  homeLocationSelect.innerHTML = "";
  currentCities.forEach((city) => {
    homeLocationSelect.appendChild(createOption(`city:${city.id}`, `${city.country} · ${city.city}`));
  });
  customPlaceOptions().forEach((place) => {
    homeLocationSelect.appendChild(createOption(place.value, place.label));
  });
}

function updateModePanels() {
  const mode = displayMode.value;
  graphicPanel.hidden = mode !== "graphic";
  worldPanel.hidden = mode !== "world-daylight";
  airportPanel.hidden = mode !== "airport-board";
  lichtzeitpegelPanel.hidden = mode !== "lichtzeitpegel";
  wordClockPanel.hidden = mode !== "word-clock";
}

function updateHomeLocationStatus() {
  if (!currentState.homeLocation) {
    homeLocationStatus.textContent = "No home location saved yet.";
    return;
  }
  const home = currentState.homeLocation;
  homeLocationStatus.textContent = `Home: ${home.label} · ${home.city}, ${home.country} (${home.lat.toFixed(3)}, ${home.lon.toFixed(3)})`;
}

function createButton(label, className, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  if (className) button.className = className;
  button.addEventListener("click", onClick);
  return button;
}

function renderGallery() {
  gallery.innerHTML = "";
  if (!currentPhotos.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No photos on the device yet.";
    gallery.appendChild(empty);
    return;
  }
  currentPhotos.forEach((photo) => {
    const card = document.createElement("article");
    card.className = "card";
    if (photo.path === currentState.defaultPhoto) card.classList.add("is-default");

    const image = document.createElement("img");
    image.className = "thumb";
    image.src = photo.url;
    image.alt = photo.name;

    const title = document.createElement("div");
    title.className = "card-title";
    title.textContent = photo.name;

    const source = document.createElement("span");
    source.className = "pill";
    source.textContent = photo.path === currentState.defaultPhoto ? `${photo.source} · default` : photo.source;

    const actions = document.createElement("div");
    actions.className = "toolbar";
    actions.appendChild(createButton("Use in graphic mode", "", () => setDefaultPhoto(photo.path)));
    if (photo.source === "upload") {
      actions.appendChild(createButton("Delete", "danger", () => deletePhoto(photo.name)));
    }

    card.appendChild(image);
    card.appendChild(title);
    card.appendChild(source);
    card.appendChild(actions);
    gallery.appendChild(card);
  });
}

function renderDestinationList() {
  destinationList.innerHTML = "";
  const destinations = currentState.airportDestinations || [];
  if (!destinations.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No destinations selected yet.";
    destinationList.appendChild(empty);
    return;
  }
  destinations.forEach((destinationId) => {
    const city = cityOptionById(destinationId);
    if (!city) return;
    const card = document.createElement("article");
    card.className = "mini-card";
    const title = document.createElement("div");
    title.className = "mini-title";
    title.textContent = `${city.city}, ${city.country}`;
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = city.timezone;
    const actions = document.createElement("div");
    actions.className = "toolbar";
    actions.appendChild(createButton("Remove", "danger", () => removeDestination(destinationId)));
    card.appendChild(title);
    card.appendChild(pill);
    card.appendChild(actions);
    destinationList.appendChild(card);
  });
}

function renderCustomPlaces() {
  customPlacesList.innerHTML = "";
  const places = currentState.customPlaces || [];
  if (!places.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "No custom places saved yet.";
    customPlacesList.appendChild(empty);
    return;
  }
  places.forEach((place) => {
    const card = document.createElement("article");
    card.className = "mini-card";
    const title = document.createElement("div");
    title.className = "mini-title";
    title.textContent = `${place.label} · ${place.city}, ${place.country}`;
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = `${place.lat.toFixed(3)}, ${place.lon.toFixed(3)}`;
    const actions = document.createElement("div");
    actions.className = "toolbar";
    actions.appendChild(createButton("Use as Home", "", () => setHomeLocationFromCustom(place.id)));
    actions.appendChild(createButton("Delete", "danger", () => deleteCustomPlace(place.id)));
    card.appendChild(title);
    card.appendChild(pill);
    card.appendChild(actions);
    customPlacesList.appendChild(card);
  });
}

async function fetchState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const payload = await response.json();
  currentState = payload.state;
  currentPhotos = payload.photos;
  currentCities = payload.cities;
  currentRotationModes = payload.rotationModes || [];
  currentAirportUnitModes = payload.airportUnitModes || [];
  lichtzeitpegelColorModes = payload.lichtzeitpegelColorModes || [];
  wordClockLanguages = payload.wordClockLanguages || [];
  wordClockStyles = payload.wordClockStyles || [];
  wordClockFonts = payload.wordClockFonts || [];
  maxAirportDestinations = payload.maxAirportDestinations || 6;
  airportRotateSecondsRange = payload.airportRotateSecondsRange || airportRotateSecondsRange;

  showAnalog.checked = payload.state.showAnalog !== false;
  mode24.checked = payload.state.mode24 !== false;
  airportRotateSeconds.min = airportRotateSecondsRange.min;
  airportRotateSeconds.max = airportRotateSecondsRange.max;
  airportRotateSeconds.value = payload.state.airportRotateSeconds || 60;
  populateDisplayMode();
  populateRotationMode();
  populateAirportUnits();
  populateLichtzeitpegelColors();
  populateWordClockSettings();
  populateCountryFilter();
  populateCitySelect();
  populateHomeLocationSelect();
  updateModePanels();
  updateHomeLocationStatus();
  renderGallery();
  renderDestinationList();
  renderCustomPlaces();
}

async function updateState(payload, successMessage) {
  const response = await fetch("/api/state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error("Could not update display state.");
  await fetchState();
  setStatus(successMessage);
}

async function setDefaultPhoto(photoPath) {
  setStatus("Updating default photo...");
  await updateState({ defaultPhoto: photoPath }, "Default photo updated.");
}

async function deletePhoto(photoName) {
  setStatus("Deleting photo...");
  const response = await fetch(`/api/photos/${encodeURIComponent(photoName)}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Could not delete photo.");
  await fetchState();
  setStatus("Photo removed from device.");
}

async function uploadPhotos() {
  const files = Array.from(photoInput.files || []);
  if (!files.length) {
    setStatus("Choose at least one photo first.");
    return;
  }
  setStatus("Uploading photos...");
  const body = new FormData();
  files.forEach((file) => body.append("photos", file));
  const response = await fetch("/api/photos", { method: "POST", body });
  if (!response.ok) throw new Error("Upload failed.");
  photoInput.value = "";
  await fetchState();
  setStatus("Upload complete.");
}

async function saveDisplaySettings() {
  setStatus("Saving display settings...");
  await updateState({
    displayMode: displayMode.value,
    rotation: rotationMode.value,
    airportUnits: airportUnits.value,
    airportRotateSeconds: Number(airportRotateSeconds.value || 60),
    wordClockLanguage: wordClockLanguage.value,
    wordClockStyle: wordClockStyle.value,
    wordClockFont: wordClockFont.value,
    lichtzeitpegelColors: {
      H: lichtColorH.value,
      h: lichtColorh.value,
      M: lichtColorM.value,
      m: lichtColorm.value,
      S: lichtColorS.value,
      s: lichtColors.value,
    },
    showAnalog: showAnalog.checked,
    mode24: mode24.checked
  }, "Display settings saved.");
}

function buildHomeLocationFromSelection(value) {
  if (!value) return null;
  if (value.startsWith("city:")) {
    const city = cityOptionById(value.slice(5));
    if (!city) return null;
    return {
      label: city.city,
      city: city.city,
      country: city.country,
      timezone: city.timezone,
      lat: city.lat,
      lon: city.lon,
    };
  }
  if (value.startsWith("custom:")) {
    const place = (currentState.customPlaces || []).find((entry) => entry.id === value.slice(7));
    if (!place) return null;
    return place;
  }
  return null;
}

async function applySelectedHomeLocation() {
  const homeLocation = buildHomeLocationFromSelection(homeLocationSelect.value);
  if (!homeLocation) {
    setStatus("Choose a valid home location first.");
    return;
  }
  setStatus("Saving home location...");
  await updateState({ homeLocation }, "Home location updated.");
}

async function clearSelectedHomeLocation() {
  setStatus("Clearing home location...");
  await updateState({ homeLocation: null }, "Home location cleared.");
}

async function saveCustomPlaceEntry() {
  const label = customLabel.value.trim() || customCity.value.trim() || "Custom place";
  const city = customCity.value.trim();
  const country = customCountry.value.trim();
  const timezone = customTimezone.value.trim() || "UTC";
  const lat = Number(customLat.value);
  const lon = Number(customLon.value);

  if (!city || !country || Number.isNaN(lat) || Number.isNaN(lon)) {
    setStatus("Custom places require city, country, latitude, and longitude.");
    return;
  }

  const updatedPlaces = [...(currentState.customPlaces || []), {
    id: `custom-${Date.now()}`,
    label,
    city,
    country,
    timezone,
    lat,
    lon
  }];

  setStatus("Saving custom place...");
  await updateState({ customPlaces: updatedPlaces }, "Custom place saved.");
  customLabel.value = "";
  customCity.value = "";
  customCountry.value = "";
  customTimezone.value = "";
  customLat.value = "";
  customLon.value = "";
}

async function deleteCustomPlace(placeId) {
  const updatedPlaces = (currentState.customPlaces || []).filter((place) => place.id !== placeId);
  setStatus("Removing custom place...");
  await updateState({ customPlaces: updatedPlaces }, "Custom place removed.");
}

async function setHomeLocationFromCustom(placeId) {
  const place = (currentState.customPlaces || []).find((entry) => entry.id === placeId);
  if (!place) return;
  setStatus("Saving home location...");
  await updateState({ homeLocation: place }, "Home location updated.");
}

async function addSelectedDestination() {
  const destinationId = citySelect.value;
  if (!destinationId) {
    setStatus("Choose a destination city first.");
    return;
  }
  const existing = currentState.airportDestinations || [];
  if (existing.includes(destinationId)) {
    setStatus("That destination is already on the board.");
    return;
  }
  if (existing.length >= maxAirportDestinations) {
    setStatus(`Only ${maxAirportDestinations} destinations are allowed.`);
    return;
  }
  setStatus("Adding destination...");
  await updateState({ airportDestinations: [...existing, destinationId] }, "Destination added.");
}

async function removeDestination(destinationId) {
  const existing = (currentState.airportDestinations || []).filter((id) => id !== destinationId);
  setStatus("Removing destination...");
  await updateState({ airportDestinations: existing }, "Destination removed.");
}

displayMode.addEventListener("change", updateModePanels);
countryFilter.addEventListener("change", populateCitySelect);
uploadButton.addEventListener("click", () => uploadPhotos().catch((error) => setStatus(error.message)));
saveSettings.addEventListener("click", () => saveDisplaySettings().catch((error) => setStatus(error.message)));
applyHomeLocation.addEventListener("click", () => applySelectedHomeLocation().catch((error) => setStatus(error.message)));
clearHomeLocation.addEventListener("click", () => clearSelectedHomeLocation().catch((error) => setStatus(error.message)));
saveCustomPlace.addEventListener("click", () => saveCustomPlaceEntry().catch((error) => setStatus(error.message)));
addDestination.addEventListener("click", () => addSelectedDestination().catch((error) => setStatus(error.message)));

fetchState().then(() => setStatus("Portal connected.")).catch((error) => setStatus(error.message));
