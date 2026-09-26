const crypto = require('crypto');
const fs = require('fs');

const MAGIC = 'KS1';

function deriveKey(pass, salt) {
  return crypto.scryptSync(pass, salt, 32);
}

function seal(inputPath, outputPath) {
  const pass = process.env.KS_PASS;
  if (!pass) throw new Error('thieu bien KS_PASS');
  const data = fs.readFileSync(inputPath);
  const salt = crypto.randomBytes(16);
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', deriveKey(pass, salt), iv);
  const ct = Buffer.concat([cipher.update(data), cipher.final()]);
  const tag = cipher.getAuthTag();
  const parts = [
    MAGIC,
    salt.toString('base64'),
    iv.toString('base64'),
    tag.toString('base64'),
    ct.toString('base64'),
  ];
  fs.writeFileSync(outputPath, parts.join('\n') + '\n');
  console.log('sealed ' + data.length + ' bytes -> ' + fs.statSync(outputPath).size + ' bytes');
}

function unseal(inputPath, outputPath) {
  const pass = process.env.KS_PASS;
  if (!pass) throw new Error('thieu bien KS_PASS');
  const parts = fs.readFileSync(inputPath, 'utf8').trim().split('\n');
  if (parts.length !== 5 || parts[0] !== MAGIC) throw new Error('file khong hop le');
  const key = deriveKey(pass, Buffer.from(parts[1], 'base64'));
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(parts[2], 'base64'));
  decipher.setAuthTag(Buffer.from(parts[3], 'base64'));
  const out = Buffer.concat([
    decipher.update(Buffer.from(parts[4], 'base64')),
    decipher.final(),
  ]);
  fs.writeFileSync(outputPath, out);
  console.log('unsealed -> ' + out.length + ' bytes');
}

const cmd = process.argv[2];
const inPath = process.argv[3];
const outPath = process.argv[4];
if (!inPath || !outPath) throw new Error('dung: node tools/keystore-crypto.js seal|unseal <in> <out>');
if (cmd === 'seal') seal(inPath, outPath);
else if (cmd === 'unseal') unseal(inPath, outPath);
else throw new Error('lenh khong hop le: ' + cmd);
