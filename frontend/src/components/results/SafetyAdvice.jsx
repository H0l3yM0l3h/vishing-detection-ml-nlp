export default function SafetyAdvice({ isVishing }) {
  if (isVishing) {
    return (
      <div className="sg-card !p-4" style={{ borderColor: 'rgba(232,32,60,.2)' }}>
        <div className="sec-label mb-3" style={{ color: 'var(--red)' }}>Safety Information</div>
        <ul className="space-y-2 text-sm text-[var(--muted)] list-none">
          <li className="flex gap-2"><span className="text-[var(--red)]">[!]</span> Do NOT share OTP, PIN, or password with anyone over the phone</li>
          <li className="flex gap-2"><span className="text-[var(--red)]">[!]</span> Hang up and call your bank using the number on the back of your card</li>
          <li className="flex gap-2"><span className="text-[var(--red)]">[!]</span> Report the number to your local authorities</li>
          <li className="flex gap-2"><span className="text-[var(--red)]">[!]</span> Real banks will NEVER ask for your full PIN or OTP over a call</li>
        </ul>
      </div>
    )
  }
  return (
    <div className="sg-card !p-4" style={{ borderColor: 'rgba(0,232,122,.15)' }}>
      <div className="sec-label mb-3" style={{ color: 'var(--green)' }}>Assessment Note</div>
      <p className="text-sm text-[var(--muted)] leading-relaxed">
        This call does not exhibit obvious vishing patterns. However, always remain cautious
        with unsolicited calls. Never share sensitive information unless you initiated the call
        and verified the recipient's identity.
      </p>
    </div>
  )
}
