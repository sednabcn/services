import os, imaplib, email, re, json

# Regex for thread IDs and bounce detection
TID_RE = re.compile(r"\[TID:([a-f0-9\-]{1,16})\]", re.IGNORECASE)
BOUNCE_RE = re.compile(r"(undeliverable|mail delivery|failure notice|returned mail)", re.IGNORECASE)

# Configurable UID state file (defaults to tracking/.uids.json)
UID_STATE_FILE = os.path.join(
    os.environ.get("TRACKING_DIR", "tracking"),
    ".uids.json"
)

def _load_seen_uids():
    if os.path.exists(UID_STATE_FILE):
        with open(UID_STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def _save_seen_uids(seen):
    os.makedirs(os.path.dirname(UID_STATE_FILE), exist_ok=True)
    with open(UID_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, indent=2)

class ReplyTracker:
    def __init__(self, imap_host=None, imap_user=None, imap_pass=None, mailbox="INBOX", mark_seen=False):
        self.imap_host = imap_host or os.environ.get("IMAP_HOST")
        self.imap_user = imap_user or os.environ.get("IMAP_USER")
        self.imap_pass = imap_pass or os.environ.get("IMAP_PASS")
        self.mailbox = mailbox
        self.mark_seen = mark_seen

    def _connect(self):
        m = imaplib.IMAP4_SSL(self.imap_host)
        m.login(self.imap_user, self.imap_pass)
        return m

    def _extract_body(self, msg):
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in disp:
                    charset = part.get_content_charset() or "utf-8"
                    body += part.get_payload(decode=True).decode(charset, errors="ignore")
            # fallback: use html if no plain text found
            if not body:
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        charset = part.get_content_charset() or "utf-8"
                        body = part.get_payload(decode=True).decode(charset, errors="ignore")
                        break
        else:
            charset = msg.get_content_charset() or "utf-8"
            body = msg.get_payload(decode=True).decode(charset, errors="ignore")
        return body

    def fetch_replies(self):
        seen = _load_seen_uids()
        m = self._connect()
        m.select(self.mailbox)
        result, data = m.search(None, "ALL")
        if result != "OK":
            m.logout()
            return []

        uids = data[0].split()
        replies, new_seen = [], set(seen)

        for uid in uids:
            uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
            if uid_str in seen:
                continue  # already processed

            res, msgdata = m.fetch(uid, "(RFC822)")
            if res != "OK":
                continue

            msg = email.message_from_bytes(msgdata[0][1])
            subject = msg.get("Subject", "")
            body = self._extract_body(msg)

            # TID + bounce detection
            match = TID_RE.search(subject) or TID_RE.search(body)
            tid = match.group(1) if match else None
            is_bounce = bool(BOUNCE_RE.search(subject) or BOUNCE_RE.search(body))

            from_addr = email.utils.parseaddr(msg.get("From"))[1]

            replies.append({
                "uid": uid_str,
                "subject": subject,
                "body": body,
                "tid": tid,
                "from": from_addr,
                "bounce": is_bounce
            })

            new_seen.add(uid_str)
            if self.mark_seen:
                m.store(uid, "+FLAGS", "\\Seen")

        m.logout()
        _save_seen_uids(new_seen)
        return replies
