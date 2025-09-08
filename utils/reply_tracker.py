import os, imaplib, email, re, json

TID_RE = re.compile(r"\[TID:([a-f0-9\-]{1,16})\]", re.IGNORECASE)
UID_STATE_FILE = "tracking/.uids.json"

def _load_seen_uids():
    if os.path.exists(UID_STATE_FILE):
        with open(UID_STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()

def _save_seen_uids(seen):
    with open(UID_STATE_FILE, "w") as f:
        json.dump(list(seen), f)

class ReplyTracker:
    def __init__(self, imap_host=None, imap_user=None, imap_pass=None, mailbox='INBOX'):
        self.imap_host = imap_host or os.environ.get('IMAP_HOST')
        self.imap_user = imap_user or os.environ.get('IMAP_USER')
        self.imap_pass = imap_pass or os.environ.get('IMAP_PASS')
        self.mailbox = mailbox

    def _connect(self):
        m = imaplib.IMAP4_SSL(self.imap_host)
        m.login(self.imap_user, self.imap_pass)
        return m

    def fetch_replies(self):
        seen = _load_seen_uids()
        m = self._connect()
        m.select(self.mailbox)
        result, data = m.search(None, 'ALL')
        if result != 'OK':
            m.logout()
            return []

        uids = data[0].split()
        replies, new_seen = [], set(seen)
        for uid in uids:
            uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
            if uid_str in seen:
                continue  # already processed

            res, msgdata = m.fetch(uid, '(RFC822)')
            if res != 'OK':
                continue
            msg = email.message_from_bytes(msgdata[0][1])
            subject, body = msg.get('Subject', ''), ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body += part.get_payload(decode=True).decode(errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')

            match = TID_RE.search(subject) or TID_RE.search(body)
            tid = match.group(1) if match else None
            from_addr = email.utils.parseaddr(msg.get('From'))[1]

            replies.append({
                'uid': uid_str,
                'subject': subject,
                'body': body,
                'tid': tid,
                'from': from_addr
            })
            new_seen.add(uid_str)

        m.logout()
        _save_seen_uids(new_seen)
        return replies
