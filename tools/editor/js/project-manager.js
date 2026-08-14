// #479: Electron-only Project lifecycle controls. This file intentionally does
// nothing in browser-only/golden hosting where the bounded preload bridge is
// absent, so Project management does not become a second HTTP/root-selection
// protocol and does not perturb browser-only Studio surfaces.
(function() {
    const bridge = window.thestraProjects;
    if (!bridge) return;

    function show(message) {
        if (typeof showToast === 'function') showToast(message);
        else alert(message);
    }

    function cleanFolderName(value) {
        const name = String(value || '').trim();
        if (!name || name === '.' || name === '..' || /[\\/]/.test(name)) return null;
        return name;
    }

    function joinTarget(parent, name) {
        return String(parent).replace(/[\\/]+$/, '') + '/' + name;
    }

    function hasUnsavedProjectChanges() {
        try {
            return typeof window.thestraHasUnsavedProjectChanges === 'function'
                && !!window.thestraHasUnsavedProjectChanges();
        } catch (_) {
            return false;
        }
    }

    function confirmProjectSwitch(action) {
        if (typeof window.thestraPrepareForProjectSwitch === 'function'
                && !window.thestraPrepareForProjectSwitch()) return false;
        if (!hasUnsavedProjectChanges()) return true;
        return confirm([
            'The current Project has unsaved changes.',
            '',
            `${action} will discard those changes. Continue without saving?`,
        ].join('\n'));
    }

    async function currentState() {
        try { return await bridge.current(); }
        catch (error) { show(`Could not read current Project: ${error.message}`); return null; }
    }

    window.showCurrentProject = async function() {
        const state = await currentState();
        if (!state) return;
        const info = state.info;
        alert([
            'Current Thestra Project',
            '',
            info.projectRoot,
            '',
            info.sameAsInstall ? 'This checkout is the opened Project.' : 'This is an external/separate Project.',
            info.assetsPath ? 'Project assets/: present' : 'Project assets/: absent',
        ].join('\n'));
    };

    window.openThestraProject = async function() {
        if (!confirmProjectSwitch('Opening another Project')) return;
        const selected = await bridge.chooseDirectory({ title: 'Open Thestra Project Folder' });
        if (!selected) return;
        try {
            show('Reopening Thestra Studio with the selected Project…');
            await bridge.open(selected);
        } catch (error) {
            show(`Cannot open Project: ${error.message}`);
        }
    };

    window.forkCurrentThestraProject = async function() {
        const state = await currentState();
        if (!state) return;
        const parent = await bridge.chooseDirectory({ title: 'Choose Folder for Forked Project' });
        if (!parent) return;
        const suggested = state.info.sameAsInstall ? 'new-game' : 'project-fork';
        const name = cleanFolderName(prompt('Folder name for the forked Project:', suggested));
        if (!name) {
            show('Project folder name must be non-empty and cannot contain path separators.');
            return;
        }
        const target = joinTarget(parent, name);
        try {
            const created = await bridge.fork({ source: state.info.projectRoot, target });
            if (confirm(`Project created at:\n${created.projectRoot}\n\nOpen it now?`)) {
                if (!confirmProjectSwitch('Opening the forked Project')) return;
                await bridge.open(created.projectRoot);
            }
        } catch (error) {
            show(`Could not fork Project: ${error.message}`);
        }
    };

    window.createSparseThestraProject = async function() {
        if (!confirmProjectSwitch('Creating and opening a new Project')) return;
        const state = await currentState();
        if (!state) return;
        if (!state.sparse || !state.sparse.available) {
            alert([
                'New sparse Project is not available on this revision yet.',
                '',
                (state.sparse && state.sparse.reason) || 'The neutral authored-default provider is unavailable.',
                '',
                'Use Fork Project for safe isolation today. This command will become active when the neutral #390 baseline lands; callers will not need a new Project API.',
            ].join('\n'));
            return;
        }
        const parent = await bridge.chooseDirectory({ title: 'Choose Parent Folder for New Thestra Project' });
        if (!parent) return;
        const name = cleanFolderName(prompt('Folder name for the new Project:', 'new-game'));
        if (!name) {
            show('Project folder name must be non-empty and cannot contain path separators.');
            return;
        }
        try {
            const created = await bridge.create({ mode: 'sparse', target: joinTarget(parent, name) });
            show(`Project created at:\n${created.projectRoot}\n\nOpening it now…`);
            await bridge.open(created.projectRoot);
        } catch (error) {
            show(`Could not create Project: ${error.message}`);
        }
    };

    function item(label, handler, title) {
        const row = document.createElement('div');
        row.className = 'dropdown-item';
        row.textContent = label;
        if (title) row.title = title;
        row.addEventListener('click', handler);
        return row;
    }

    function injectFileMenu() {
        const menuBar = document.querySelector('.menu-bar');
        if (!menuBar) return;
        const fileMenu = Array.from(menuBar.querySelectorAll(':scope > .menu-item'))
            .find(node => String(node.childNodes[0] && node.childNodes[0].textContent || '').trim() === 'File');
        if (!fileMenu) return;
        const dropdown = fileMenu.querySelector('.dropdown-menu');
        if (!dropdown || dropdown.querySelector('[data-thestra-project-item]')) return;

        const separator = document.createElement('div');
        separator.setAttribute('data-thestra-project-item', 'separator');
        separator.style.cssText = 'border-top: 1px solid var(--win-shadow); margin: 2px 4px;';
        dropdown.appendChild(separator);

        const rows = [
            item('📁 Project Info…', () => showCurrentProject()),
            item('📂 Open Project…', () => openThestraProject(), 'Select a Thestra Project folder (the folder that contains data/).'),
            item('🧬 Fork Project…', () => forkCurrentThestraProject(), 'Copy Project-owned data/assets into an isolated Project root.'),
            item('✨ New Project…', () => createSparseThestraProject(), 'Create a neutral sparse Project, then immediately open it in Thestra Studio.'),
        ];
        rows.forEach(row => {
            row.setAttribute('data-thestra-project-item', 'true');
            dropdown.appendChild(row);
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', injectFileMenu);
    else injectFileMenu();
})();
