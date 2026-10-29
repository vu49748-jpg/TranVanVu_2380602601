// TranVanVu_2380602601 — copy into a Google Apps Script project.
// Set Script Property OTP_SHARED_SECRET to a random string of at least 32 characters.
// Deploy as Web App: execute as yourself; access Anyone. Every request is HMAC signed.
function jsonOutput(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return jsonOutput({ service: 'TranVanVu_2380602601 OTP', status: 'ready' });
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    var secret = PropertiesService.getScriptProperties().getProperty('OTP_SHARED_SECRET');
    if (!secret || secret.length < 32) return jsonOutput({ ok: false });
    var data = JSON.parse(e.postData.contents);
    if (typeof data.email !== 'string' || !/^[^\s@,;|<>]+@[^\s@,;|<>]+\.[^\s@,;|<>]+$/.test(data.email) ||
        typeof data.code !== 'string' || !/^\d{6}$/.test(data.code) ||
        typeof data.timestamp !== 'string' || !/^\d{10,12}$/.test(data.timestamp) ||
        typeof data.nonce !== 'string' || !/^[a-f0-9]{32}$/.test(data.nonce) ||
        typeof data.signature !== 'string' || !/^[a-f0-9]{64}$/.test(data.signature)) return jsonOutput({ ok: false });
    if (Math.abs(Date.now()/1000 - Number(data.timestamp)) > 120) return jsonOutput({ ok: false });
    var canonical = [data.email, data.code, data.timestamp, data.nonce].join('|');
    var expected = Utilities.computeHmacSha256Signature(canonical, secret, Utilities.Charset.UTF_8)
      .map(function(b) { return ('0' + ((b + 256) % 256).toString(16)).slice(-2); }).join('');
    var difference = 0;
    for (var i = 0; i < expected.length; i++) difference |= expected.charCodeAt(i) ^ data.signature.charCodeAt(i);
    if (difference !== 0) return jsonOutput({ ok: false });
    if (!lock.tryLock(5000)) return jsonOutput({ ok: false });
    var cache = CacheService.getScriptCache();
    if (cache.get('nonce:' + data.nonce)) return jsonOutput({ ok: false });
    if (MailApp.getRemainingDailyQuota() < 1) return jsonOutput({ ok: false });
    cache.put('nonce:' + data.nonce, 'used', 600);
    // Keep only the replay check atomic; email delivery must not serialize other users.
    lock.releaseLock();
    MailApp.sendEmail({to: data.email, subject: 'Mã xác thực Chấm công • Trần Văn Vũ',
      body: 'Mã xác thực của bạn: ' + data.code + '\nMã có hiệu lực 10 phút. Không chia sẻ mã với người khác.',
      name: 'Vũ • Chấm công'});
    return jsonOutput({ ok: true });
  } catch (error) {
    // Never log request bodies, addresses, OTPs or signing secrets.
    return jsonOutput({ ok: false });
  } finally {
    if (lock.hasLock()) lock.releaseLock();
  }
}
