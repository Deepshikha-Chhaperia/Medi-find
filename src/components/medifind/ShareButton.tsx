import { useState } from "react";
import { Share2, MessageCircle, Link2, Check } from "lucide-react";
import { buildWhatsAppShare } from "@/lib/geocode";
import { cn } from "@/lib/utils";

interface Props {
  facilityName: string;
  address: string;
  phone: string;
  directionsUrl: string;
  facilityId: string;
  className?: string;
}

export function ShareButton({ facilityName, address, phone, directionsUrl, facilityId, className }: Props) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const waUrl = buildWhatsAppShare(facilityName, address, phone, directionsUrl);
  const facilityUrl = `${window.location.origin}/facility/${facilityId}`;

  const copyLink = async () => {
    await navigator.clipboard.writeText(facilityUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("relative", className)}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        className="inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:bg-surface-muted hover:text-foreground transition-colors"
        title="Share"
      >
        <Share2 className="h-3.5 w-3.5" />
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          {/* Dropdown */}
          <div className="absolute right-0 bottom-full mb-1 z-[999] w-44 rounded-lg border border-border bg-surface shadow-soft-lg p-1 animate-fade-in-up">
            <a
              href={waUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-foreground hover:bg-surface-muted transition-colors"
              onClick={() => setOpen(false)}
            >
              <MessageCircle className="h-3.5 w-3.5 text-[#25D366]" />
              WhatsApp
            </a>
            <button
              onClick={() => { copyLink(); setOpen(false); }}
              className="w-full flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-foreground hover:bg-surface-muted transition-colors"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Link2 className="h-3.5 w-3.5" />}
              {copied ? "Copied!" : "Copy link"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
