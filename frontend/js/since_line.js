/**
 * "Since you last looked" delta line.
 *
 * Renders a single muted line at the top of a page summarising what
 * has changed since the user last visited it. Format:
 *
 *     Since 4 min ago: 12 packets · 1 NodeInfo broadcast · 2 messages
 *     Since just now: nothing yet
 *
 * Single responsibility: render. The page-specific data fetch lives
 * in the caller, which passes a snapshot to update().
 */
class SinceLine {
    constructor(hostEl) {
        this._host = hostEl;
        this._root = null;
    }

    mount() {
        if (!this._host || this._root) return;
        const root = document.createElement('div');
        root.className = 'since-line';
        root.setAttribute('role', 'status');
        root.setAttribute('aria-live', 'polite');
        root.innerHTML = `
            <span class="since-line__prefix">Since</span>
            <span class="since-line__when" id="since-line-when">just now</span>
            <span class="since-line__sep" aria-hidden="true">·</span>
            <span class="since-line__items" id="since-line-items">nothing yet</span>
        `;
        this._host.insertBefore(root, this._host.firstChild);
        this._root = root;
    }

    /**
     * snapshot = {
     *     lastVisitAt: number|null,
     *     items: [{label, count}],
     * }
     */
    update(snapshot) {
        if (!this._root) return;
        const whenEl = this._root.querySelector('#since-line-when');
        const itemsEl = this._root.querySelector('#since-line-items');
        const last = snapshot && snapshot.lastVisitAt;
        whenEl.textContent = _formatRelative(last);

        const items = (snapshot && Array.isArray(snapshot.items))
            ? snapshot.items.filter((i) => i && i.count > 0)
            : [];
        if (items.length === 0) {
            itemsEl.textContent = 'nothing yet';
            this._root.classList.add('since-line--quiet');
            return;
        }
        itemsEl.textContent = items
            .map((i) => `${i.count} ${i.label}`)
            .join(' · ');
        this._root.classList.remove('since-line--quiet');
    }
}

function _formatRelative(timestamp) {
    if (!timestamp) return 'just now';
    const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
    if (seconds < 30) return 'just now';
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hr ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

window.SinceLine = SinceLine;
