/**
 * Settings → Auth panel orchestrator.
 *
 * Single responsibility: own the lifecycle of the four sub-forms
 * (password change, sign-out everywhere, viewer role, lockout) and
 * keep them in sync with ``/api/identity``. The controller does not
 * render any HTML itself -- it expects the panel structure to be
 * present in ``index.html`` and binds behaviour to the data
 * attributes those nodes carry.
 *
 * Lifecycle:
 *   const ctrl = new AuthPanelController(rootEl);
 *   ctrl.bind();          // wires form submissions
 *   await ctrl.refresh(); // pulls live config + viewer state
 *
 * The orchestrator only cares about coordination -- each sub-form
 * owns its own DOM and its own request shape.
 */

class AuthPanelController {
    constructor(rootEl) {
        this.root = rootEl;
        this.passwordChange = new window.PasswordChangeForm(
            rootEl.querySelector('[data-pwc-root]')
        );
        this.signOutAll = new window.SignOutAllForm(
            rootEl.querySelector('[data-sigout-all-root]')
        );
        this.viewerRole = new window.ViewerRoleForm(
            rootEl.querySelector('[data-viewer-root]')
        );
        this.lockout = new window.LockoutConfigForm(
            rootEl.querySelector('[data-lockout-root]')
        );
    }

    bind() {
        this.passwordChange.bind();
        this.signOutAll.bind();
        this.viewerRole.bind();
        this.lockout.bind();
    }

    async refresh() {
        const identity = await this._fetchIdentity();
        if (!identity) return;
        this.viewerRole.setEnabled(!!identity.viewer_enabled);
        // Lockout values are not yet exposed on /api/identity to keep
        // the public response small. The defaults shown match the
        // server-side defaults; once the operator saves, the form
        // round-trip confirms the persisted values.
    }

    async _fetchIdentity() {
        try {
            const response = await fetch('/api/identity', {
                credentials: 'same-origin',
                cache: 'no-store',
            });
            if (!response.ok) return null;
            return await response.json();
        } catch (_e) {
            return null;
        }
    }
}

window.AuthPanelController = AuthPanelController;
