/** Lower case, without accents when `normalize`: the combobox search compares these (DOM-free). */
export function searchText(text, normalize = false) {
  const lower = String(text ?? "").toLowerCase().trim();
  return normalize ? lower.normalize("NFD").replace(/[\u0300-\u036F]/g, "") : lower;
}
