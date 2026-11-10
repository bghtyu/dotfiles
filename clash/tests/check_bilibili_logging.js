// Exercise only the hash-pinned logger class with synthetic values in a VM.
// Do not evaluate the bundle entry point or provide network/persistence APIs.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const filename = path.join(__dirname, '../stash/scripts/sha256/response.bundle-e8768eb5c75bbfaea78f5798ac7827c431f81a61416a7877753f36dd36b9cb60.js');
const bytes = fs.readFileSync(filename);
assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), 'e8768eb5c75bbfaea78f5798ac7827c431f81a61416a7877753f36dd36b9cb60');
const source = bytes.toString('utf8');
// Acorn identified the complete top-level Console class at these UTF-16 offsets.
// Hash and boundaries prevent an updated bundle from silently changing this fixture.
const loggerSource = source.slice(595, 2551);
assert.ok(loggerSource.startsWith('class t{static#e='));
assert.ok(source.slice(2551).startsWith('class n{static escape'));
assert.match(source, /catch\(n\)\{t\.error\(n,e\)\}/);
assert.ok(source.includes('LogLevel:"WARN"'));
const messages = [];
const logger = new vm.Script(`(${loggerSource})`).runInNewContext({
  e: 'Stash',
  console: {log: value => messages.push(value)},
}, {timeout: 1000});
logger.logLevel = 'WARN';
logger.info('SYNTHETIC_INFO');
logger.debug('SYNTHETIC_DEBUG');
assert.equal(messages.length, 0);
const response = {
  status: 200,
  headers: {'set-cookie': 'SYNTHETIC_RESPONSE_HEADER'},
  body: '{SYNTHETIC_NON_JSON_BODY',
};
let parseError;
try {
  JSON.parse(response.body);
} catch (error) {
  parseError = error;
  logger.error(error, response);
}
assert.ok(parseError);
const output = messages.join('\n');
assert.ok(output.includes(String(parseError)));
assert.ok(output.includes('[object Object]'));
assert.ok(!output.includes('SYNTHETIC_RESPONSE_HEADER'));
assert.ok(!output.includes(JSON.stringify(response)));
logger.logLevel = 'OFF';
const count = messages.length;
logger.error(new Error('SYNTHETIC_SUPPRESSED'), response);
assert.equal(messages.length, count);
console.log('WARN emits parse errors; plain response becomes [object Object]; OFF suppresses errors');
