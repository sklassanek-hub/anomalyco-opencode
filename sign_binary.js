#!/usr/bin/env node
// Local binary signing script (CP-2)
// Generates a SHA256 hash + RSA signature using Node's crypto module
// Usage: node sign_binary.js <binary>
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const binary = process.argv[2] || 'opencode_new.exe';
if (!fs.existsSync(binary)) {
  console.error('Binary not found:', binary);
  process.exit(1);
}

const data = fs.readFileSync(binary);
const sha256 = crypto.createHash('sha256').update(data).digest('hex');
const sha512 = crypto.createHash('sha512').update(data).digest('hex');

// Generate or load signing key
const keyPath = 'signing_key.pem';
let privateKey, publicKey;
if (fs.existsSync(keyPath)) {
  privateKey = crypto.createPrivateKey(fs.readFileSync(keyPath));
  publicKey = crypto.createPublicKey(privateKey);
} else {
  const { publicKey: pub, privateKey: priv } = crypto.generateKeyPairSync('rsa', {
    modulusLength: 2048,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' }
  });
  fs.writeFileSync(keyPath, priv);
  fs.writeFileSync('signing_key.pub.pem', pub);
  privateKey = crypto.createPrivateKey(priv);
  publicKey = crypto.createPublicKey(pub);
  console.log('Generated new RSA 2048 signing key (signing_key.pem + .pub.pem)');
}

// Sign
const signature = crypto.sign('RSA-SHA256', data, privateKey);
const sigB64 = signature.toString('base64');

// Write sigstore-style signature bundle
const bundle = {
  mediaType: 'application/vnd.dev.sigstore.bundle+json;version=0.1',
  verificationMaterial: {
    publicKey: { hint: { algorithm: 'RSASSA-PKCS1-v1_5' } },
    certificate: null
  },
  signature: {
    content: sigB64,
    publicKey: { hint: { algorithm: 'RSASSA-PKCS1-v1_5' } }
  },
  metadata: {
    binary: path.basename(binary),
    size: data.length,
    sha256,
    sha512,
    algorithm: 'RSASHA256',
    timestamp: new Date().toISOString(),
    signedBy: 'local-key (NOT a real sigstore; placeholder for testing)'
  }
};

const sigFile = binary + '.sig';
fs.writeFileSync(sigFile, JSON.stringify(bundle, null, 2));
fs.writeFileSync(binary + '.sha256', sha256 + '  ' + path.basename(binary) + '\n');

// Verify
const verified = crypto.verify('RSA-SHA256', data, publicKey, signature);
console.log('Binary:', binary);
console.log('Size:', data.length, 'bytes');
console.log('SHA256:', sha256);
console.log('SHA512:', sha512);
console.log('Signature:', sigFile, '(' + signature.length + ' bytes)');
console.log('Public key: signing_key.pub.pem');
console.log('Self-verify:', verified ? 'PASS' : 'FAIL');
console.log('NOTE: This is a local RSA key, NOT a real sigstore/codesign certificate.');
console.log('      For production: use cosign with a real OIDC identity or codesign.exe.');
