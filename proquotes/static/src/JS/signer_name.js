/** @odoo-module **/

/**
 * Auto signature draws the name that is already in the field. The website
 * public user is "Public user for ...", and that must not be signed.
 * A real customer name, whether the visitor is anonymous or logged in to
 * the portal, is accepted. Draw and load modes are not blocked here.
 */
export function autoSignNameBlocked(name, signMode) {
    if (signMode !== "auto") {
        return false;
    }
    const text = String(name || "").trim();
    if (!text) {
        return false;
    }
    return text === "Public User" || text.toLowerCase().includes("public user");
}
