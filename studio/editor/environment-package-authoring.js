'use strict';

// HTTP/panel adapter for the one environment-manifest persistence authority.
const storage = require('./plate-manifest-storage');
module.exports = { read: storage.readPackage, writeCalibration: storage.writeCalibration };
