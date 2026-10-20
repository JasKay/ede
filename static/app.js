"use strict";
const $ = id => document.getElementById(id);
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function status(id, text, kind = "") {
  $(id).textContent = text;
  $(id).className = kind;
}
async function request(url, options = {}) {
  const response = await fetch(url, { ...options, headers: { "Content-Type": "application/json", ...options.headers } });
  const data = await response.json();
  if (!response.ok || data.success === false) {
    throw new Error(typeof data.detail === "string" ? data.detail : "The request could not be completed. Check the fields and try again.");
  }
  return data;
}
function sourceNode(source) {
  try {
    const url = new URL(source);
    if (url.protocol === "https:") {
      const a = element("a", source);
      a.href = url.href; a.target = "_blank"; a.rel = "noopener noreferrer";
      return a;
    }
  } catch { /* Source names are usually dataset identifiers, not URLs. */ }
  return element("span", source);
}
function senseContent(sense) {
  const block = element("section", undefined, "dictionary-sense");
  const labels = { source_imported: "Source imported · awaiting Ede review", editor_reviewed: "Editor reviewed · not native-speaker verified", needs_correction: "Flagged for correction" };
  block.append(element("p", labels[sense.review_status] || labels.source_imported, sense.review_status === "needs_correction" ? "error" : "sense-status"));
  block.append(element("h4", sense.pos + " · " + sense.glosses.join(" → ")));
  if (sense.labels.length) block.append(element("p", "Source labels: " + sense.labels.join(", "), "metadata"));
  for (const note of sense.usage_notes || []) block.append(element("p", "Source usage note: " + note, "metadata"));
  for (const example of sense.examples || []) {
    const quote = element("blockquote", undefined, "usage-example");
    const yoruba = element("p", example.yoruba); yoruba.lang = "yo";
    quote.append(yoruba, element("p", example.english, "example-english"));
    block.append(quote);
  }
  if (!sense.examples.length) block.append(element("p", "No sourced usage example in this extract.", "metadata"));
  const attribution = element("p", sense.attribution + " · ", "metadata");
  for (const [name, url] of [["Source entry", sense.source], ["Contributors & history", sense.history], ["CC BY-SA 4.0", sense.license_url]]) {
    const link = sourceNode(url); link.textContent = name;
    attribution.append(link, document.createTextNode(" · "));
  }
  block.append(attribution, element("p", "Adapted source data; extraction can contain errors. No endorsement by Wiktionary or Kaikki.", "metadata"));
  return block;
}
function entryCard(entry) {
  const card = element("article", undefined, "entry");
  const heading = element("div", undefined, "entry-heading");
  heading.append(element("h3", entry.english), element("span",
    (entry.senses || []).length ? "Dictionary source" : entry.status === "editor_reviewed" ? "Editor reviewed" : "Imported · unverified", "badge"));
  const translation = element("p", entry.translation, "translation"); translation.lang = "yo";
  card.append(heading, translation);
  for (const sense of entry.senses || []) card.append(senseContent(sense));
  card.append(element("p", (entry.senses || []).length ? "Sourced dictionary headword" : entry.entry_kind === "word" ? "Single-word corpus pair" : "Phrase or sentence record", "metadata"));
  if (entry.entry_kind === "phrase") {
    const detail = element("details");
    detail.append(element("summary", "Explore individual words"));
    detail.append(element("p", "English and Yoruba words are listed separately. These are token lookups, not aligned translations.", "hint"));
    for (const [label, words, lang] of [["English", entry.english_words, "en"], ["Yoruba", entry.yoruba_words, "yo"]]) {
      detail.append(element("p", label, "metadata"));
      const tokens = element("div", undefined, "examples");
      for (const word of words || []) {
        const button = element("button", word);
        button.type = "button"; button.lang = lang;
        button.addEventListener("click", () => {
          $("query").value = word; $("record-kind").value = "word";
          search(false); $("search-results").scrollIntoView({ behavior: "smooth" });
        });
        tokens.append(button);
      }
      detail.append(tokens);
    }
    card.append(detail);
  }
  card.append(element("p", "Yoruba · Dialect: " + entry.dialect + " · Domain: " + entry.domain, "metadata"));
  const sources = element("p", "Sources: ", "metadata");
  entry.sources.forEach((source, i) => { if (i) sources.append(document.createTextNode(" · ")); sources.append(sourceNode(source)); });
  card.append(sources);
  card.append(element("p", "Licence: " + entry.license + " · Confidence: not established · Native-speaker verification: not established", "metadata"));
  const button = element("button", "Suggest a correction", "secondary");
  button.type = "button";
  button.addEventListener("click", () => {
    $("english").value = entry.english;
    $("yoruba").value = entry.translation;
    $("context").value = "Correction to corpus record " + entry.id + ": ";
    $("contribute").scrollIntoView({ behavior: "smooth" });
    $("yoruba").focus({ preventScroll: true });
  });
  card.append(button);
  return card;
}
let contributionsEnabled = false;
async function loadStats() {
  try {
    const data = await request("/stats");
    $("entry-count").textContent = data.total_entries.toLocaleString();
    $("corpus-breakdown").textContent = data.dictionary_headwords.toLocaleString() + " sourced dictionary headwords ? " + data.dictionary_senses.toLocaleString() + " senses ? " + data.word_entries.toLocaleString() + " word records ? " + data.phrase_entries.toLocaleString() + " longer corpus records.";
    $("reviewed-count").textContent = data.reviewed_senses.toLocaleString();
    $("pending-count").textContent = data.pending_contributions.toLocaleString();
    status("data-status", data.data_errors.length ? "Some corpus files could not be imported. Loaded records are searchable; an operator should inspect the import errors." :
      data.ready ? "Counts reflect the loaded corpus. Imported records have not been verified by native speakers." :
      "No corpus is loaded. Search results and counts will remain empty until a real dataset is imported.", data.data_errors.length || !data.ready ? "error" : "");
    contributionsEnabled = data.contributions_enabled;
    $("submit-contribution").disabled = !contributionsEnabled;
    if (!data.contributions_enabled) status("contribution-status", data.storage_note, "error");
    $("examples").replaceChildren();
    for (const text of data.examples) {
      const button = element("button", text);
      button.type = "button";
      button.addEventListener("click", () => { $("query").value = text; search(false); });
      $("examples").append(button);
    }
  } catch (error) { status("data-status", "Could not check corpus availability: " + error.message, "error"); }
}
let controller, activeQuery = "", activeKind = "word", offset = 0, searchVersion = 0;
async function search(more) {
  const query = more ? activeQuery : $("query").value.trim();
  const kind = more ? activeKind : $("record-kind").value;
  if (controller) controller.abort();
  controller = new AbortController();
  const version = ++searchVersion;
  if (!more) { activeQuery = query; activeKind = kind; offset = 0; $("results").replaceChildren(); }
  $("more").hidden = true;
  $("search-results").setAttribute("aria-busy", "true");
  status("search-status", "Searching the corpus…");
  try {
    const data = await request((query ? "/search?" : "/browse?") + new URLSearchParams({ ...(query ? { q: query } : {}), kind, limit: "20", offset: String(offset) }), { signal: controller.signal });
    if (version !== searchVersion) return;
    $("results-title").textContent = query ? "Matches for " + query : ({ word: "Individual words", phrase: "Phrases & sentences", all: "All corpus records" })[kind];
    $("result-count").textContent = data.total.toLocaleString() + " translation pairs";
    for (const entry of data.entries) $("results").append(entryCard(entry));
    offset += data.entries.length;
    $("more").hidden = offset >= data.total;
    status("search-status", data.total ? "Results are corpus records. Their verification status and available sources appear below." :
      "No matching record was found. This does not mean a Yoruba translation does not exist. You can suggest an entry below.");
    if (!more && query) $("english").value = query;
    const url = new URL(location.href); if (query) url.searchParams.set("q", query); else url.searchParams.delete("q"); url.searchParams.set("kind", kind); history.replaceState(null, "", url);
  } catch (error) {
    if (error.name !== "AbortError") {
      status("search-status", "Search failed: " + error.message, "error");
      if (more) $("more").hidden = false;
    }
  } finally { if (version === searchVersion) $("search-results").setAttribute("aria-busy", "false"); }
}
$("search-form").addEventListener("submit", event => { event.preventDefault(); search(false); });
$("more").addEventListener("click", () => search(true));
$("record-kind").addEventListener("change", () => search(false));
$("contribution-form").addEventListener("submit", async event => {
  event.preventDefault();
  const button = $("submit-contribution"); button.disabled = true;
  const fields = new FormData(event.currentTarget);
  const body = {
    word: String(fields.get("word")).trim(), translation: String(fields.get("translation")).trim(),
    language: "Yoruba", username: String(fields.get("username")).trim() || "Anonymous",
    dialect: String(fields.get("dialect")).trim() || "unspecified",
    context: String(fields.get("context")).trim(), source: String(fields.get("source")).trim(),
    consent: fields.get("consent") === "on"
  };
  status("contribution-status", "Saving your submission…");
  try {
    const data = await request("/contribute", { method: "POST", body: JSON.stringify(body) });
    status("contribution-status", (data.duplicate ? "This suggestion is already awaiting review." : data.message) + " Reference: " + data.id, "success");
    $("contribution-form").reset();
    await loadStats();
  } catch (error) {
    status("contribution-status", error.message + " Your text remains in the form.", "error");
  } finally { button.disabled = !contributionsEnabled; }
});
let reviewToken = "";
async function loadQueue() {
  const data = await request("/review/contributions", { headers: { Authorization: "Bearer " + reviewToken } });
  $("review-queue").replaceChildren();
  status("review-status", data.contributions.length + " community suggestions in this batch.");
  for (const item of data.contributions) {
    const card = element("article", undefined, "entry");
    card.append(element("h3", item.english + " → " + item.translation));
    card.append(element("p", "Submitted by " + item.username + " · Dialect: " + item.dialect, "metadata"));
    card.append(element("p", item.context || "No context provided."));
    card.append(element("p", "Reference: " + (item.source || "Not supplied"), "metadata"));
    for (const approve of [true, false]) {
      const button = element("button", approve ? "Approve as editor-reviewed" : "Reject", "secondary");
      button.type = "button";
      button.addEventListener("click", async () => {
        card.querySelectorAll("button").forEach(b => { b.disabled = true; });
        try {
          await request("/review/contributions/" + encodeURIComponent(item.id), {
            method: "POST", headers: { Authorization: "Bearer " + reviewToken },
            body: JSON.stringify({ approve })
          });
          await loadQueue(); await loadStats();
        } catch (error) {
          status("review-status", error.message, "error");
          card.querySelectorAll("button").forEach(b => { b.disabled = false; });
        }
      });
      card.append(button, document.createTextNode(" "));
    }
    $("review-queue").append(card);
  }
  $("sense-filter-form").hidden = false;
  const dictionary = await request("/review/senses?" + new URLSearchParams({ q: $("sense-filter").value.trim() }), { headers: { Authorization: "Bearer " + reviewToken } });
  $("review-queue").append(element("h3", "Dictionary senses awaiting editor review"));
  for (const sense of dictionary.senses) {
    const card = element("article", undefined, "entry");
    card.append(element("h3", sense.yoruba + " — " + sense.english), senseContent(sense));
    for (const approve of [true, false]) {
      const button = element("button", approve ? "Mark this sense reviewed" : "Flag for correction", "secondary");
      button.type = "button";
      button.addEventListener("click", async () => {
        card.querySelectorAll("button").forEach(b => { b.disabled = true; });
        try {
          await request("/review/senses/" + encodeURIComponent(sense.id), {
            method: "POST", headers: { Authorization: "Bearer " + reviewToken }, body: JSON.stringify({ approve })
          });
          await loadQueue(); await loadStats();
        } catch (error) {
          status("review-status", error.message, "error");
          card.querySelectorAll("button").forEach(b => { b.disabled = false; });
        }
      });
      card.append(button, document.createTextNode(" "));
    }
    $("review-queue").append(card);
  }

}
$("review-form").addEventListener("submit", async event => {
  event.preventDefault(); reviewToken = $("review-token").value; $("review-token").value = "";
  try { await loadQueue(); } catch (error) { reviewToken = ""; status("review-status", error.message, "error"); }
});
$("sense-filter-form").addEventListener("submit", async event => {
  event.preventDefault();
  try { await loadQueue(); } catch (error) { status("review-status", error.message, "error"); }
});
const initial = new URLSearchParams(location.search).get("q");
if (initial) $("query").value = initial;
const initialKind = new URLSearchParams(location.search).get("kind");
if (["word", "phrase", "all"].includes(initialKind)) $("record-kind").value = initialKind;
loadStats().then(() => search(false));
