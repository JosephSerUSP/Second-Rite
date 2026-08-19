'use strict';

const PRODUCT_NAME = 'Thestra Studio';
const WINDOWS_APP_USER_MODEL_ID = 'com.josephserusp.thestrastudio';
const WINDOWS_HOST_FILENAME = `${PRODUCT_NAME}.exe`;
const WINDOWS_HOST_DESCRIPTION = 'Thestra Studio Development Host';
const COMPANY_NAME = 'JosephSerUSP';

function quoteWindowsCommandArgument(value) {
    const text = String(value);
    if (text.includes('"')) {
        throw new Error(`Windows paths used for Studio relaunch may not contain a quote: ${text}`);
    }
    return `"${text}"`;
}

function buildWindowsRelaunchCommand(executablePath, appPath) {
    return `${quoteWindowsCommandArgument(executablePath)} ${quoteWindowsCommandArgument(appPath)}`;
}

module.exports = {
    COMPANY_NAME,
    PRODUCT_NAME,
    WINDOWS_APP_USER_MODEL_ID,
    WINDOWS_HOST_DESCRIPTION,
    WINDOWS_HOST_FILENAME,
    buildWindowsRelaunchCommand,
    quoteWindowsCommandArgument,
};
