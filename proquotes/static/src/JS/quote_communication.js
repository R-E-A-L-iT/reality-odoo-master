/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// Post-processes the stock portal chatter (#sale_order_communication) on the
// quote preview page: strips the "Published on" prefix, tries to split a
// combined "Name (Company)"-style author line onto two lines with the date
// alongside the company, and collapses consecutive duplicate "quote viewed"
// style messages into one with a ×N badge.
//
// This widget is deliberately defensive rather than hard-coded to one exact
// class/markup shape: portal_chatter is a core OWL component we don't
// control or have local source for, its messages render/re-render
// asynchronously after this widget's own start(), and if any of these
// assumptions turn out wrong on the live site this should degrade to a
// no-op on that specific piece rather than throwing or corrupting content.

const MERGE_WINDOW_MS = 10 * 60 * 1000;
// Not anchored to the start (^) — on the live page this text sits directly
// after the author/actor name with no separating whitespace in the source
// ("Pete WittmaierPublished on Jul 7, 2026, ..."), all inside what's
// apparently one element, so a ^-anchored match against that combined text
// never matched at all.
const PUBLISHED_ON_RE = /Published on\s*/i;
// Only the literal "Name (Company)" parenthetical form — a comma/dash
// version too ("R-E-A-L.iT Solutions, Ézékiel deBlois") turned out to be
// Company-then-Name on the live page, the reverse of this pattern, and
// there's no reliable way to tell the two orderings apart from text alone.
const NAME_COMPANY_RE = /^(.+?)\s*\((.+?)\)\s*$/;

function findMessageContainer(root) {
    return (
        root.querySelector(".o_portal_chatter_messages") ||
        root.querySelector(".o_portal_chatter") ||
        root
    );
}

function findMessageEls(container) {
    const byClass = container.querySelectorAll(".o_portal_chatter_message");
    if (byClass.length) {
        return Array.from(byClass);
    }
    // Fallback: direct element children of whatever holds the messages,
    // skipping the composer (textarea/button) block if it's a sibling here.
    return Array.from(container.children).filter(
        (el) => !el.matches(".o_portal_chatter_composer, form, textarea")
    );
}

function findAvatarEl(msgEl) {
    return msgEl.querySelector("img");
}

// Wraps the avatar <img> in its own positioned container so the repeat
// badge can sit absolutely positioned over its corner (see
// .quote-message-avatar-wrap / .quote-message-repeat-badge in
// quotePreview.css) instead of inline in the message text — idempotent,
// safe to call repeatedly across re-renders.
function getAvatarWrap(msgEl) {
    const existing = msgEl.querySelector(".quote-message-avatar-wrap");
    if (existing) {
        return existing;
    }
    const avatarEl = findAvatarEl(msgEl);
    if (!avatarEl) {
        return msgEl;
    }
    const wrap = document.createElement("div");
    wrap.className = "quote-message-avatar-wrap";
    avatarEl.parentElement.insertBefore(wrap, avatarEl);
    wrap.appendChild(avatarEl);
    return wrap;
}

function findDateEl(msgEl) {
    // Once stripPublishedOn() removes the "Published on" text, the
    // text-content heuristic below can no longer find this element on a
    // later call (nothing left in it to match against) — tag it the first
    // time it's found so every later lookup for this same message can
    // still locate it directly regardless of what its text says by then.
    const tagged = msgEl.querySelector("[data-quote-date-el]");
    if (tagged) {
        return tagged;
    }
    // .o_portal_chatter_puslished_date (sic — that's the real, misspelled
    // class Odoo's own template uses) confirmed from a live DOM dump.
    let found =
        msgEl.querySelector(".o_portal_chatter_puslished_date") ||
        msgEl.querySelector(".o_portal_chatter_message_date") ||
        msgEl.querySelector("time");
    if (!found) {
        // querySelectorAll returns document order, so a broad wrapper div
        // (which also "contains" this text via its own descendants) would
        // otherwise win just by appearing before its more specific
        // children — picking the shortest matching text instead favors the
        // most specific element actually holding the date, not some large
        // container around the whole message.
        const candidates = Array.from(msgEl.querySelectorAll("span, small, div")).filter((el) =>
            PUBLISHED_ON_RE.test(el.textContent)
        );
        if (candidates.length) {
            found = candidates.reduce((a, b) => (a.textContent.length <= b.textContent.length ? a : b));
        }
    }
    if (found) {
        found.dataset.quoteDateEl = "1";
        // Parsed and cached right now, before stripPublishedOn() (called
        // immediately after this element is first tagged) removes the
        // "Published on" text this parsing depends on — parseMessageDate()
        // reads this cached value back instead of re-parsing live text
        // that may no longer contain what it's looking for by then.
        const afterLabel = found.textContent.match(/Published on\s*(.+)/i);
        const dateText = afterLabel ? afterLabel[1].trim() : found.textContent.trim();
        const parsed = new Date(dateText);
        found.dataset.quoteParsedDate = isNaN(parsed) ? "" : parsed.toISOString();
    }
    return found;
}

function findAuthorEl(msgEl) {
    // .o_portal_chatter_message_title wraps *both* the name (h5) and the
    // date paragraph together (confirmed from a live DOM dump) — prefer
    // just the h5 inside it so this returns the name specifically, not the
    // date glued alongside it.
    const title = msgEl.querySelector(".o_portal_chatter_message_title");
    if (title) {
        return title.querySelector("h5") || title;
    }
    return msgEl.querySelector("b, strong, h5, h6") || null;
}

// No dedicated body element found on the live page (or at least none of
// the class names guessed at below) — falling back to the whole message's
// text would include the author/date text too, and since the date differs
// message to message that made every "same body" comparison in
// mergeDuplicateMessages() fail even for genuinely identical messages.
// Subtracting out whatever's identified as the author/date text first
// isolates just the actual content instead.
function getBodyText(msgEl, authorEl, dateEl) {
    const bodyEl = msgEl.querySelector(
        ".o_portal_chatter_message_body, .o-mail-Message-body, .o_Message_body"
    );
    if (bodyEl) {
        return bodyEl.textContent.trim();
    }
    // No dedicated body element on the live markup either — the actual
    // content is just a bare <p>, a sibling of .o_portal_chatter_message_title
    // and the .float-end "Internal Note"/public-toggle badge, all inside
    // the same .flex-grow-1. Subtracting all of those out isolates it.
    let text = msgEl.textContent;
    if (authorEl) {
        text = text.replace(authorEl.textContent, "");
    }
    if (dateEl) {
        text = text.replace(dateEl.textContent, "");
    }
    const floatEnd = msgEl.querySelector(".float-end");
    if (floatEnd) {
        text = text.replace(floatEnd.textContent, "");
    }
    return text.trim();
}

function stripPublishedOn(dateEl) {
    if (!dateEl) {
        return;
    }
    for (const node of dateEl.childNodes) {
        if (node.nodeType === Node.TEXT_NODE && PUBLISHED_ON_RE.test(node.textContent)) {
            // A space, not empty string — on the live page this text sits
            // directly against the preceding name with no source
            // whitespace, so a plain removal would fuse them together
            // ("Pete WittmaierJul 7, ...") instead of just dropping the
            // "Published on" wording.
            node.textContent = node.textContent.replace(PUBLISHED_ON_RE, " ");
        }
    }
}

// Best-effort machine-readable timestamp: a datetime/title attribute if one
// exists (common for elements showing a humanized "3 minutes ago" string
// with the exact time in a hover title), otherwise tries to parse the
// visible text directly — which only works if it's an absolute date/time,
// not a relative string, so this intentionally returns null rather than
// guessing when it can't be sure.
function parseMessageDate(msgEl) {
    const dateEl = findDateEl(msgEl);
    if (!dateEl) {
        return null;
    }
    const attr =
        dateEl.getAttribute("datetime") ||
        dateEl.getAttribute("data-message-date") ||
        dateEl.getAttribute("title");
    if (attr) {
        const fromAttr = new Date(attr);
        if (!isNaN(fromAttr)) {
            return fromAttr;
        }
    }
    // Cached at discovery time in findDateEl(), before stripPublishedOn()
    // could remove the text this depends on — see the comment there.
    if (dateEl.dataset.quoteParsedDate) {
        return new Date(dateEl.dataset.quoteParsedDate);
    }
    return null;
}

// Splits "Jane Smith (Speedwell Construction)" into a two-line layout —
// name on top, company name small underneath, with the date moved down
// next to the company. Only restructures when the author text actually
// matches that combined pattern; a plain "Jane Smith" with no parenthetical
// is left exactly as-is (nothing to split out).
function restructureAuthorLine(msgEl) {
    const authorEl = findAuthorEl(msgEl);
    const dateEl = findDateEl(msgEl);
    if (!authorEl || authorEl.dataset.quoteRestructured) {
        return;
    }

    const match = authorEl.textContent.trim().match(NAME_COMPANY_RE);
    if (!match) {
        return;
    }
    const [, name, company] = match;
    if (!company) {
        return;
    }

    authorEl.dataset.quoteRestructured = "1";
    authorEl.textContent = "";

    const nameLine = document.createElement("div");
    nameLine.className = "quote-message-author-name";
    nameLine.textContent = name.trim();

    const subLine = document.createElement("div");
    subLine.className = "quote-message-author-sub";

    const companySpan = document.createElement("span");
    companySpan.className = "quote-message-author-company";
    companySpan.textContent = company.trim();
    subLine.appendChild(companySpan);

    if (dateEl) {
        const dateSpan = document.createElement("span");
        dateSpan.className = "quote-message-author-date";
        dateSpan.textContent = dateEl.textContent.trim();
        subLine.appendChild(dateSpan);
        dateEl.remove();
    }

    authorEl.appendChild(nameLine);
    authorEl.appendChild(subLine);
}

function mergeDuplicateMessages(container) {
    const msgEls = findMessageEls(container);
    let lastKept = null;
    let lastBody = null;
    let lastDate = null;
    let count = 1;

    for (const msgEl of msgEls) {
        if (msgEl.dataset.quoteMergedAway) {
            continue;
        }
        const body = getBodyText(msgEl, findAuthorEl(msgEl), findDateEl(msgEl));
        const date = parseMessageDate(msgEl);

        const isDuplicate =
            lastKept &&
            body &&
            body === lastBody &&
            date &&
            lastDate &&
            Math.abs(date - lastDate) <= MERGE_WINDOW_MS;

        if (isDuplicate) {
            count += 1;
            msgEl.dataset.quoteMergedAway = "1";
            // Confirmed from a live DOM dump: these message rows carry
            // Bootstrap's .d-flex utility class, which Bootstrap itself
            // declares as `display: flex !important` — a plain (non-
            // important) inline style here loses to that every time, which
            // is why messages correctly marked/parsed as duplicates were
            // still visibly showing. An inline !important always wins
            // regardless of what importance level the competing rule is.
            msgEl.style.setProperty("display", "none", "important");

            let badge = lastKept.querySelector(".quote-message-repeat-badge");
            if (!badge) {
                badge = document.createElement("span");
                badge.className = "quote-message-repeat-badge";
                getAvatarWrap(lastKept).appendChild(badge);
            }
            badge.textContent = "×" + count;
        } else {
            lastKept = msgEl;
            lastBody = body;
            lastDate = date;
            count = 1;
        }
    }
}

function processMessages(root) {
    const container = findMessageContainer(root);
    const msgEls = findMessageEls(container);

    for (const msgEl of msgEls) {
        const avatarEl = findAvatarEl(msgEl);
        if (avatarEl) {
            avatarEl.classList.add("quote-message-avatar");
        }
        getAvatarWrap(msgEl);
        stripPublishedOn(findDateEl(msgEl));
        restructureAuthorLine(msgEl);
    }

    mergeDuplicateMessages(container);
}

publicWidget.registry.quoteCommunication = publicWidget.Widget.extend({
    selector: "#sale_order_communication",

    async start() {
        await this._super(...arguments);

        // portal_chatter renders/re-renders its message list asynchronously
        // (initial load, after posting a new message, etc.) well after this
        // widget's own start() — reprocessing on every mutation is the only
        // reliable way to catch all of those instead of just the first one.
        let raf = null;
        const schedule = () => {
            if (raf) {
                return;
            }
            raf = requestAnimationFrame(() => {
                raf = null;
                processMessages(this.el);
            });
        };

        schedule();
        new MutationObserver(schedule).observe(this.el, { childList: true, subtree: true });
    },
});
