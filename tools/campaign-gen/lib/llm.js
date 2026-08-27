// Compatibility export. Transport lives in the shared module so independent
// authoring tools cannot drift in streaming, retries, or JSON extraction.
'use strict';
module.exports = require('../../shared/llm');
