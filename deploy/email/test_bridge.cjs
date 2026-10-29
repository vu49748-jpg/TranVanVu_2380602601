const vm = require('node:vm');
const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const secret = 'unit-test-signing-secret-only-not-for-production';
const sent = [], cache = new Map();
const sandbox = {
  ContentService: { MimeType: { JSON: 'json' }, createTextOutput: text => ({ text, setMimeType() { return this; } }) },
  PropertiesService: { getScriptProperties: () => ({ getProperty: () => secret }) },
  Utilities: { Charset: { UTF_8: 'utf8' }, computeHmacSha256Signature: (data, key) => [...crypto.createHmac('sha256', key).update(data).digest()] },
  LockService: { getScriptLock: () => ({ tryLock: () => true, hasLock: () => true, releaseLock() {} }) },
  CacheService: { getScriptCache: () => ({ get: key => cache.get(key), put: (key,value) => cache.set(key,value) }) },
  MailApp: { getRemainingDailyQuota: () => 100, sendEmail: value => sent.push(value) },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(`${__dirname}/Code.gs`, 'utf8'), sandbox);
const payload = { email: 'staff@example.com', code: '123456', timestamp: String(Math.floor(Date.now()/1000)), nonce: crypto.randomBytes(16).toString('hex') };
payload.signature = crypto.createHmac('sha256',secret).update([payload.email,payload.code,payload.timestamp,payload.nonce].join('|')).digest('hex');
const run = data => JSON.parse(sandbox.doPost({postData:{contents:JSON.stringify(data)}}).text);
assert.equal(run({...payload, code:'999999'}).ok, false, 'Reject tampering');
assert.equal(run({...payload, timestamp:'1000000000'}).ok, false, 'Reject stale request');
assert.equal(run({...payload, email:'a@example.com,b@example.com'}).ok, false, 'Reject recipient injection');
assert.equal(run(payload).ok, true, 'Accept signed request');
assert.equal(sent.length,1);
assert.equal(sent[0].to, payload.email);
assert.match(sent[0].body,/123456/);
assert.equal(run(payload).ok,false,'Reject replay');
assert.equal(sent.length,1,'Never resend a replay');
console.log('Email bridge: signed request, tampering, expiry, injection and replay checks passed (mock MailApp; no email sent).');
