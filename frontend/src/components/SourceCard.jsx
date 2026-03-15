import { ExternalLink, Globe } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

function getDomainFromUrl(url) {
  try { return new URL(url).hostname.replace('www.', ''); }
  catch { return url; }
}

function getFaviconUrl(url) {
  try { return `https://www.google.com/s2/favicons?domain=${new URL(url).origin}&sz=32`; }
  catch { return null; }
}

export default function SourceCard({ source, index }) {
  const domain = getDomainFromUrl(source.url);
  const faviconUrl = getFaviconUrl(source.url);

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
      id={`source-${index}`}
    >
      <Card className="h-full transition-all duration-200 hover:border-primary/30 hover:bg-card/90 bg-card/60">
        <CardContent className="p-4">
          {/* Domain */}
          <div className="flex items-center gap-1.5 mb-2">
            <span className="flex items-center justify-center w-5 h-5 rounded text-xs font-bold bg-primary/10 text-primary flex-shrink-0">
              {index + 1}
            </span>
            {faviconUrl ? (
              <img src={faviconUrl} alt="" className="w-3.5 h-3.5 rounded-sm" onError={(e) => { e.target.style.display = 'none'; }} />
            ) : (
              <Globe className="w-3.5 h-3.5 text-muted-foreground" />
            )}
            <span className="text-xs text-muted-foreground truncate">{domain}</span>
            <ExternalLink className="w-3 h-3 text-muted-foreground ml-auto opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
          </div>

          {/* Title */}
          <h4 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors line-clamp-2 mb-1 leading-snug">
            {source.title}
          </h4>

          {/* Summary */}
          {source.summary && (
            <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">{source.summary}</p>
          )}
        </CardContent>
      </Card>
    </a>
  );
}
