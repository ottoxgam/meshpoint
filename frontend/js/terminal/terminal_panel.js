/**
 * Terminal panel orchestrator.
 *
 * Single responsibility: glue the xterm.js renderer to the
 * ``TerminalClient`` WebSocket, the ``CommandDrawer``, and the
 * status indicators on the panel header. No business logic, no
 * direct DOM authoring -- the markup lives in ``index.html`` and
 * this class only wires events.
 *
 * Lifecycle is lazy: the controller is constructed once at app
 * boot, but the xterm instance + WebSocket only spin up the first
 * time the operator clicks Connect. That keeps the dashboard
 * responsive for users who never visit the Terminal section.
 */

class TerminalPanelController {
    constructor(rootEl) {
        this.root = rootEl;
        this.hostEl = rootEl.querySelector('#terminal-host');
        this.statusEl = rootEl.querySelector('[data-term-status]');
        this.connectBtn = rootEl.querySelector('[data-term-connect]');
        this.disconnectBtn = rootEl.querySelector('[data-term-disconnect]');
        this.clearBtn = rootEl.querySelector('[data-term-clear]');
        this.toggleBtn = rootEl.querySelector('[data-term-toggle-drawer]');
        this.closeBtn = rootEl.querySelector('[data-term-close-drawer]');
        this.drawerEl = rootEl.querySelector('[data-term-drawer]');
        this.hintEl = rootEl.querySelector('[data-term-hint]');
        this.client = new window.TerminalClient();
        this.term = null;
        this.fitAddon = null;
        this.drawer = new window.CommandDrawer(this.drawerEl, {
            toggleBtn: this.toggleBtn,
            closeBtn: this.closeBtn,
            onInsert: (cmd) => this._insertCommand(cmd),
        });
        this._resizeBound = false;
        this._loadedCommands = false;
    }

    bind() {
        this.drawer.bind();
        this.connectBtn?.addEventListener('click', () => this.connect());
        this.disconnectBtn?.addEventListener('click', () => this.disconnect());
        this.clearBtn?.addEventListener('click', () => this.term?.clear());
        this._wireClientCallbacks();
    }

    async refresh() {
        if (this._loadedCommands) return;
        this._loadedCommands = true;
        await this.drawer.load();
    }

    onSectionEnter() {
        if (this.term) {
            this.fitAddon?.fit();
        }
    }

    connect() {
        if (this.client.connected) return;
        this._ensureXterm();
        this._setStatus('connecting', 'connecting…');
        this.client.connect();
    }

    disconnect() {
        this.client.disconnect();
    }

    _ensureXterm() {
        if (this.term) return;
        if (!window.Terminal) {
            this._setStatus('error', 'xterm not loaded');
            return;
        }
        this.term = new window.Terminal({
            cursorBlink: true,
            fontFamily: 'JetBrains Mono, Menlo, Consolas, monospace',
            fontSize: 13,
            theme: {
                background: '#0c0f14',
                foreground: '#e6e6e6',
                cursor: '#ffb84d',
                cursorAccent: '#0c0f14',
                selectionBackground: 'rgba(255,184,77,0.25)',
            },
            allowProposedApi: true,
        });
        if (window.FitAddon) {
            this.fitAddon = new window.FitAddon.FitAddon();
            this.term.loadAddon(this.fitAddon);
        }
        this.term.open(this.hostEl);
        this.term.onData((data) => this.client.sendInput(data));
        this.term.onResize(({ rows, cols }) => this.client.sendResize(rows, cols));
        if (this.fitAddon) {
            requestAnimationFrame(() => this.fitAddon.fit());
        }
        if (!this._resizeBound) {
            this._resizeBound = true;
            window.addEventListener('resize', () => this.fitAddon?.fit());
        }
    }

    _wireClientCallbacks() {
        this.client.onOpen = () => {
            this._setStatus('connected', 'connected');
            this.connectBtn.disabled = true;
            this.disconnectBtn.disabled = false;
            if (this.fitAddon) {
                requestAnimationFrame(() => {
                    this.fitAddon.fit();
                    const { rows, cols } = this.term;
                    this.client.sendResize(rows, cols);
                });
            }
            this.term?.focus();
        };
        this.client.onOutput = (bytes) => {
            this.term?.write(new TextDecoder('utf-8', { fatal: false }).decode(bytes));
        };
        this.client.onExit = (code) => {
            this.term?.writeln(`\r\n[session exited (code ${code})]`);
            this._handleDisconnected('idle', 'session exited');
        };
        this.client.onError = (message) => {
            this.term?.writeln(`\r\n[error: ${message}]`);
            this._handleDisconnected('error', `error: ${message}`);
        };
        this.client.onClose = () => {
            this._handleDisconnected('idle', 'disconnected');
        };
    }

    _handleDisconnected(state, label) {
        this._setStatus(state, label);
        this.connectBtn.disabled = false;
        this.disconnectBtn.disabled = true;
    }

    _setStatus(state, label) {
        if (!this.statusEl) return;
        this.statusEl.dataset.state = state;
        this.statusEl.textContent = label;
    }

    _insertCommand(commandText) {
        if (!commandText) return;
        if (!this.client.connected) {
            this._setStatus('idle', 'connect to insert');
            return;
        }
        this.client.sendInput(commandText);
    }
}

window.TerminalPanelController = TerminalPanelController;
