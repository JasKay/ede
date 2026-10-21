"use strict";
const $ = id => document.getElementById(id);
function node(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }
function message(text, error = false) { $("portal-status").textContent = text; $("portal-status").className = error ? "error" : "success"; }
let key = "", offset = 0, generation = 0, writable = false;
async function api(path, body) {
  const response = await fetch(path, { headers: { Authorization: "Bearer " + key, "Content-Type": "application/json" }, ...(body === undefined ? {} : { method: "POST", body: JSON.stringify(body) }) });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) signOut();
    throw Error(typeof data.detail === "string" ? data.detail : "The request could not be completed.");
  }
  return data;
}
function signOut() { key = ""; generation++; writable = false; $("workspace").hidden = true; $("portal-login").hidden = false; $("sign-out").hidden = true; $("portal-queue").replaceChildren(); $("portal-summary").textContent = ""; $("access-key").value = ""; message("Signed out."); }
function reference(value, label = "Source") {
  const p = node("p", label + ": ", "metadata");
  try { const url = new URL(value); if (url.protocol !== "https:") throw Error(); const a = node("a", value); a.href = url.href; a.target = "_blank"; a.rel = "noopener noreferrer"; p.append(a); }
  catch { p.append(document.createTextNode(value || "Not supplied")); }
  return p;
}
function meaning(sense) {
  const block = node("div", undefined, "dictionary-sense");
  block.append(node("h3", sense.yoruba + " - " + sense.english), node("p", sense.pos + " | " + sense.glosses.join(" / ")));
  if (sense.labels?.length) block.append(node("p", "Labels: " + sense.labels.join(", "), "metadata"));
  for (const note of sense.usage_notes || []) block.append(node("p", note, "metadata"));
  for (const example of sense.examples || []) { const q = node("blockquote", undefined, "usage-example"); const yo = node("p", example.yoruba); yo.lang = "yo"; q.append(yo, node("p", example.english)); block.append(q); }
  block.append(reference(sense.source), reference(sense.history, "Contributor history"), node("p", (sense.attribution || "") + " | " + (sense.license || "not established"), "metadata"));
  return block;
}
function decisions(card, path, yes, no) {
  const note = node("textarea"); note.maxLength = 1000; note.rows = 2;
  const label = node("label", "Review note (optional)"); label.append(note); card.append(label);
  for (const approve of [true, false]) {
    const button = node("button", approve ? yes : no, "secondary"); button.disabled = !writable;
    button.addEventListener("click", async () => {
      const version = generation;
      card.querySelectorAll("button").forEach(b => { b.disabled = true; });
      try { await api(path, { approve, note: note.value.trim() }); if (version !== generation || !key) return; message("Decision saved."); offset = 0; await refresh(); }
      catch (error) { if (version !== generation || !key) return; message(error.message, true); card.querySelectorAll("button").forEach(b => { b.disabled = !writable; }); }
    }); card.append(button, document.createTextNode(" "));
  }
}
function proposalForm(sense) {
  const details = node("details"); details.append(node("summary", "Suggest a synonym for this meaning"));
  const form = node("form");
  const target = node("input"); target.required = true; target.maxLength = 150; target.lang = "yo";
  const label = node("label", "Yoruba synonym, with tone marks"); label.append(target);
  const source = node("input"); source.required = true; source.maxLength = 500;
  const sourceLabel = node("label", "Evidence or source reference"); sourceLabel.append(source);
  const note = node("textarea"); note.maxLength = 1000; const notes = node("label", "Usage, dialect and context"); notes.append(note);
  const submit = node("button", "Save synonym proposal"); submit.disabled = !writable;
  form.append(label, sourceLabel, notes, submit); details.append(form);
  form.addEventListener("submit", async event => {
    event.preventDefault(); submit.disabled = true; const version = generation;
    try { const data = await api("/review/synonyms", { sense_id: sense.id, target: target.value.trim(), source: source.value.trim(), note: note.value.trim() }); if (version !== generation || !key) return; message(data.duplicate ? "This relationship already exists: " + data.status : "Synonym saved for review. It is not public yet."); form.reset(); }
    catch (error) { if (version === generation && key) message(error.message, true); }
    finally { submit.disabled = !writable; }
  });
  return details;
}
async function refresh() {
  const version = ++generation, type = $("queue-type").value;
  $("queue-next").hidden = true; $("queue-back").hidden = true; $("portal-queue").replaceChildren(); $("batch-status").textContent = "Loading...";
  const summary = await api("/review/summary");
  if (version !== generation || !key) return;
  writable = summary.writable;
  $("portal-summary").textContent = summary.contributions + " new words | " + (summary.senses.source_imported || 0) + " meanings | " + (summary.senses.needs_correction || 0) + " flagged | " + summary.synonyms + " synonym proposals. Signed in as " + summary.actor + (writable ? "" : ". Storage is read-only.");
  const params = new URLSearchParams({ offset, limit: 20, q: $("queue-query").value.trim() });
  const path = type === "reviewed" ? "/review/senses?" + params + "&status=editor_reviewed" : type === "approved-synonyms" ? "/review/synonyms?" + params + "&status=approved" : type === "flagged" ? "/review/senses?" + params + "&status=needs_correction" : "/review/" + type + "?" + params;
  const data = await api(path);
  if (version !== generation || !key) return;
  const items = data.contributions || data.senses || data.synonyms || data.actions || [];
  for (const item of items) {
    const card = node("article", undefined, "entry");
    if (type === "contributions") {
      card.append(node("h3", item.translation + " - " + item.english), node("p", "Contributor: " + item.username + " | Dialect: " + item.dialect, "metadata"), node("p", item.context || "No context supplied."), reference(item.source));
      decisions(card, "/review/contributions/" + encodeURIComponent(item.id), "Approve word", "Reject word");
    } else if (type === "senses" || type === "flagged" || type === "reviewed") {
      card.append(meaning(item), node("p", "Sense reference: " + item.id, "metadata"));
      if (item.review_note) card.append(node("p", "Previous review note: " + item.review_note));
      decisions(card, "/review/senses/" + encodeURIComponent(item.id), type === "flagged" ? "Resolve as reviewed" : "Mark meaning reviewed", "Flag for correction");
      if (type === "flagged") card.querySelectorAll("button")[1].disabled = true;
      if (type === "reviewed") card.querySelector("button").disabled = true;
      card.append(proposalForm(item));
    } else if (type === "synonyms" || type === "approved-synonyms") {
      card.append(node("h3", item.sense.yoruba + " / " + item.target), meaning(item.sense), node("p", "Proposed synonym: " + item.target), node("p", "Meaning status: " + item.sense_status, "metadata"), reference(item.provenance.source));
      card.append(node("p", "Origin: " + item.provenance.origin + " | Licence: " + item.provenance.license, "metadata"));
      if (item.provenance.qualifiers?.length) card.append(node("p", "Source qualifiers: " + item.provenance.qualifiers.join(", ")));
      if (item.provenance.note) card.append(node("p", item.provenance.note));
      if (item.provenance.history) card.append(reference(item.provenance.history, "Contributor history"));
      const targetDetails = node("details"); targetDetails.append(node("summary", "Compare target meanings"));
      let loaded = false;
      targetDetails.addEventListener("toggle", async () => {
        if (!targetDetails.open || loaded) return;
        loaded = true;
        try {
          const target = await api("/dictionary/word?" + new URLSearchParams({ headword: item.target }));
          for (const sense of target.senses) targetDetails.append(meaning(sense));
        } catch { targetDetails.append(node("p", "No sourced definition could be loaded for this target. Check the original reference before approval.", "hint")); }
      }); card.append(targetDetails);
      decisions(card, "/review/synonyms/" + encodeURIComponent(item.id), "Approve synonym", type === "approved-synonyms" ? "Withdraw synonym" : "Reject synonym");
      if (type === "approved-synonyms") card.querySelector("button").disabled = true;
    } else {
      card.append(node("h3", item.record_type + ": " + item.decision), node("p", item.note || "No note provided."), node("p", item.created_at + " | " + item.actor, "metadata"), node("p", "Record: " + item.record_id, "metadata"));
    }
    $("portal-queue").append(card);
  }
  $("batch-status").textContent = items.length ? "Batch " + (Math.floor(offset / 20) + 1) + ": " + items.length + " records" : "No records in this batch.";
  $("queue-back").hidden = offset === 0;
  $("queue-next").hidden = items.length < 20;
}
async function reload() { try { await refresh(); } catch (error) { if (key) message(error.message, true); else message("Sign-in failed: " + error.message, true); $("batch-status").textContent = "Queue could not be loaded."; } }
$("portal-login").addEventListener("submit", async event => {
  event.preventDefault(); key = $("access-key").value; $("access-key").value = "";
  try { await api("/review/summary"); $("workspace").hidden = false; $("portal-login").hidden = true; $("sign-out").hidden = false; message("Signed in. Choose a queue to begin."); offset = 0; await reload(); }
  catch (error) { signOut(); message("Sign-in failed: " + error.message, true); }
});
$("sign-out").addEventListener("click", signOut);
$("queue-controls").addEventListener("submit", event => { event.preventDefault(); offset = 0; reload(); });
$("queue-type").addEventListener("change", () => { offset = 0; $("queue-query").disabled = ["contributions", "history"].includes($("queue-type").value); reload(); });
$("queue-query").disabled = true;
$("queue-next").addEventListener("click", () => { offset += 20; reload(); });
$("queue-back").addEventListener("click", () => { offset = Math.max(0, offset - 20); reload(); });
