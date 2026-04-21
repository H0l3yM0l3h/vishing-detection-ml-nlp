import { useRef, useState } from 'react'
import { Button } from '../ui/button'
import {
  Dialog, DialogClose, DialogContent, DialogDescription,
  DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from '../ui/dialog'
import { ScrollText } from 'lucide-react'

const SECTIONS = [
  {
    title: 'Acceptance of Terms',
    body: 'By accessing and using ShieldGuard, you agree to comply with and be bound by these Terms of Service. If you do not agree, discontinue use immediately.',
  },
  {
    title: 'User Account Responsibilities',
    body: 'You are responsible for maintaining the confidentiality of your credentials. Any activities under your account are your sole responsibility. Notify administrators immediately of any unauthorised access.',
  },
  {
    title: 'Data & Content Usage',
    body: 'ShieldGuard processes audio and transcripts you submit solely for vishing detection purposes. Submitted content is not stored permanently and is not used for training without explicit consent.',
  },
  {
    title: 'Limitation of Liability',
    body: 'ShieldGuard provides analysis "as is" without warranties. Results are probabilistic and should not be the sole basis for legal or financial decisions. The authors shall not be liable for any damages arising from use of the platform.',
  },
  {
    title: 'Acceptable Use',
    body: null,
    list: [
      'Do not upload content that violates applicable law',
      'Do not attempt to reverse-engineer or abuse the AI models',
      'Respect the rights and privacy of other individuals',
      'Comply with local and international telecommunications laws',
    ],
  },
  {
    title: 'Modifications',
    body: 'ShieldGuard reserves the right to modify these terms at any time. Continued use after changes constitutes acceptance.',
  },
  {
    title: 'Governing Law',
    body: 'These terms are governed by the laws of the jurisdiction where ShieldGuard is primarily operated, without regard to conflict of law principles.',
  },
]

export default function TocDialog({ onAgree }) {
  const [hasRead, setHasRead] = useState(false)
  const contentRef = useRef(null)

  const handleScroll = () => {
    const el = contentRef.current
    if (!el) return
    const pct = el.scrollTop / (el.scrollHeight - el.clientHeight)
    if (pct >= 0.99 && !hasRead) setHasRead(true)
  }

  return (
    <Dialog onOpenChange={() => setHasRead(false)}>
      <DialogTrigger asChild>
        <button
          type="button"
          style={{
            background: 'none', border: 'none', padding: 0, cursor: 'pointer',
            fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px',
            color: '#a1a1aa', textDecoration: 'underline',
            textUnderlineOffset: '3px', display: 'inline',
          }}
        >
          Terms &amp; Conditions
        </button>
      </DialogTrigger>

      <DialogContent className="flex flex-col gap-0 p-0" style={{ maxWidth: '500px', maxHeight: '80vh' }}>
        <DialogHeader className="contents space-y-0 text-left">
          <DialogTitle
            style={{ borderBottom: '1px solid #27272a', padding: '16px 24px', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ScrollText size={16} style={{ color: '#6366f1' }} />
              Terms &amp; Conditions
            </span>
          </DialogTitle>

          <div
            ref={contentRef}
            onScroll={handleScroll}
            style={{ overflowY: 'auto', flex: 1, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '50vh' }}
          >
            <DialogDescription asChild>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {SECTIONS.map((s) => (
                  <div key={s.title} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 600, fontSize: '13px', color: '#f4f4f5' }}>
                      {s.title}
                    </p>
                    {s.body && (
                      <p style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#a1a1aa', lineHeight: 1.65 }}>
                        {s.body}
                      </p>
                    )}
                    {s.list && (
                      <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {s.list.map((item) => (
                          <li key={item} style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '13px', color: '#a1a1aa', lineHeight: 1.55 }}>
                            {item}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </DialogDescription>
          </div>
        </DialogHeader>

        <DialogFooter style={{ borderTop: '1px solid #27272a', padding: '14px 24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          {!hasRead && (
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#52525b', flexGrow: 1 }}>
              Scroll to read all terms before accepting.
            </span>
          )}
          <DialogClose asChild>
            <Button type="button" variant="outline"
              style={{ borderColor: '#27272a', background: '#18181b', color: '#a1a1aa', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
              Cancel
            </Button>
          </DialogClose>
          <DialogClose asChild>
            <Button
              type="button"
              disabled={!hasRead}
              onClick={() => hasRead && onAgree?.()}
              style={{ background: hasRead ? '#f4f4f5' : '#27272a', color: hasRead ? '#09090b' : '#71717a', fontFamily: "'Plus Jakarta Sans', sans-serif" }}
            >
              I agree
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
