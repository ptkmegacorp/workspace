#!/usr/bin/env node
/**
 * Simple Resend CLI - send emails via Resend API
 * Usage: 
 *   export RESEND_API_KEY="re_123456789"
 *   ./resend-cli.js send --to recipient@example.com --subject "Subject" --body "Email body"
 *   ./resend-cli.js list    # List emails
 */

const { Resend } = require('resend');
const fs = require('fs');

const args = process.argv.slice(2);
const command = args[0];

const apiKey = process.env.RESEND_API_KEY;
if (!apiKey) {
  console.error('Error: RESEND_API_KEY environment variable not set');
  console.error('Set it with: export RESEND_API_KEY="re_your_api_key"');
  process.exit(1);
}

const resend = new Resend(apiKey);

async function listEmails() {
  try {
    const { data, error } = await resend.emails.list();
    if (error) {
      console.error('Error:', error);
      return;
    }
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error('Error:', e.message);
  }
}

async function sendEmail() {
  const toIdx = args.indexOf('--to');
  const subjectIdx = args.indexOf('--subject');
  const bodyIdx = args.indexOf('--body');
  const fromIdx = args.indexOf('--from');
  
  const to = args[toIdx + 1];
  const subject = args[subjectIdx + 1];
  const body = args[bodyIdx + 1];
  const from = fromIdx ? args[fromIdx + 1] : 'onboarding@resend.dev';
  
  if (!to || !subject || !body) {
    console.error('Usage: send --to <email> --subject <subject> --body <body> [--from <email>]');
    process.exit(1);
  }
  
  try {
    const { data, error } = await resend.emails.send({
      from,
      to,
      subject,
      html: `<p>${body}</p>`,
    });
    
    if (error) {
      console.error('Error:', error);
      return;
    }
    console.log('Email sent successfully!');
    console.log(JSON.stringify(data, null, 2));
  } catch (e) {
    console.error('Error:', e.message);
  }
}

if (command === 'list') {
  listEmails();
} else if (command === 'send') {
  sendEmail();
} else {
  console.log(`
Resend CLI - Simple email sending via Resend API

Usage:
  export RESEND_API_KEY="re_your_api_key"
  
  resend-cli list                  # List recent emails
  resend-cli send --to <email> --subject <subject> --body <body> [--from <email>]

Examples:
  resend-cli send --to test@example.com --subject "Hello" --body "World"
  resend-cli send --to user@mail.com --subject "Alert" --body "Something happened" --from me@yourdomain.com
  `);
}
